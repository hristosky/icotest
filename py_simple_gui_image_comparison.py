import PySimpleGUI as sg
import os
import re
import imghdr
layout = [[sg.Text('Filename')],
			[sg.Input(), sg.FolderBrowse()],
			[sg.OK(), sg.Cancel()] ]

event, (number) = sg.Window('Get filename example', layout).Read()
found = {}
chunk = ""
interval = 5000
count = 10
start = 10000
chunk_size = 10
dirlist = {}

def get_chunks(start, interval, chunk_size, count, filepath, filesize):
	chunks = ""
	with open(filepath, 'rb') as f:
		for i in range(count):
			chs = start + i*interval
			if filesize > chs:
				f.seek(chs)
				chunks += str(f.read(chunk_size))
	return chunks

if os.path.exists(number[0]):
	for directory_name, _, file_list in os.walk(number[0]):
		for fname in file_list:
			fullpath = os.path.join(directory_name, fname)
			fsize = os.path.getsize(fullpath)
			imgtype = imghdr.what(fullpath)
			if fname.startswith(".") or not imgtype:
				continue
			dirlist[fullpath] = ""
			chunk = get_chunks(start, interval, chunk_size, count, fullpath, fsize)
			if chunk not in dirlist.values():
				dirlist[fullpath] = chunk
			else:
				for ckey,cval in dirlist.items():
					if chunk == cval:
						found[fullpath] = ckey
else:
	print("no such dir")
sg.PopupScrolled(found)