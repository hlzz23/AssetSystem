#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import os
import os.path
from time import strftime
import tempfile
import xlrd
from flask import g, flash, render_template

from ..models.equipment import Equipment
from ..models.project import Project
from ..utils.import_utils import (check_empty, check_str, check_float,
                                  check_unique, show_dup_error,
                                  validate_headers, check_dup,
                                  get_date, get_department,
                                  )

from assetapp import t

required_keys = ('department', 'project', 'source', 'name', 'flex_id',
                 'sn', 'is_good', 'is_instore',
                 )


def do_import(file_path, update=False):
    fn = file_path.split('_', 2)[-1]
    wb = xlrd.open_workbook(file_path)
    ws = wb.sheet_by_index(0)
    if ws.nrows < 1:
        os.remove(file_path)
        flash(t('invalid_format'), 'error')
        return render_template('equipment/show_import.html',
                               file_name=fn,
                               error=True,
                               errors=None,
                               )

    headers = ws.row_values(0)
    maps = parse_headers(headers)
    if validate_headers(maps, required_keys) is False:
        os.remove(file_path)
        flash(t('invalid_format'), 'error')
        return render_template('equipment/show_import.html',
                               file_name=fn,
                               error=True,
                               errors=None,
                               )

    # validations
    # 1. check_permission - make sure the user can do this
    # 2. check_empty - make sure required fields are there
    # 3. check_types (int, float, str, etc.)
    # 4. check_unique - make sure the value is unique in the db

    # get projects map
    projects = [p.name for p in Project.find()]
    data = []
    flex_ids = dict()
    sns = dict()
    fixed_ids = dict()
    errors = []
    error = False
    rv = dict()
    spec = dict()
    for i in range(1, ws.nrows):
        rv.clear()
        values = ws.row_values(i)
        if len(values) < len(maps):
            errors.append(t('invalid_row').format(row=i + 1))
            error = True
            continue

        for k in maps:
            v = values[maps[k]]
            if k == 'price':
                if isinstance(v, float):
                    rv[k] = v
                elif isinstance(v, basestring) and v.strip():
                    rv[k] = v.strip()
            elif k == 'department':
                rv[k] = get_department(unicode(v))
            elif k == 'source':
                rv[k] = unicode(v).strip().title()
            elif k in ('tn', 'cn'):
                rv[k] = unicode(v)
                if isinstance(v, (float, int)):
                    rv[k] = rv[k].split('.')[0]
            elif k in ('prod_date', 'req_date'):
                rv[k] = get_date(v)
            else:
                rv[k] = unicode(v)

        if rv['project'] not in projects:
            error = True
            errors.append(t('project_not_found').format(row=i + 1,
                                                        pj=rv['project'],
                                                        )
                          )
            continue

        # 1. make sure the user can do this
        if not g.user.can_import_equipment(rv['department'], rv['project']):
            error = True
            errors.append(t('require_auth').format(row=i + 1,
                                                   dp=rv['department'],
                                                   pj=rv['project'],
                                                   )
                          )
            continue

        # 2. make sure the fields are there
        for name in required_keys:
            if check_empty(name, rv[name], i, t, errors) is False:
                error = True

        # 3. check types
        # price should be float
        if 'price' in rv:
            if check_float('price', rv['price'], i, t, errors) is False:
                error = True
            else:
                rv.update(price=float(rv['price']))

        # 4. check unique
        # flex_id, sn, [fixed_id] should be unique in db
        # notice: should be careful when 'updating'

        # 4.1 flex_id
        err, flex_id = check_dup('flex_id', rv, i, flex_ids, t, errors)
        if flex_id:
            rv.update(flex_id=flex_id)
            if err is True:
                error = True

            spec.update(flex_id=flex_id)
            if check_unique(Equipment, 'flex_id', i, spec,
                            t, errors, update=update) is False:
                error = True

            spec.pop('flex_id')

        # 4.2 sn
        err, sn = check_dup('sn', rv, i, sns, t, errors)
        if sn:
            rv.update(sn=sn)
            if err is True:
                error = True

            spec.update(sn=sn)
            if check_unique(Equipment, 'sn', i, spec,
                            t, errors, update) is False:
                error = True

            spec.pop('sn')

        # 4.3 fixed_id [optional]
        if 'fixed_id' in rv:
            fixed_id = rv['fixed_id']
            if isinstance(fixed_id, (int, float)):
                fixed_id = unicode(float(fixed_id)).split('.')[0]

            fixed_id = fixed_id.strip().upper()
            if fixed_id:
                rv.update(fixed_id=fixed_id)
                if fixed_id not in fixed_ids:
                    fixed_ids[fixed_id] = []
                else:
                    error = True
                    lines = [l[0] for l in fixed_ids[val]]
                    show_dup_error('fixed_id', fixed_id, i, t,
                                   lines, errors)

                spec.update(fixed_id=fixed_id)
                if check_unique(Equipment, 'fixed_id', i, spec,
                                t, errors, update=update) is False:
                    error = True

        if 'is_good' in rv:
            is_good = rv['is_good'].upper()
            if '坏' in is_good or 'N' in is_good:
                rv.update(is_good=False)
            else:
                rv.update(is_good=True)

        if 'is_instore' in rv:
            is_instore = rv['is_instore'].upper()
            if '否' in is_instore or 'N' in is_instore:
                rv.update(is_instore=False)
            else:
                rv.update(is_instore=True)

        if error is False:
            data.append(rv.copy())

    os.remove(file_path)
    if error is False:
        spec = dict()
        for row in data:
            if update is True:
                spec.update(flex_id=row['flex_id'])
                ep = Equipment.find_one(spec=spec)
                if ep:  # already exists, update it
                    ep.update(**row)
                else:
                    ep = Equipment(**row)
            else:
                ep = Equipment(**row)

            ep.save(skip=True)
            if not ep.is_valid:
                for k, v in ep._errors.items():
                    flash('{}: {}'.format(k, v), 'error')

    return render_template('equipment/show_import.html',
                           file_name=fn,
                           error=error,
                           errors=errors,
                           )


def parse_headers(headers):
    # 部门    项目  来源  来源说明    供应商 制造商 名称  生产日期
    # 伟创力编号 序列号 固定资产编号  追踪编号    海关号 责任人 型号
    # 价格  线别  位置  保修开始    保修结束    好或坏?    仓库内?
    # 申请人 申请日期    申请备注    描述

    maps = dict()
    for i, h in enumerate(headers):
        h = ('{}'.format(h)).replace('\n', '').strip().lower()
        if '部门' in h or 'department' in h:
            k = 'department'
        elif '项目' in h or 'project' in h:
            k = 'project'
        elif '来源说明' in h or 'source remark' in h:
            k = 'sr'
        elif '来源' in h or 'source' in h:
            k = 'source'
        elif '供应商' in h or 'supplier' in h or 'vendor' in h:
            k = 'supplier'
        elif '制造商' in h or 'manufacturer' in h:
            k = 'mf'
        elif '名称' in h or 'name' in h:
            k = 'name'
        elif '生产日期' in h or 'production date' in h:
            k = 'prod_date'
        elif '伟创力编号' in h or 'flex id' in h:
            k = 'flex_id'
        elif '序列号' in h or 'sn#' in h:
            k = 'sn'
        elif '固定资产' in h or 'fixed' in h:
            k = 'fixed_id'
        elif '追踪' in h or 'track' in h:
            k = 'tn'
        elif '海关' in h or 'custom' in h:
            k = 'cn'
        elif '责任人' in h or 'owner' in h:
            k = 'owner'
        elif '型号' in h or 'model' in h:
            k = 'model'
        elif '价格' in h or 'price' in h:
            k = 'price'
        elif '线别' in h or 'line' in h:
            k = 'line'
        elif '位置' in h or 'location' in h:
            k = 'location'
        elif '保修开始' in h or 'warranty start' in h:
            k = 'ws'
        elif '保修结束' in h or 'warranty end' in h:
            k = 'we'
        elif '好或坏' in h or 'good' in h:
            k = 'is_good'
        elif '仓库内' in h or 'in store' in h:
            k = 'is_instore'
        elif '申请人' in h or 'request user' in h:
            k = 'req_user'
        elif '申请日期' in h or 'request date' in h:
            k = 'req_date'
        elif '申请备注' in h or 'request remark' in h:
            k = 'req_remark'
        elif '描述' in h or 'description' in h:
            k = 'desc'
        else:
            continue

        if k not in maps:
            maps[k] = i

    return maps
