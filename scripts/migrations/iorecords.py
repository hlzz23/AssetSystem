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


def get_asset(id, kind):
    spec = dict(_id=id)
    if kind == 'equipment':
        return old_db.equipment.find_one(spec)

    return old_db.spcodes.find_one(spec)


def get_user(id):
    return old_db.users.find_one(dict(_id=id))

for io in old_db.iorecords.find():
    if io['department_id'] not in depts:
        print 'Department not found, {}'.format(io['department_id'])
        continue

    dept = depts[io['department_id']]
    dept_name = get_department(dept)
    if dept_name is None:
        print 'Invalid department - {}, {}'.format(dept, io['_id'])
        continue

    project = projects[io['project_id']]
    user = get_user(io['user_id'])
    if user:
        login = user['full_name']
        login_id = user['badge_id']
    else:
        print 'user not found, {}'.format(io['_id'])
        continue

    kind = '0' if io['asset_type'] == 'equipment' else '1'
    obj = get_asset(io['asset_id'], kind=io['asset_type'])
    if obj:
        if kind == '0':  # equipment
            name = obj['name']
            asset = dict(iogood=io['good_qty'] == 0,
                         flex_id=obj['asset_no'],
                         sn=obj['sn'],
                         fixed_id=obj['fixed_asset_no'],
                         model=obj.get('model', ''),
                         )

            if not io['is_out']:
                asset.update(back_to=obj['location'])
        else:
            name = obj['description']
            asset = dict(code=obj['code'],
                         pn=obj.get('pn', ''),
                         iogood=io['good_qty'],
                         iobad=io['bad_qty'],
                         )

        if io['is_out']:
            asset.update(to_project=io.get('to_project', ''),
                         to_where=io.get('to_where', ''),
                         to_line=io.get('to_line', io.get('to_where', '')),
                         )
    else:
        print 'asset not found, {} - {}'.format(io['asset_type'],
                                                io['asset_id']
                                                )
        continue

    doc = dict(_id=io['_id'],
               department=dept_name,
               project=project,
               login=login,
               login_id=login_id,
               user=io['io_user_name'],
               uid=io['io_user_id'],
               date=io['io_date'].strftime('%Y-%m-%d'),
               is_out=io['is_out'],
               kind=kind,
               name=name,
               hard_copy=io.get('hard_copy_no', ''),
               remark=io['remark'],
               asset=asset,
               created_at=io['created_at'].strftime(time_fmt),
               updated_at=io['updated_at'].strftime(time_fmt),
               )
    new_db.iorecords.save(doc)

close_db(conn)
