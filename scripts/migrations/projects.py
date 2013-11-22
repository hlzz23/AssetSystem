#!/usr/bin/env python
#-*- coding: utf-8 -*-

from _utils import connect_db, close_db, time_fmt

conn, old_db, new_db = connect_db()

for pj in old_db.projects.find():
    new_db.projects.save(dict(_id=pj['_id'],
                              name=pj['name'],
                              remark=pj['description'],
                              created_at=pj['created_at'].strftime(time_fmt),
                              updated_at=pj['updated_at'].strftime(time_fmt),
                              )
                         )

close_db(conn)
