#!/usr/bin/env python
#-*- coding: utf-8 -*-

from _utils import connect_db, close_db, time_fmt, get_department

conn, old_db, new_db = connect_db()
depts = dict()
projects = dict()

for dp in old_db.departments.find():
    depts[dp['_id']] = dp['name']

for pj in old_db.projects.find():
    projects[pj['_id']] = pj['name']

for sp in old_db.spcodes.find():
    dept = depts[sp['department_id']]
    dept_name = get_department(dept)
    if dept_name is None:
        print 'Invalid department - {}, {}'.format(dept, sp['code'])
        continue

    project = projects[sp['project_id']]
    out_good = sp['outside_good']
    out_bad = sp['outside_bad']
    if out_good < 0:
        out_good = 0

    if out_bad < 0:
        out_bad = 0

    min_store = sp['min_store']
    if min_store > 0:
        min_alert = sp['good_qty'] - min_store
    else:
        min_alert = 0

    doc = dict(_id=sp['_id'],
               department=dept_name,
               project=project,
               name=sp['description'],
               code=sp['code'],
               model=sp['model'],
               location=sp['location'],
               desc=sp['description'],
               remark='',
               prod_model=sp.get('prod_model', ''),
               pn=sp.get('pn', ''),
               store_good=sp['good_qty'],
               store_bad=sp['bad_qty'],
               out_good=out_good,
               out_bad=out_bad,
               buy_good=sp['buy_good'],
               buy_bad=sp['buy_bad'],
               min_store=sp['min_store'],
               max_store=0,
               is_local=sp['is_local'],
               lead_time=sp['lead_time'],
               mcq=sp['month_consumed'],
               npq=sp['next_purchase_qty'],
               cqdp=sp['consumed_during_purchase'],
               unit_price=sp.get('price', 0.0),
               vendor=sp.get('vendor', sp['supplier']),
               min_alert=min_alert,
               max_alert=0,
               created_at=sp['created_at'].strftime(time_fmt),
               updated_at=sp['updated_at'].strftime(time_fmt),
               )
    new_db.spareparts.save(doc)

close_db(conn)
