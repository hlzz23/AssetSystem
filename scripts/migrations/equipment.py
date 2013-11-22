#!/usr/bin/env python
#-*- coding: utf-8 -*-

from _utils import connect_db, close_db, time_fmt, get_department

conn, old_db, new_db = connect_db()
depts = dict()
projects = dict()
sources = dict()

for dp in old_db.departments.find():
    depts[dp['_id']] = dp['name']

for pj in old_db.projects.find():
    projects[pj['_id']] = pj['name']

for source in old_db.sources.find():
    sources[source['_id']] = source['name']

for e in old_db.equipment.find():
    if not e['asset_no']:
        continue

    dept = depts[e['department_id']]
    dept_name = get_department(dept)
    if dept_name is None:
        print 'Invalid department - {}, {}'.format(dept, e['flex_id'])
        continue

    project = projects[e['project_id']]
    source = sources[e['source_id']].title()
    req_date = e.get('request_date', '')
    if req_date and hasattr(req_date, 'strftime'):
        req_date = req_date.strftime('%Y-%m-%d')

    doc = dict(_id=e['_id'],
               department=dept_name,
               project=project,
               source=source,
               sr=e['source_remark'],
               supplier=e['supplier'],
               mf=e['manufacturer'],
               name=e['name'],
               prod_date=e.get('prod_date', ''),
               desc=e['description'],
               flex_id=e['asset_no'],
               sn=e['sn'],
               fixed_id=e['fixed_asset_no'],
               tn=e['tracking_no'],
               cn=e['custom_no'],
               owner=e['owner'],
               model=e['model'],
               price=e['price'],
               line=e.get('line', ''),
               location=e['location'],
               ws=e['warranty_start'],
               we=e['warranty_end'],
               is_good=e['is_good'],
               is_instore=e['is_instore'],
               is_live=True,
               status=[],
               req_user=e.get('request_user', ''),
               req_date=req_date,
               req_remark=e.get('request_remark', ''),
               need_cal=e['need_cal'],
               need_pm=e['need_pm'],
               created_at=e['created_at'].strftime(time_fmt),
               updated_at=e['updated_at'].strftime(time_fmt),
               )

    new_db.equipment.save(doc)

close_db(conn)
