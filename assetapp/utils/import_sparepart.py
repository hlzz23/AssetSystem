#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import os
import os.path
from time import strftime
import tempfile
import xlrd
from flask import g, flash, render_template

from ..models.sparepart import Sparepart
from ..models.project import Project
from ..utils.import_utils import (check_empty, check_str, check_float,
                                  check_unique, show_dup_error,
                                  validate_headers, check_dup,
                                  check_int, get_department,
                                  )

from assetapp import t

required_keys = ('department', 'project', 'name', 'code', 'location')
qty_keys = ('code', )


def update_price(ws, maps, req_keys, file_path):
    '''store/asset user update price'''
    data = []
    codes = dict()
    errors = []
    error = False
    rv = dict()
    for i in range(1, ws.nrows):
        rv.clear()
        values = ws.row_values(i)
        if len(values) < len(maps):
            errors.append(t('invalid_row').format(row=i + 1))
            error = True
            continue

        for k in maps:
            v = values[maps[k]]
            if k == 'unit_price':
                if isinstance(v, float):
                    rv[k] = v
                elif isinstance(v, basestring) and v.strip():
                    rv[k] = v.strip()
            elif k == 'code':
                rv[k] = unicode(v).upper().strip()

                # make sure the fields are there
        for name in req_keys:
            if check_empty(name, rv[name], i, t, errors) is False:
                error = True

        sp = Sparepart.find_one(spec=dict(code=rv['code']))
        if not sp:
            errors.append(t('sparepart_not_exist').format(row=i + 1,
                                                          code=rv['code'],
                                                          )
                          )
            error = True
        else:
            # make sure the user can do this
            if not g.user.can_update_sparepart_price(sp.department,
                                                     sp.project):
                error = True
                errors.append(t('require_auth').format(row=i + 1,
                                                       dp=sp.department,
                                                       pj=sp.project,
                                                       )
                              )

        # check types
        #  > unit_price should be float
        if 'unit_price' in rv:
            if check_float('unit_price', rv['unit_price'],
                           i, t, errors) is False:
                error = True
            else:
                rv['unit_price'] = float(rv['unit_price'])

        # check unique
        #  > code should be unique in excel file
        err, code = check_dup('spareparts.code', rv, i, codes, t, errors)
        rv.update(code=code)
        if err is True:
            error = True

        if error is False:
            data.append(rv.copy())

    os.remove(file_path)
    if error is False:
        for row in data:
            sp = Sparepart.find_one(spec=dict(code=row['code']))
            row.pop('code')
            sp.save(doc=row, skip=True, update_ts=False)

            if not sp.is_valid:
                for k, v in sp._errors.items():
                    flash('{}: {}'.format(k, v), 'error')

    return error, errors


def update_qty(ws, maps, req_keys, file_path):
    '''asset user update qty'''
    data = []
    codes = dict()
    errors = []
    error = False
    rv = dict()
    for i in range(1, ws.nrows):
        rv.clear()
        values = ws.row_values(i)
        if len(values) < len(maps):
            errors.append(t('invalid_row').format(row=i + 1))
            error = True
            continue

        for k in maps:
            v = values[maps[k]]
            if k in ('store_good', 'store_bad', 'out_good', 'out_bad'):
                if isinstance(v, float):
                    rv[k] = v
                elif isinstance(v, basestring) and v.strip():
                    rv[k] = v.strip()

            elif k == 'code':
                rv[k] = unicode(v).upper().strip()

        # make sure the fields are there
        for name in req_keys:
            if check_empty(name, rv[name], i, t, errors) is False:
                error = True

        sp = Sparepart.find_one(spec=dict(code=rv['code']))
        if not sp:
            errors.append(t('sparepart_not_exist').format(row=i + 1,
                                                          code=rv['code'],
                                                          )
                          )
            error = True
        else:
            # make sure the user can do this
            if not g.user.can_update_sparepart_qty(sp.department, sp.project):
                error = True
                errors.append(t('require_auth').format(row=i + 1,
                                                       dp=sp.department,
                                                       pj=sp.project,
                                                       )
                              )

        # check types
        #  > store good qty should be int
        #  > store bad qty should be int
        #  > out good qty should be int
        #  > out bad qty should be int
        for k in ('store_good', 'store_bad', 'out_good', 'out_bad'):
            if k in rv:
                if check_int(k, rv[k], i, t, errors) is False:
                    error = True
                else:
                    rv[k] = int(float(rv[k]))

        # check unique
        #  > code should be unique in excel file
        err, code = check_dup('spareparts.code', rv, i, codes, t, errors)
        rv.update(code=code)
        if err is True:
            error = True

        if error is False:
            data.append(rv.copy())

    os.remove(file_path)
    if error is False:
        for row in data:
            sp = Sparepart.find_one(spec=dict(code=row['code']))
            row.pop('code')
            sp.save(doc=row, skip=True, update_ts=False)

            # update low/high limit
            sp.pre_store_alert()
            sp.save(doc=dict(min_alert=sp.min_alert,
                             max_alert=sp.max_alert,
                             ),
                    skip=True,
                    update_ts=False,
                    )
            if not sp.is_valid:
                for k, v in sp._errors.items():
                    flash('{}: {}'.format(k, v), 'error')

    return error, errors


def import_sparepart(ws, maps, req_keys, file_path, update):
    data = []
    codes = dict()
    errors = []
    error = False
    rv = dict()
    projects = [p.name for p in Project.find()]
    for i in range(1, ws.nrows):
        rv.clear()
        values = ws.row_values(i)
        if len(values) < len(maps):
            errors.append(t('invalid_row').format(row=i + 1))
            error = True
            continue

        for k in maps:
            v = values[maps[k]]
            if k in ('store_good', 'store_bad',
                     'out_good', 'out_bad',
                     'unit_price'):
                if isinstance(v, float):
                    rv[k] = v
                elif isinstance(v, basestring) and v.strip():
                    rv[k] = v.strip()
            elif k == 'department':
                rv[k] = get_department(unicode(v))
            else:
                rv[k] = unicode(v)

        if rv['project'] not in projects:
            error = True
            errors.append(t('project_not_found').format(row=i + 1,
                                                        pj=rv['project'],
                                                        )
                          )
            continue

        # make sure the fields are there
        for name in req_keys:
            if check_empty(name, rv[name], i, t, errors) is False:
                error = True

        # make sure the user can do this
        if not g.user.can_import_sparepart(rv['department'], rv['project']):
            error = True
            errors.append(t('require_auth').format(row=i + 1,
                                                   dp=rv['department'],
                                                   pj=rv['project'],
                                                   )
                          )
            continue

        # check types
        #  > unit price should be float
        #  > store good qty should be int
        #  > store bad qty should be int
        #  > out good qty should be int
        #  > out bad qty should be int
        #  > min store should be int
        #  > max store should be int
        if 'unit_price' in rv:
            if check_float('unit_price', rv['unit_price'], i, t, errors):
                rv.update(unit_price=float(rv['unit_price']))
            else:
                error = True

        for k in ('store_good', 'store_bad', 'out_good', 'out_bad',
                  'min_store', 'max_store'):
            if k in rv:
                if check_int(k, rv[k], i, t, errors):
                    rv[k] = int(float(rv[k]))
                else:
                    error = True

        # 4. check unique
        # 4.1 code should be unique in excel
        # notice: should be careful when 'updating'

        err, code = check_dup('spareparts.code', rv, i, codes, t, errors)
        rv.update(code=code)
        if err is True:
            error = True

        sp = Sparepart.find_one(spec=dict(code=code))
        if sp:
            if update:
                # store good qty, store bad qty
                # out good qty, out bad qty
                # can only be updated by asset user
                rv.pop('store_good', None)
                rv.pop('store_bad', None)
                rv.pop('out_good', None)
                rv.pop('out_bad', None)
            else:
                error = True
                errors.append(t('sparepart_exists').format(row=i + 1,
                                                           code=code,
                                                           )
                              )

        if error is False:
            data.append(rv.copy())

    os.remove(file_path)
    if error is False:
        for row in data:
            sp = Sparepart.find_one(spec=dict(code=row['code']))
            if sp:
                sp.update(**row)
            else:
                sp = Sparepart(**row)

            sp.pre_store_alert()
            sp.save(skip=True)
            if not sp.is_valid:
                for k, v in sp._errors.items():
                    flash('{}: {}'.format(k, v), 'error')

    return error, errors


def do_import(file_path, update=False, kind=0):
    # kind: 0 -> asset leader update qty
    #       1 -> store user import spare part
    #       2 -> update unit_price
    fn = file_path.split('_', 2)[-1]
    wb = xlrd.open_workbook(file_path)
    ws = wb.sheet_by_index(0)
    if ws.nrows < 1:
        os.remove(file_path)
        flash(t('invalid_format'), 'error')
        return render_template('spareparts/show_import.html',
                               file_name=fn,
                               error=True,
                               errors=None,
                               kind=kind,
                               )

    headers = ws.row_values(0)
    maps = parse_headers(headers, kind=kind)
    keys = required_keys if kind == 1 else qty_keys
    if validate_headers(maps, keys) is False:
        os.remove(file_path)
        flash(t('invalid_format'), 'error')
        return render_template('spareparts/show_import.html',
                               file_name=fn,
                               error=True,
                               errors=None,
                               kind=kind,
                               )

    if kind == 0:
        error, errors = update_qty(ws, maps, keys, file_path)
    elif kind == 1:
        error, errors = import_sparepart(ws, maps, keys, file_path, update)
    else:
        error, errors = update_price(ws, maps, keys, file_path)

    return render_template('spareparts/show_import.html',
                           file_name=fn,
                           error=error,
                           errors=errors,
                           kind=kind,
                           )


def parse_headers(headers, kind=0):
    # 部门    项目  名称  编号  位置  PN# 型号  产品型号
    # 仓库内数量(好)  仓库内数量(坏)    仓库外数量(好)    仓库外数量(坏)
    # 单价(USD)   供应商 描述  备注
    maps = dict()
    if kind == 0:
        for i, h in enumerate(headers):
            h = ('{}'.format(h)).replace('\n', '').strip().lower()
            if '编号' in h or 'code' in h:
                k = 'code'
            elif '仓库内数量' in h:
                k = 'store_good' if '好' in h else 'store_bad'
            elif '仓库外数量' in h:
                k = 'out_good' if '好' in h else 'out_bad'
            elif 'store good' in h:
                k = 'store_good'
            elif 'store bad' in h:
                k = 'store_bad'
            elif 'outside good' in h:
                k = 'out_good'
            elif 'outside bad' in h:
                k = 'out_bad'
            else:
                continue

            if k not in maps:
                maps[k] = i

        return maps

    # kind == 2
    if kind == 2:
        for i, h in enumerate(headers):
            h = ('{}'.format(h)).replace('\n', '').strip().lower()
            if '编号' in h or 'code' in h:
                k = 'code'
            elif '单价' in h or 'unit price' in h:
                k = 'unit_price'
            else:
                continue

            if k not in maps:
                maps[k] = i

        return maps

    # kind == 1
    for i, h in enumerate(headers):
        h = ('{}'.format(h)).replace('\n', '').strip().lower()
        if '部门' in h or 'department' in h:
            k = 'department'
        elif '项目' in h or 'project' in h:
            k = 'project'
        elif '名称' in h or 'name' in h:
            k = 'name'
        elif '编号' in h or 'code' in h:
            k = 'code'
        elif '位置' in h or 'location' in h:
            k = 'location'
        elif 'pn#' in h or '料号' in h:
            k = 'pn'
        elif '产品型号' in h or 'product model' in h:
            k = 'prod_model'
        elif '型号' in h or 'model' in h:
            k = 'model'
        elif '仓库内数量' in h:
            k = 'store_good' if '好' in h else 'store_bad'
        elif '仓库外数量' in h:
            k = 'out_good' if '好' in h else 'out_bad'
        elif 'store good' in h:
            k = 'store_good'
        elif 'store bad' in h:
            k = 'store_bad'
        elif 'outside good' in h:
            k = 'out_good'
        elif 'outside bad' in h:
            k = 'out_bad'
        elif '下限' in h or 'low limit' in h:
            k = 'min_store'
        elif '上限' in h or 'high limit' in h:
            k = 'max_store'
        elif '单价' in h or '价格' in h or 'price' in h:
            k = 'unit_price'
        elif '供应商' in h or 'vendor' in h:
            k = 'vendor'
        elif '描述' in h or 'description' in h:
            k = 'desc'
        elif '备注' in h or 'remark' in h:
            k = 'remark'
        else:
            continue

        if k not in maps:
            maps[k] = i

    return maps
