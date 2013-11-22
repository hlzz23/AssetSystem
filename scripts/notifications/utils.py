#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import os
from pymongo import Connection

cmd = """/sbin/ifconfig eth0 |awk '/inet/ {split($2,x,":");print x[2]}'"""


def get_connection():
    conn = Connection()
    return conn, conn.flexasset


def close_connection(conn):
    conn.disconnect()


def get_ip():
    return os.popen(cmd).read().strip()


def get_groups(db, dp, pj, role='project_leader'):
    spec = dict(is_active=True,
                role=role,
                department={'$in': ['*', dp]},
                projects=pj,
                )
    return [p['group'] for p in db.permissions.find(spec)]


def get_users(db, groups, can_send=None):
    spec = dict(is_active=True,
                groups={'$in': groups},
                email={'$ne': ''},
                )
    if can_send:
        spec.update(can_send=can_send)

    return [u['email'].split('@')[0] for u in db.users.find(spec)]
