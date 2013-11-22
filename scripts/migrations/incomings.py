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


def get_asset(id, kind):
    spec = dict(_id=id)
    if kind == 'equipment':
        return old_db.equipment.find_one(spec)

    return old_db.spcodes.find_one(spec)


def get_user(id):
    return old_db.users.find_one(dict(_id=id))

for buy in old_db.acceptings.find():
    if 'asset_id' not in buy:
        continue

    obj = get_asset(buy['asset_id'], kind=buy['asset_type'])
    if not obj:
        print 'asset not found, {}'.format(buy['_id'])
        continue

    user = get_user(buy['user_id'])
    if user:
        login = user['full_name']
        login_id = user['badge_id']
    else:
        print 'user not found, {}'.format(buy['_id'])
        continue

    kind = '0' if buy['asset_type'] == 'equipment' else '1'
    if kind == '0':
        name = obj['name']
        tn = obj.get('tracking_no', '')
        cn = obj.get('custom_no', '')
        ws = obj['warranty_start']
        we = obj['warranty_end']
        asset = dict(sn=obj['sn'],
                     location=obj['location'],
                     desc=obj['description'],
                     ws=ws.strftime('%Y-%m-%d') if ws else '',
                     we=we.strftime('%Y-%m-%d') if we else '',
                     is_good=buy['good_qty'] == 1,
                     flex_id=obj['asset_no'],
                     fixed_id=obj['fixed_asset_no'],
                     )
    else:
        name = obj['description']
        tn = ''
        cn = ''
        asset = dict(code=obj['code'],
                     desc=obj['description'],
                     good=buy['good_qty'],
                     bad=buy['bad_qty'],
                     )

    if 'route' in buy:
        confirm = buy['route'].get('confirm', False)
        approve = buy['route'].get('approve', False)
        if kind == '0':
            if approve:
                workflow = 'done'
            elif confirm:
                workflow = 'accept'
            else:
                workflow = 'fresh'
        else:
            if confirm:
                workflow = 'done'
            else:
                workflow = 'fresh'

    else:
        confirm = False
        approve = False
        workflow = 'fresh'

    history = []
    for h in buy['history']:
        if 'is_approve' in h:
            accept = h['is_approve']
            flow = '2'
        else:
            accept = h['is_accept']
            flow = '1'

        item = dict(time=h['time'].strftime(time_fmt),
                    accept=accept,
                    remark=h['reject_remark'],
                    flow=flow,
                    )
        user = get_user(h['user_id'])
        if user:
            item.update(user=user['full_name'])
        else:
            item.update(user='')

        history.append(item)

    doc = dict(_id=buy['_id'],
               login=login,
               login_id=login_id,
               department=get_department(depts[obj['department_id']]),
               project=projects[obj['project_id']],
               source=sources[buy['source_id']].title(),
               source_remark=buy['source_remark'],
               po=buy['po_no'],
               mf=buy['manufacturer'],
               supplier=buy['supplier'],
               model=obj.get('model', ''),
               owner=obj.get('owner', ''),
               price=buy['price'],
               date=buy['buy_date'].strftime('%Y-%m-%d'),
               tn=tn,
               cn=cn,
               kind=kind,
               name=name,
               asset=asset,
               history=history,
               workflow=workflow,
               remark=buy['remark'],
               created_at=buy['created_at'].strftime(time_fmt),
               updated_at=buy['updated_at'].strftime(time_fmt),

               )
    new_db.buys.save(doc)

close_db(conn)
