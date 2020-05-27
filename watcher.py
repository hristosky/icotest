import os
import json
import threading
import sys
import time
import subprocess
import signal
from pathlib import Path

sys.path.append('/opt/containers/ocpytools/lib/')
from etcd3_client import EtcdManagement

from configman import ProcessConfig
from logger import Logger

class Watcher(threading.Thread):

	def __init__(self, confman_etcd_root):
		threading.Thread.__init__(self)
		logs = Logger(filename = "watcher", \
						logger_name = "Config Watcher", \
						dirname="/aux1/occonfman/")
		self.etcd = EtcdManagement()

		normalized_confman_etcd_root = os.path.normpath(confman_etcd_root)
		confman_config = f"{normalized_confman_etcd_root}/occonfman"

		self.confman_key = {}
		self.conf = []
		try:
			self.conf = self.etcd.get_key(confman_config)
			print("Getting main config for occonfman")
			logs.info("Getting main config for occonfman")
			if(self.conf[0]):
				self.confman_key = json.loads(self.conf[0].decode("utf-8"))
				logs.info(f"Successfully retrieved main config for occonfman")
			else:
				logs.error(f"Confman config may be empty {self.conf}")
		except Exception as e:
			print(f"Watcher was unable to retrieve its main config file {confman_config}")
			logs.log.exception(f"Watcher was unable to get its config file {confman_config}")
			raise(e)

		# At this point we know that ectd is available
		# if self.confman_key is not present or it is empty, add default config to ectd
		if not self.confman_key:
			self.confman_key = {
				"config_key_prefix" : f"{normalized_confman_etcd_root}/configs/",
				"status_key_prefix" : f"{normalized_confman_etcd_root}/status/",
				"appconf_json_key" : f"{normalized_confman_etcd_root}/occonfman/",
				"appconf_json_dir" : "/aux0/customer/occonfman/"
			}

			logs.warning(f"{confman_config} is not present in etcd or empty. Using default: {self.confman_key}");
			self.etcd.write(confman_config, json.dumps(self.confman_key))

		"""
		Initialize the configurations
		- read all application json config files and copy them to etcd
		- check if config key exists, if not, copy its content and commands
		- run through all configs and process them one by one
		"""

		logs.info("Starting config initialization procedure.")

		if(self.confman_key):
			self.initial = InitializeConfig(self.confman_key["config_key_prefix"], self.confman_key["status_key_prefix"])
			logs.info("Applying preset configs for initialization:")
			self.initial.apply_preset_configs(self.confman_key["appconf_json_dir"], self.confman_key["appconf_json_key"], 0)
			logs.info("Going through each config file in etcd and processing its content and commands:")
			self.initial.preconfigure()
		else:
			logs.error(f"No initialization will be done, since main confman key was not present: {confman_config}")
			print(f"No initialization, because there's no confman key: {confman_config}")
		logs.clear_handler()

	def watcher(self, events):
		
		logs = Logger(filename = "watcher", \
                                                logger_name = "Config Watcher", \
                                                dirname="/aux1/occonfman/")
		for event in events.events:
			logs.info(f"New event received: {event}")
#			print(event.mod_revision)
			new_event = Worker(event, self.confman_key["status_key_prefix"])
			new_event.start()
		logs.clear_handler()


	def run(self):
		self.etcd.add_watch_prefix_callback(self.confman_key["config_key_prefix"], self.watcher)


class Worker(threading.Thread):

	def __init__(self, event, status_path):
		threading.Thread.__init__(self)
		self.event = event
		self.status_path = status_path

	def worker_method(self):
		worker = ProcessConfig(self.event, self.status_path, 0)
		worker.process_config()

	def run(self):
		self.worker_method()


class InitializeConfig():

	def __init__(self, key_prefix, status_path):
		self.hostname = os.uname()[1]
		logs = Logger(filename = "initialize_config", \
                                                logger_name = "Config Initialize", \
                                                dirname="/aux1/occonfman/")
		self.etcd = EtcdManagement()

		self.key_pref = key_prefix
		self.status_path = status_path
		logs.clear_handler()

	def check_affected(self, val):
		command_list = []
		logs = Logger(filename = "occonfman", \
                                                logger_name = "Config Initialize check_affected", \
                                                dirname="/aux1/occonfman/")
		try:
			json_val = json.loads(val)
		except:
			logs.error(f"Invalid json: {val} ")
			return []

		if self.hostname in json_val["commands"].keys():
			command_list += json_val["commands"][self.hostname]

		logs.clear_handler()

		return command_list

	def apply_preset_configs(self, json_path, etcd_path, reset):

		logs = Logger(filename = "occonfman", \
                                                logger_name = "Config Initialize apply_preset_configs", \
                                                dirname="/aux1/occonfman/")
		app_path = Path(json_path)
		json_data = []
		if app_path.is_dir():
			for confs in app_path.glob('*.json'):
				if confs.is_file():
					with open(confs, "r") as conf:
						try:
							conf_content = conf.read()
							json_data += json.loads(conf_content)
							etcd_fullpath = etcd_path.rstrip('/') + '/' +str(confs.name)
							self.etcd.write(etcd_fullpath, conf_content)
						except:
							print(f"Could not load {confs} file")
							logs.error(f"Cound not load {confs} file")
							continue
		else:
			print(f"Filepath does not exist: {json_path}")
			logs.error(f"Filepath does not exist: {json_path}")
		configdict = {}
		for cnt in json_data:
			if cnt["config"] in configdict.keys():
				for arrv in cnt["command"]:
					configdict[cnt["config"]].append(arrv)
			else:
				configdict[cnt["config"]] = list()
				for arrv in cnt["command"]:
					configdict[cnt["config"]].append(arrv)

		for config_data in json_data:
			config_key_path = self.key_pref.rstrip('/') + config_data["config"]
			config_key = self.etcd.get_key(config_key_path)
			if(config_key[0]):
				try:
					json_content = json.loads(config_key[0].decode("utf-8"))
				except:
					print("Invalid json for: {} \n Content: {}".format(config_key_path, config_key[0].decode("utf-8")))
					logs.error(f"Invalid json for: {config_key_path} \n Content: {config_key[0].decode('utf-8')} ")
					continue
				if self.hostname in json_content["commands"].keys() and not reset:
					print("Hostname already exists in commands and reset is not set, so no overwrite")
					logs.info("Hostname already exists in commands and reset is not set, so no overwrite")
				else:
					json_content["commands"][self.hostname] = configdict[config_data["config"]]
					self.etcd.write(config_key_path, json_content)
					print(f"Key exists, but  {self.hostname} is not in commands or reset is given")
					logs.info(f"Key exists, but  {self.hostname} is not in commands or reset is given")
			else:
				print("Found config file without a key in etcd. Attempting to generate it from template.")
				logs.error("Found config file without a key in etcd. Attempting to generate it from template.")
				if Path(config_data["config"]).is_file():
					fcontent = ''
					json_content = {}
					with open(config_data["config"], "r") as content_file:
						fcontent = content_file.read()
					json_content["content"] = fcontent
					json_content["commands"] = dict()
					json_content["commands"][self.hostname] = configdict[config_data["config"]]
					json_content["path"] = config_data["config"]
					self.etcd.write(config_key_path, json.dumps(json_content))
		logs.clear_handler()

	def preconfigure(self):

		logs = Logger(filename = "occonfman", \
                                                logger_name = "Config Initializa - preconfigure", \
                                                dirname="/aux1/occonfman/")
		commands_set = set()
		for kvmeta in self.etcd.get_prefix_real(self.key_pref):
			ckey = kvmeta[1].key.decode('utf-8')
			cval = kvmeta[0].decode("utf-8")
			affected_commands = self.check_affected(cval)
			if not affected_commands:
				print(f"{ckey} does not concern my hostname {self.hostname}")
				logs.info(f"{ckey} does not concern my hostname {self.hostname}")
				continue
			process_config = ProcessConfig(kvmeta, self.status_path, 1)
			process_config.process_config()
#			for single_command in affected_commands:
#				commands_set.add(single_command)
#			for command in commands_set:
#				subprocess.run(str(command), shell = True)
		logs.clear_handler()


g_Run = True

def sigint_hander(signum, frame):
	global g_Run

	print("Stop signal received.")
	g_Run = False

signal.signal(signal.SIGINT, sigint_hander)
signal.signal(signal.SIGTERM, sigint_hander)

if "ETCD_CONFMAN_ROOT" in os.environ:
	confman_path = os.environ['ETCD_CONFMAN_ROOT']
else:
	confman_path = "/platform/v1/sdp"

watcher = Watcher(confman_path)
watcher.start()

while g_Run:
	signal.pause()
