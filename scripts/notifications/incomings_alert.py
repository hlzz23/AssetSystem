#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from pymongo import Connection
import utils
from sendmail import send_mail

conn, db = utils.get_connection()

users = dict()
spec = dict(workflow='fresh')
for buy in db.buys.find(spec):
    dept = buy['department']
    proj = buy['project']
    if dept not in users:
        users[dept] = dict()

    if proj not in users[dept]:
        users[dept][proj] = 0

    users[dept][proj] += 1

subject = 'Your project has new incomings'
author = (('Incomings Notification',
          'Incomings.Notification@cn.flextronics.com')
          )
body_title = '<h1>There are {} incomings:</h1>'
no_leader = '<h1>But no project leader is specified.</h1>'
line = '~' * 60
dept_fmt = '&raquo; Department: <strong>{}</strong><br />'
proj_fmt = '&raquo; Project: <strong>{}</strong><br />'
url = '''More details on <a href='http://{ip}/buys/?routing=fresh'>
http://{ip}/buys/?routing=fresh</a> or
<a href='http://teasset/buys/?routing=fresh'>
http://teasset/buys/?routing=fresh</a>.
'''.format(ip=utils.get_ip())
remark = '''This notification will be sent out from Monday to Friday'''

for dept, projects in users.items():
    for proj, num in projects.items():
        groups = utils.get_groups(db, dept, proj)
        to_list = utils.get_users(db, groups, can_send='notify')
        body = [body_title.format(num)]
        body.append(dept_fmt.format(dept))
        body.append(proj_fmt.format(proj))
        if to_list:
            body.append(url)
        else:
            body.append(no_leader)
            groups = utils.get_groups(db, dept, proj, role='asset_leader')
            to_list = utils.get_users(db, groups)

        body.append('<br />')
        body.append(line)
        body.append(remark)
        send_mail(subject=subject,
                  body='<br />'.join(body),
                  author=author,
                  to=to_list,
                  )

utils.close_connection(conn)
