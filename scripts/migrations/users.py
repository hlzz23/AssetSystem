#!/usr/bin/env python
#-*- coding: utf-8 -*-

from _utils import connect_db, close_db, time_fmt

conn, old_db, new_db = connect_db()

can_send = ['buy', 'io', 'tf', 'idle', 'scrap', 'alarm', 'notify']
spec = dict(is_locked=False)
for user in old_db.users.find(spec):
    new_db.users.save(dict(_id=user['_id'],
                           login=user['username'],
                           nick_name=user['full_name'],
                           hash_pass=user['hash_pass'],
                           email=user['email'],
                           badge_id=user['badge_id'],
                           lang=user['lang'],
                           gsm=user['mobile'],
                           phone=user['office_no'],
                           short_no=user['short_no'],
                           is_active=True,
                           can_send=can_send,
                           groups=[],
                           created_at=user['created_at'].strftime(time_fmt),
                           updated_at=user['updated_at'].strftime(time_fmt),
                           ))

close_db(conn)
