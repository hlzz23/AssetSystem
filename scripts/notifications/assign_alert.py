#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import utils
from sendmail import send_mail

conn, db = utils.get_connection()
spec = dict(kind='0', workflow='accept')
users = dict()
for buy in db.buys.find(spec):
    dept = buy['department']
    proj = buy['project']
    if dept not in users:
        users[dept] = dict()

    if proj not in users[dept]:
        users[dept][proj] = 0

    users[dept][proj] += 1

subject = 'Need to assign Flex Asset ID'
author = (('Assign Flex ID Notification',
          'Assign.Notification@cn.flextronics.com')
          )
body_title = '<h1>There are {} assets need assign Flex Asset ID:</h1>'
no_leader_title = '''<h1><font color="red">
But no asset user is specified.</font></h1>'''
line = '~' * 60
dept_fmt = '&raquo; Department: <strong>{}</strong><br />'
proj_fmt = '&raquo; Project: <strong>{}</strong>'
url = '''More details on <a href='http://{ip}/buys/?routing=accept'>
http://{ip}/buys/?routing=accept</a> or
<a href='http://teasset/buys/?routing=accept'>
http://teasset/buys/?routing=accept</a>.
'''.format(ip=utils.get_ip())
remark = '''This notification will be sent out from Monday to Friday'''

for dept, projects in users.items():
    for proj, num in projects.items():
        groups = utils.get_groups(db, dept, proj, role='asset_user')
        to_list = utils.get_users(db, groups)
        body = [body_title.format(num)]
        if to_list:
            body.append(url)
        else:
            body.append(no_leader_title)
            groups = utils.get_groups(db, dept, proj, role='asset_leader')
            to_list = utils.get_users(db, groups)

        body.append(dept_fmt.format(dept))
        body.append(proj_fmt.format(proj))
        body.append('<br />')
        body.append(line)
        body.append(remark)
        send_mail(subject=subject,
                  body='<br />'.join(body),
                  author=author,
                  to=to_list,
                  )

utils.close_connection(conn)
