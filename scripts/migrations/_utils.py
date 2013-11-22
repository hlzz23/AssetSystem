#!/usr/bin/env python
#-*- coding: utf-8 -*-

from pymongo import Connection
time_fmt = '%Y-%m-%d %H:%M:%S'


def connect_db():
    conn = Connection()
    return conn, conn.engasset, conn.flexasset


def close_db(conn):
    conn.disconnect()


def get_department(name):
    if 'EE' in name:
        return 'EE'
    elif 'TE' in name:
        return 'TE'
    elif 'PE' in name:
        return 'PE'
    else:
        return None
