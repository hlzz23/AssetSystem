#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import os
import os.path
import tempfile

# from pyExcelerator import Workbook
from pymongo import Connection
from sendmail import send_mail
import mail_template as mt
import utils

conn, db = utils.get_connection()

spec = {'$or': [dict(min_alert={'$lt': 0}),
                dict(max_alert={'$lt': 0}),
                ]
        }
fields = ['code', 'department', 'project', 'store_good', 'store_bad', 'name',
          'min_store', 'max_store', 'out_good', 'out_bad',
          ]
codes = dict()

for sp in db.spareparts.find(spec, fields=fields):
    dp = sp['department']
    if dp not in codes:
        codes[dp] = dict()

    pj = sp['project']
    if pj not in codes[dp]:
        codes[dp][pj] = []

    codes[dp][pj].append(sp)

subject = 'Engineering Spare Parts QTY Alarm'
author = (('QTY Alarm', 'QTY.Alarm@cn.flextronics.com'))
line = '~' * 60
remark = 'This notification will be sent out from Monday to Friday'
no_leader = '''<h1><font color="red">
No project leader specified for:</font></h1><br />'''

css = dict(td_style=mt.td_style)
for dp, projects in codes.items():
    for pj, sps in projects.items():
        groups = utils.get_groups(db, dp, pj, role='project_leader')
        to_list = utils.get_users(db, groups, can_send='alarm')
        body = []
        if not to_list:
            groups = utils.get_groups(db, dp, pj, role='asset_leader')
            to_list = utils.get_users(db, groups)
            body.append(no_leader)

        body.append(mt.header.format(header=subject,
                                     department=dp,
                                     project=pj,
                                     )
                    )
        body.append(mt.table_header.format(table_style=mt.table_style,
                                           thead_style=mt.thead_style,
                                           tr_style=mt.tr_style,
                                           td_style=mt.td_style,
                                           )
                    )
        for i, sp in enumerate(sorted(sps)):
            body.append('<tr>')
            body.append(mt.td.format(data=i + 1, **css))
            body.append(mt.td.format(data=sp['code'], **css))
            body.append(mt.td.format(data=sp['name'], **css))
            body.append(mt.td.format(data=sp['min_store'], **css))
            body.append(mt.td.format(data=sp['max_store'], **css))
            body.append(mt.td.format(data=sp['store_good'], **css))
            body.append(mt.td.format(data=sp['store_bad'], **css))
            body.append(mt.td.format(data=sp['out_good'], **css))
            body.append(mt.td.format(data=sp['out_bad'], **css))
            body.append('</tr>')

        body.append(mt.footer)

        body.append('<br /><br />')
        body.append(line)
        body.append('<br />')
        body.append(remark)
        send_mail(subject=subject,
                  body=''.join(body),
                  author=author,
                  to=to_list,
                  )

utils.close_connection(conn)
