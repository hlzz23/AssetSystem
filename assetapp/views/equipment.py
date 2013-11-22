#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import re
import os
import os.path
from time import strftime
import tempfile

from pyExcelerator import Workbook
from werkzeug import secure_filename
from flask import (Blueprint, request, session, redirect, url_for, g,
                   render_template, flash, send_from_directory,
                   )

from ..forms.equipment import (EquipmentForm, ExportForm, QueryForm,
                               LocationForm, ImportForm,
                               )
from ..models.equipment import Equipment
from ..models.buy import Buy
from ..models.iorecord import Iorecord

from ..utils.auth import login_required, role_required
from ..utils.general import (set_referrer, get_referrer, fill_form_error,
                             handle_uploads,
                             )
from ..utils.select import department_choices, project_choices, source_choices
from ..utils.import_equipment import do_import
from assetapp import t

mod = Blueprint('equipment', __name__)


@mod.route('/')
@login_required
def index():
    get_referrer()
    keyword = request.args.get('keyword', '').strip()
    spec = dict()
    search = False
    if keyword:
        spec['$or'] = get_keyword_spec(keyword)
        search = True

    status = request.args.get('status', '').lower()
    if status:
        if status == 'fa':
            spec.update(fixed_id={'$ne': ''})
        else:
            spec.update(status=status.lower())

    dp = request.args.get('department', '')
    pj = request.args.get('project', '')
    model = request.args.get('model', '').strip()
    line = request.args.get('line', '').strip()
    word = request.args.get('word', '').strip()
    form = QueryForm(request.form,
                     department=dp,
                     project=pj,
                     model=model,
                     line=line,
                     word=word,
                     )
    form.department.choices = department_choices()
    form.project.choices = project_choices(with_all=True)
    for v, k in ((dp, 'department'),
                 (pj, 'project'),
                 (model, 'model'),
                 (line, 'line'),
                 ):
        if v:
            spec[k] = v
            search = True

    if word:
        spec['$or'] = get_keyword_spec(word)
        search = True

    session['espec'] = spec
    equipment = Equipment.find(spec=spec,
                               sort='project, flex_id',
                               search=search,
                               paginate=True,
                               total='docs',
                               )
    return render_template('equipment/index.html',
                           equipment=equipment,
                           keyword=keyword,
                           status=status,
                           form=form,
                           word=word,
                           )


@mod.route('/show/<id>')
@login_required
def show(id):
    set_referrer()
    ep = Equipment.find_one(id)
    if ep is None:
        flash(t('record_not_found'), 'error')
        return redirect(get_referrer())

    return render_template('equipment/show.html', ep=ep)


@mod.route('/new', methods=('GET', 'POST'))
@role_required('asset_user')
def new():
    set_referrer()
    form = EquipmentForm()
    fill_choices(form)
    if form.validate_on_submit():
        e = Equipment()
        update_equipment(e, form)
        if not e.source:
            form.source.errors = ['This field is required.']
        else:
            e.save()
            if e.is_valid:
                handle_uploads(str(e.id))
                flash(t('created_successfully'), 'success')
                return redirect(get_referrer())

        fill_form_error(form, e)

    return render_template('equipment/new.html',
                           form=form,
                           )


@mod.route('/edit/<id>', methods=('GET', 'POST'))
@login_required
def edit(id):
    set_referrer()
    e = Equipment.find_one(id)
    if e is None:
        flash(t('record_not_found'), 'error')
        return redirect(get_referrer())

    if not g.user.can_edit_equipment(e):
        flash(t('permission_denied'), 'error')
        return redirect(get_referrer())

    data = e.dict
    data.update(is_good='good' if data['is_good'] else 'bad',
                is_instore='in' if data['is_instore'] else 'out',
                )
    form = EquipmentForm(request.form, **data)
    fill_choices(form)
    if form.validate_on_submit():
        update_equipment(e, form)
        if not e.source:
            form.source.errors = ['This field is required.']
        else:
            e.save()
            if e.is_valid:
                handle_uploads(str(e.id))
                flash(t('updated_successfully'), 'success')
                return redirect(get_referrer())

        fill_form_error(form, e)

    return render_template('equipment/edit.html',
                           form=form,
                           equipment=e,
                           )


# for store user to update location
@mod.route('/edit2/<id>', methods=('GET', 'POST'))
@login_required
def edit2(id):
    set_referrer()
    e = Equipment.find_one(id)
    if e is None:
        flash(t('record_not_found'), 'error')
        return redirect(get_referrer())

    if not g.user.can_update_location(e):
        flash(t('permission_denied'), 'error')
        return redirect(get_referrer())

    form = LocationForm(request.form,
                        location=e.location,
                        is_good='good' if e.is_good else 'bad'
                        )
    form.is_good.choices = [('good', t('good')), ('bad', t('bad'))]
    if form.validate_on_submit():
        e.location = form.location.data
        if not e.is_good:
            e.is_good = form.is_good.data == 'good'

        e.save(skip=True)
        if e.is_valid:
            flash(t('updated_successfully'), 'success')
            return redirect(get_referrer())

    return render_template('equipment/edit2.html',
                           form=form,
                           equipment=e,
                           )


@mod.route('/destroy/<id>')
@login_required
def destroy(id):
    set_referrer()
    e = Equipment.find_one(id)
    if e is None:
        flash(t('record_not_found'), 'error')
    elif g.user.can_remove_equipment(e):
        if e.canbe_removed:
            e.destroy()
            [up.destroy() for up in e.uploads]

            flash(t('destroyed_successfully'), 'success')
        else:
            flash(t('cannot_be_removed'), 'error')
    else:
        flash(t('permission_denied'), 'error')

    return redirect(get_referrer())


@mod.route('/export', methods=('GET', 'POST'))
@login_required
def export():
    spec = session.get('espec')
    form = ExportForm()
    if request.method == 'POST':
        dbkeys = request.values.getlist('dbkey')
        session['echecked'] = dbkeys
        if not dbkeys:
            flash(t('no_field_was_selected'), 'error')
            return render_template('equipment/export.html',
                                   fields=get_fields(),
                                   form=form,
                                   checked=session['echecked'] or [None],
                                   )

        wb = Workbook()
        ws = wb.add_sheet('Equipment List')
        fill_header(ws, dbkeys)
        objs = Equipment.find(spec=spec, sort='department, project, flex_id')
        row = 1
        for e in objs:
            for i, k in enumerate(dbkeys):
                if k == 'is_good':
                    ws.write(row, i, t('good' if e.is_good else 'bad'))
                elif k == 'is_instore':
                    ws.write(row, i, t('yes' if e.is_instore else 'no'))
                else:
                    ws.write(row, i, getattr(e, k))

            row += 1

        file_name = 'Equipment List {}.xls'.format(str(g.user.id))
        file_dir = tempfile.gettempdir()
        file_path = os.path.join(file_dir, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

        session.pop('espec', None)
        wb.save(file_path)
        return send_from_directory(file_dir,
                                   file_name,
                                   as_attachment=True,
                                   attachment_filename=file_name,
                                   )

    return render_template('equipment/export.html',
                           fields=get_fields(),
                           form=form,
                           checked=session.get('echecked', []),
                           )


@mod.route('/import', methods=('GET', 'POST'))
@role_required('asset_user')
def import_equipment():
    checked = False
    form = ImportForm()
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

            return do_import(file_path, update=checked)

    return render_template('equipment/import.html',
                           checked=checked,
                           form=form,
                           )


def fill_header(ws, headers):
    tmaps = dict((k, v) for v, k in get_fields())
    [ws.write(0, i, t(tmaps[k])) for i, k in enumerate(headers)]


def fill_choices(form):
    form.department.choices = department_choices()
    form.project.choices = project_choices()
    form.source.choices = source_choices()
    form.is_good.choices = [('good', t('good')), ('bad', t('bad'))]
    form.is_instore.choices = [('in', t('.instore')),
                               ('out', t('.outstore'))
                               ]


def update_equipment(e, form):
    e.update(department=form.department.data,
             project=form.project.data,
             source=form.source_text.data.strip().upper() or form.source.data,
             sr=form.sr.data,
             supplier=form.supplier.data,
             mf=form.mf.data,
             name=form.name.data,
             desc=form.desc.data,
             flex_id=form.flex_id.data.strip().upper(),
             sn=form.sn.data.strip().upper(),
             fixed_id=form.fixed_id.data.strip().upper(),
             prod_date=form.prod_date.data,
             tn=form.tn.data.strip().upper(),
             cn=form.cn.data.strip().upper(),
             owner=form.owner.data,
             model=form.model.data.strip().upper(),
             price=form.price.data,
             line=form.line.data,
             location=form.location.data,
             ws=form.ws.data,
             we=form.we.data,
             is_good=form.is_good.data == 'good',
             is_instore=form.is_instore.data == 'in',
             req_user=form.req_user.data.strip(),
             req_date=form.req_date.data,
             req_remark=form.req_remark.data,
             )


def get_fields():
    return (('department', 'department'),
            ('project', 'project'),
            ('source', 'source'),
            ('source_remark', 'sr'),
            ('supplier', 'supplier'),
            ('manufacturer', 'mf'),
            ('name', 'name'),
            ('equipment.prod_date', 'prod_date'),
            ('equipment.flex_id', 'flex_id'),
            ('sn', 'sn'),
            ('equipment.fixed_id', 'fixed_id'),
            ('buys.track_no', 'tn'),
            ('buys.custom_no', 'cn'),
            ('owner', 'owner'),
            ('model', 'model'),
            ('price', 'price'),
            ('line', 'line'),
            ('location', 'location'),
            ('equipment.warranty_start', 'ws'),
            ('equipment.warranty_end', 'we'),
            ('equipment.is_good', 'is_good'),
            ('equipment.is_instore', 'is_instore'),
            ('equipment.req_user', 'req_user'),
            ('equipment.req_date', 'req_date'),
            ('equipment.req_remark', 'req_remark'),
            ('description', 'desc'),
            )


def get_keyword_spec(keyword):
    key_re = re.compile(re.escape(keyword).upper())
    return [dict(flex_id=key_re),
            dict(sn=key_re),
            dict(fixed_id=key_re)
            ]
