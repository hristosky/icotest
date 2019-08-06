import socket
import threading
import sys
import ipaddress
from pprint import pprint

subnet = '10.102.7.0/24'
port_number = 22
delay = 5
output = {}
threads = []

if(len(sys.argv) > 1):
	subnet = sys.argv[1]
else:
	print('Using default values for subnet/port/delay')

def check_port(ip):
	str(ip)
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.settimeout(delay)
	try:
		res = sock.connect(('{}'.format(ip), port_number))
		print('{} is OK'.format(ip))
	except:
		pass

net4 = ipaddress.ip_network('{}'.format(subnet),strict = False)
for i,x in enumerate(net4.hosts()):
	t = threading.Thread(target=check_port, args=(x,))
	threads.append(t)
	t.start()

#print(output)