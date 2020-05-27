import os
import sys
import json
import jinja2
from subprocess import PIPE, run

sys.path.append('/opt/containers/ocpytools/lib/')
from etcd3_client import EtcdManagement
from logger import Logger

class ProcessConfig():
	"""
	- Processes a given etcd config key:
	- checks if local node is affected by this config change
	- generates new config file
	- replaces markers with their respective values
	- executes the set of commands related to this host
	"""
	def __init__(self, event, status_path, initial):
		log = Logger(filename = "confman", \
                                                logger_name = "Process Config", \
                                                dirname="/aux1/occonfman/")
		self.etcd = EtcdManagement()
			
		self.initial = initial
		if(self.initial):
			self.event_value = json.loads(event[0].decode("utf-8"))
			self.event_revision = str(self.etcd.get_mod_revision(event[1].key.decode("utf-8")))
			print(self.event_revision)
			log.info(f"Event revision is: {self.event_revision}")
		else:
			self.event_value = json.loads(event.value)
			self.event_revision = event.mod_revision

		self.hostname = os.uname()[1]
		self.status_path = status_path
		log.clear_handler()

	def check_affected(self, hosts):
		""" 
		If node hostname is not within 
		the etcd config's command keys,
		then the config change is ignored.
		"""
		if self.hostname in hosts.keys():
			return 0

		return 1

	def process_config(self):
		
		log = Logger(filename = "confman", \
                                                logger_name = "Process Config", \
                                                dirname="/aux1/occonfman/")
		if(self.check_affected(self.event_value["commands"])):
			print('This change does not concern my host: {}'.format(self.hostname))
			log.info("This config change does not concern my host {}".format(self.hostname))
			log.clear_handler()
			return ''
		log.info("Config change: {}".format(self.event_value["path"]))
		config_path = self.event_value["path"]
		content = self.apply_markers(self.event_value["content"])
		self.write_config(config_path, content)
		res = self.execute_command()
		log.clear_handler()

		return(res)

	def apply_markers(self, content):
		"""
		Using jinja2 template engine to replace markers within the config content
		"""
		
		log = Logger(filename = "confman", \
                                                logger_name = "Process Config", \
                                                dirname="/aux1/occonfman/")
		content_ready = content
		if "markers" in self.event_value.keys():
			for host in self.event_value["markers"]:
				if self.hostname in self.event_value["markers"].keys():
					template = jinja2.Template(content)
					log.info("Replacing markers for {}".format(self.hostname))
					log.clear_handler()
					content_ready = template.render(self.event_value["markers"][self.hostname])
		log.clear_handler()

		return content_ready

	def write_config(self, config_path, content):

		log = Logger(filename = "confman", \
                                                logger_name = "Process Config", \
                                                dirname="/aux1/occonfman/")
		try:
			with open(config_path, 'w') as conf:
				conf.write(content)
				conf.close()
		except:
			print(f"Could not write config file: { config_path }")
			log.error("Could not write config file {}".format(config_path))

		log.clear_handler()

	def execute_command(self):
		"""
		Executes all commands found in commands object
		Returns the output of executed commands
		"""

		results = {}
		log = Logger(filename = "confman", \
                                                logger_name = "Process Config", \
                                                dirname="/aux1/occonfman/")

		if self.hostname in self.event_value["commands"].keys():
			for command in self.event_value["commands"][self.hostname]:
				log.info("Executing command {}".format(command))
				res = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell = True)
				log.info("Command output: {}".format(res.stdout))
				log.clear_handler()
				results[command] = res.stdout

		self.return_status(results)
		log.clear_handler()

		return results

	def return_status(self, results):
		"""
		Writes status key in etcd
		Status key containes the executed command output as value
		"""
		
		log = Logger(filename = "confman", \
                                                logger_name = "Process Config", \
                                                dirname="/aux1/occonfman/")
		stat_path = self.status_path.rstrip('/') + self.event_value["path"] + '/' + str(self.event_revision) + '/' + self.hostname
		print(stat_path)
		log.info("Writing status key: {} , value: {}".format(stat_path,results))
		log.clear_handler()
		self.etcd.write(stat_path, str(results))

