#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import os
import os.path
from datetime import datetime
from time import strftime
import re
from math import ceil
import tempfile
import xlrd
from pyExcelerator import Workbook
from werkzeug import secure_filename
from flask import (Blueprint, g, request, session, url_for, redirect,
                   render_template, flash, send_from_directory,
                   )

from ..models.sparepart import Sparepart
from ..models.buy import Buy
from ..models.iorecord import Iorecord
from ..models.transfer import Transfer
from ..forms.sparepart import (SparepartForm, StockForm, ExportForm,
                               QueryForm, ImportForm,
                               )
from ..utils.general import (fill_form_error, set_referrer, get_referrer,
                             handle_uploads,
                             )
from ..utils.auth import login_required, role_required
from ..utils.select import department_choices, project_choices
from ..utils.import_sparepart import do_import

from assetapp import t

mod = Blueprint('spareparts', __name__)


@mod.route('/')
@login_required
def index():
    get_referrer()
    spec = dict()
    search = False
    keyword = request.args.get('keyword', '').strip()
    if keyword:
        spec['$or'] = get_keyword_spec(keyword)
        search = True

    for k in ('department', 'project'):
        value = request.args.get(k, '').strip()
        if value:
            spec[k] = re.compile(value, re.I)
            search = True

    status = request.args.get('status', '')
    if status:
        if status == 'ok':
            spec.update(min_alert={'$gt': 0}, max_alert={'$gt': 0})
        else:
            spec['$or'] = [dict(min_alert={'$lt': 0}),
                           dict(max_alert={'$lt': 0}),
                           ]

    dp = request.args.get('dp', '')
    pj = request.args.get('pj', '')
    word = request.args.get('word', '').strip()
    form = QueryForm(request.form,
                     dp=dp,
                     pj=pj,
                     word=word,
                     )
    form.dp.choices = department_choices()
    form.pj.choices = project_choices(with_all=True)
    if dp:
        spec.update(department=dp)
        search = True

    if pj:
        spec.update(project=pj)
        search = True

    if word:
        spec['$or'] = get_keyword_spec(word)
        search = True

    session['spspec'] = spec
    spareparts = Sparepart.find(spec=spec,
                                sort='code',
                                search=search,
                                paginate=True,
                                total='docs',
                                )
    return render_template('spareparts/index.html',
                           spareparts=spareparts,
                           keyword=keyword,
                           total_qty=Sparepart.total_count(),
                           ok_qty=Sparepart.ok_qty(),
                           danger_qty=Sparepart.danger_qty(),
                           status=status,
                           form=form,
                           word=word,
                           )


@mod.route('/show/<id>')
@login_required
def show(id):
    sp = Sparepart.find_one(id)
    if sp is None:
        flash(t('record_not_found', 'error'))
        return redirect(request.referrer or url_for('.index'))

    return render_template('spareparts/show.html',
                           sp=sp,
                           )


@mod.route('/new', methods=('GET', 'POST'))
@role_required('store_user')
def new():
    form = SparepartForm()
    form.department.choices = department_choices()
    form.project.choices = project_choices(g.user.is_root)
    if form.validate_on_submit():
        sp = Sparepart()
        update_part(sp, form, True)
        sp.save()
        if sp.is_valid:
            handle_uploads(str(sp.id))
            flash(t('created_successfully'), 'success')
            return redirect(url_for('.index'))

        fill_form_error(form, sp)

    return render_template('spareparts/new.html',
                           form=form,
                           )


@mod.route('/edit/<id>', methods=('GET', 'POST'))
@login_required
def edit(id):
    sp = Sparepart.find_one(id)
    if sp is None:
        flash(t('record_not_found'), 'error')
        return redirect(request.referrer)

    if not g.user.can_edit_sparepart(sp):
        flash(t('permission_denied'), 'error')
        return redirect(request.referrer)

    doc = sp.dict
    can_edit_qty = sp.can_edit_qty
    form = SparepartForm(request.form, **doc)
    form.department.choices = department_choices()
    form.project.choices = project_choices(with_all=g.user.is_root)
    if form.validate_on_submit():
        update_part(sp, form, can_edit_qty)
        sp.save()
        if sp.is_valid:
            handle_uploads(str(sp.id))
            flash(t('updated_successfully'), 'success')
            return redirect(url_for('.index'))

        fill_form_error(form, sp)

    return render_template('spareparts/edit.html',
                           form=form,
                           can_edit_qty=can_edit_qty,
                           sp=sp,
                           )


@mod.route('/destroy/<id>')
@login_required
def destroy(id):
    sp = Sparepart.find_one(id)
    if sp is None:
        flash(t('record_not_found'), 'error')
    elif g.user.can_remove_sparepart(sp):
        if sp.canbe_removed:
            sp.destroy()
            [up.destroy() for up in sp.uploads]

            flash(t('destroyed_successfully'), 'success')
        else:
            flash(t('cannot_be_removed'), 'error')

    else:
        flash(t('permission_denied'), 'error')

    return redirect(request.referrer)


@mod.route('/setstock/<id>', methods=('GET', 'POST'))
@login_required
def set_stock(id):
    set_referrer()
    sp = Sparepart.find_one(id)
    if sp is None:
        flash(t('record_not_found'), 'error')
        return redirect(get_referrer())

    if not g.user.can_set_stock(sp):
        flash(t('permission_denied'), 'error')
        return redirect(get_referrer())

    data = sp.dict
    data.update(is_local='local' if data['is_local'] else 'oversea')
    if data['mcq'] == 0:
        data.update(mcq=get_consumed_qty(sp))

    form = StockForm(request.form, **data)
    form.is_local.choices = [('local', t('.local')),
                             ('oversea', t('.oversea')),
                             ]
    if form.validate_on_submit():
        doc = dict(max_store=form.max_store.data,
                   is_local=form.is_local.data == 'local',
                   lead_time=form.lead_time.data,
                   mcq=form.mcq.data,
                   min_store=form.min_store.data,
                   )
        min_store = doc['min_store']
        weeks = 1 if doc['is_local'] else 2
        mcq = doc['mcq']  # month consumed qty
        lead_time = doc['lead_time']

        if min_store == 0:
            min_store = int(ceil(mcq * weeks / 4.0))

        # consumed qty during purchase
        cqdp = int(ceil(mcq * lead_time / 4.0))
        if lead_time < 4:
            npq = cqdp - sp.store_good + min_store + mcq
        else:
            npq = cqdp - sp.store_good + min_store + cqdp

        if npq < 0:
            npq = 0

        doc.update(npq=npq, cqdp=cqdp)
        if doc['min_store'] > 0:
            doc.update(min_alert=sp.store_good - doc['min_store'])

        if doc['max_store'] > 0:
            doc.update(max_alert=doc['max_store'] - sp.store_good)

        sp.save(doc=doc, skip=True, update_ts=False)
        if sp.is_valid:
            flash(t('.set_stock_successfully'), 'success')
            return redirect(get_referrer())

        fill_form_error(form, sp)

    return render_template('spareparts/stock.html',
                           form=form,
                           sp=sp,
                           )


@mod.route('/export', methods=('GET', 'POST'))
def export():
    spec = session.get('spspec')
    form = ExportForm()
    if request.method == 'POST':
        dbkeys = request.values.getlist('dbkey')
        session['spchecked'] = dbkeys
        if not dbkeys:
            flash(t('no_field_was_selected'), 'error')
            return render_template('spareparts/export.html',
                                   fields=get_fields(),
                                   form=form,
                                   checked=session['spchecked'] or [None],
                                   )

        wb = Workbook()
        ws = wb.add_sheet('Part List')
        fill_header(ws, dbkeys)
        objs = Sparepart.find(spec=spec, sort='department, project, code')
        row = 1
        for sp in objs:
            for i, k in enumerate(dbkeys):
                if k == 'total_price':
                    ws.write(row, i, sp.unit_price * sp.store_good)
                elif k == 'is_local':
                    if sp.is_local:
                        txt = t('spareparts.local')
                    else:
                        txt = t('spareparts.oversea')

                    ws.write(row, i, txt)
                else:
                    ws.write(row, i, getattr(sp, k))

            row += 1

        file_name = 'Part List {}.xls'.format(str(g.user.id))
        file_dir = tempfile.gettempdir()
        file_path = os.path.join(file_dir, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

        session.pop('spspec', None)
        wb.save(file_path)
        return send_from_directory(file_dir,
                                   file_name,
                                   as_attachment=True,
                                   attachment_filename=file_name,
                                   )

    return render_template('spareparts/export.html',
                           fields=get_fields(),
                           form=form,
                           checked=session.get('spchecked', []),
                           )


@mod.route('/select-import')
@login_required
def select_import():
    return render_template('spareparts/select_import.html')


# asset leader can update qty
# store user can import new spare part with qty
# but can not update qty if exists
# other fields can be updated
@mod.route('/import/<int:kind>', methods=('GET', 'POST'))
@login_required
def import_spareparts(kind=1):
    form = ImportForm()
    if kind == 0:
        template = 'update_sparepart_qty.xls'
        image = 'update_sparepart_qty.png'
        checked = None
        legend = '.update_sparepart_qty'
        submit = '.start_update'
    elif kind == 1:
        template = 'sparepart.xls'
        image = 'sparepart.png'
        checked = False
        legend = '.import_spareparts'
        submit = 'start_import'
    else:
        template = 'update_sparepart_price.xls'
        image = 'update_sparepart_price.png'
        checked = None
        legend = '.update_sparepart_price'
        submit = '.start_update'

    if request.method == 'POST':
        if request.form.get('if-update'):
            checked = True

        excel = request.files.get('attachment')
        if not excel:
            flash(t('please_select_a_file'), 'error')
        elif os.path.splitext(excel.filename)[-1].lower() != '.xls':
            flash(t('only_excel_is_allowed'), 'error')
        else:
            fn = '{}_{}_{}'.format(strftime('%Y%m%d%H%M%S'),
                                   g.user.id,
                                   secure_filename(excel.filename),
                                   )
            file_path = os.path.join(tempfile.gettempdir(), fn)
            excel.save(file_path)

            return do_import(file_path, update=checked, kind=kind)

    return render_template('spareparts/import.html',
                           checked=checked,
                           form=form,
                           template=template,
                           image=image,
                           legend=legend,
                           submit=submit,
                           )


def get_consumed_qty(sp):
    in_qty = out_qty = 0
    if sp.mcq == 0:
        today = datetime.now()
        end_date = '{}-{}-01'.format(today.year, today.month)
        if today.month < 4:
            year = today.year - 1
            month = 12 + today.month - 3
        else:
            year = today.year
            month = today.month - 3

        begin_date = '{}-{}-01'.format(year, month)
        spec = dict(kind='1',
                    date={'$gte': begin_date, '$lte': end_date},
                    )
        spec.update(is_out=False)
        in_qty = sum(int(io.good_qty) for io in Iorecord.find(spec=spec))

        spec.update(is_out=True)
        out_qty = sum(int(io.good_qty) for io in Iorecord.find(spec=spec))

    qty = out_qty - in_qty
    return 0 if qty < 0 else qty


def update_part(sp, form, can_edit_qty=True):
    sp.update(name=form.name.data.strip(),
              code=form.code.data.strip().upper(),
              department=form.department.data,
              project=form.project.data,
              location=form.location.data.strip(),
              model=form.model.data.strip().upper(),
              prod_model=form.prod_model.data.strip().upper(),
              pn=form.pn.data.strip().upper(),
              unit_price=form.unit_price.data,
              vendor=form.vendor.data,
              desc=form.desc.data,
              remark=form.remark.data,
              )
    if can_edit_qty:
        sp.update(store_good=form.store_good.data,
                  store_bad=form.store_bad.data,
                  out_good=form.out_good.data,
                  out_bad=form.out_bad.data,
                  )

    # update the min_alert and max_alert
    sp.pre_store_alert()


def fill_header(ws, headers):
    tmaps = dict((k, v) for v, k in get_fields())
    [ws.write(0, i, t(tmaps[k])) for i, k in enumerate(headers)]


def get_fields():
    return (('department', 'department'),
            ('project', 'project'),
            ('name', 'name'),
            ('.code', 'code'),
            ('model', 'model'),
            ('.prod_model', 'prod_model'),
            ('location', 'location'),
            ('pn', 'pn'),
            ('.low_limit', 'min_store'),
            ('.high_limit', 'max_store'),
            ('.store_good', 'store_good'),
            ('.store_bad', 'store_bad'),
            ('.out_good', 'out_good'),
            ('.out_bad', 'out_bad'),
            ('.buy_good', 'buy_good'),
            ('.buy_bad', 'buy_bad'),
            ('.lead_time', 'lead_time'),
            ('.vendor', 'vendor'),
            ('.vendor_type', 'is_local'),
            ('.month_consumed_qty', 'mcq'),
            ('.consumed_qty_during_purchase', 'cqdp'),
            ('description', 'desc'),
            ('remark', 'remark'),
            ('.unit_price', 'unit_price'),
            ('.total_price', 'total_price'),
            )


def get_keyword_spec(keyword):
    keyword = re.escape(keyword)
    return [dict(code=re.compile(keyword.upper())),
            dict(name=re.compile(keyword, re.I)),
            dict(model=re.compile(keyword.upper())),
            dict(prod_model=re.compile(keyword.upper())),
            ]
