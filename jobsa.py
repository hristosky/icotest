import os
import re
from sys import argv
import requests
from pprint import pprint
import MySQLdb as mysqldb
import smtplib

_,keyword, mailme = argv
mysql_user = "perluser"
mysql_pwd = "koikaravlaka"
database = "jobsa"
frommail = 'futureyou@yournewjob.com'
tomail = 'hristo.slavov@opencode.com'
job_site = 'https://www.jobs.bg'
url = 'https://www.jobs.bg/front_job_search.php?first_search=1&distance=0&location_sid=1&categories[]=15&categories[]=16&categories[]=43&all_type=0&all_position_level=1&keyword={}'.format(keyword)
db = mysqldb.connect(host = "localhost", user = mysql_user, passwd = mysql_pwd, db=database)
cur = db.cursor()
r = requests.get(url)
page_status = r.status_code
newjobs = []
if page_status == 200:
	content = r.text
	links = list(set(re.findall('<a\shref=\"job\/(\d{1,10}?)\"\sclass=\"joblink\".*?>(.*?)<\/a>',content)))
	pages = set(re.findall('a\shref=\"(.*?)\"\s*class=pathlink',content))
	for id,page in enumerate(pages):
		newr = requests.get('{}{}'.format(job_site,page))
		newlinks = list(set(re.findall('<a\shref=\"job\/(\d{1,10}?)\"\sclass=\"joblink\".*?>(.*?)<\/a>',newr.text)))
		links += newlinks
	for j in links:
		cur.execute("SELECT offer_id FROM offers WHERE offer_id = {}".format(j[0]))
		result = cur.fetchone()
		if not result:
			# write to db, send mail
			joburl = job_site + '/job/'+ j[0]
			nr = requests.get(joburl)
			if nr.text:
				title = re.sub('[^a-zA-Z0-9\s]', '', j[1])
				cur.execute("insert into offers (offer_id, title) values({}, '{}')".format(j[0], title))
				db.commit()
				mail = smtplib.SMTP('localhost')
				message = ('To: {}\n'.format(tomail))
				message += ('From: {}\n'.format(frommail))
				message += ('Subject: {}\n'.format(title))
				message += ('Content-type: text/html\n')
				message += ('{}'.format(nr.text))
				mail.sendmail(frommail, tomail, message.encode('utf-8').strip())
else:
	print('Main search page is not loading OK for some reason. Apache responded with code: {}'.format(page_status))
db.close()