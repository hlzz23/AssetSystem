#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import os
import os.path
import re
import tempfile
from datetime import datetime
from pyExcelerator import Workbook

from flask import (Blueprint, g, request, redirect, render_template, url_for,
                   flash, jsonify, session, send_from_directory,
                   )
from ..models.user import User
from ..models.iorecord import Iorecord
from ..models.equipment import Equipment
from ..models.sparepart import Sparepart
from ..forms.iorecord import (BackEquipmentForm, BackSparepartForm,
                              OutEquipmentForm, OutSparepartForm,
                              ExportForm, QueryForm, OutSNForm,
                              )
from ..utils.auth import login_required, role_required
from ..utils.general import fill_form_error, get_sp_desc, get_referrer
from ..utils.sendmail import send_mail
from ..utils.select import (department_choices, project_choices,
                            code_choices, limited_department_choices,
                            )
from assetapp import t

mod = Blueprint('iohistory', __name__)
two_format = '{{"label": "{} -> {}", "value": "{}"}},'
three_format = '{{"label": "{} -> {} -> {}", "value": "{}"}},'


@mod.route('/')
@login_required
def index():
    get_referrer()
    spec = {}
    search = False
    kind = request.args.get('kind', '').lower()
    if kind == 'in':
        spec.update(is_out=False)
    elif kind == 'out':
        spec.update(is_out=True)

    keyword = request.args.get('keyword', '').strip()
    if keyword:
        spec['$or'] = get_keyword_spec(keyword)
        search = True

    # for query form
    dept = request.args.get('department', '')
    project = request.args.get('project', '')
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    word = request.args.get('word', '').strip()
    form = QueryForm(request.form,
                     department=dept,
                     project=project,
                     start_date=start_date,
                     end_date=end_date,
                     word=word,
                     )
    form.department.choices = department_choices()
    form.project.choices = project_choices(with_all=True)
    if dept:
        spec.update(department=dept)
        search = True

    if project:
        spec.update(project=project)
        search = True

    if start_date:
        spec.update(date={'$gte': start_date})
        search = True

    if end_date:
        spec.update(date={'$lte': end_date})
        search = True

    if start_date and end_date:
        spec.update(date={'$gte': start_date, '$lte': end_date})

    if word:
        spec['$or'] = get_keyword_spec(word)
        search = True

    session['iospec'] = spec
    ios = Iorecord.find(spec=spec,
                        search=search,
                        sort='created_at desc',
                        paginate=True,
                        total='docs',
                        )
    return render_template('iorecords/index.html',
                           ios=ios,
                           kind=kind,
                           keyword=keyword,
                           word=word,
                           form=form,
                           )


@mod.route('/show/<id>')
@login_required
def show(id):
    io = Iorecord.find_one(id)
    kind = request.args.get('kind')
    if not io:
        flash(t('record_not_found'), 'error')
        return redirect(url_for('.index', kind=kind))

    return render_template('iorecords/show.html',
                           io=io,
                           kind=kind,
                           )


@mod.route('/<kind>-in', methods=('GET', 'POST'))
@role_required('store_user')
def instore(kind):
    if kind == 'equipment':
        return equipment_in()
    elif kind == 'sparepart':
        return sparepart_in()
    else:
        return goldenboard_in()


@mod.route('/<kind>-out', methods=('GET', 'POST'))
@role_required('store_user')
def outstore(kind):
    if kind == 'equipment':
        return equipment_out()
    elif kind == 'sparepart':
        return sparepart_out_sn()
    else:
        return goldenboard_out()


def equipment_in():
    form = BackEquipmentForm()
    form.is_good.choices = [('good', t('good')), ('bad', t('bad'))]
    e = None
    if form.validate_on_submit():
        flex_id = form.flex_id.data.strip().upper()
        spec = dict(flex_id=flex_id)
        e = Equipment.find_one(spec=spec)
        if e is None:
            form.flex_id.errors = ['not_found']
        elif e.is_instore:
            form.flex_id.errors = ['.already_in_store']
        elif not g.user.can_io_asset(e):
            form.flex_id.errors = ['permission_denied']
        else:
            io = create_io(form)
            io.update(is_out=False,
                      kind='0',
                      department=e.department,
                      project=e.project,
                      name=e.name,
                      asset=dict(back_to=form.location.data,
                                 iogood=form.is_good.data == 'good',
                                 flex_id=flex_id,
                                 sn=e.sn,
                                 fixed_id=e.fixed_id,
                                 model=e.model,
                                 ),
                      )
            io.save()
            if io.is_valid:
                doc = dict(is_instore=True,
                           location=form.location.data,
                           line='',
                           )
                e.save(doc=doc, skip=True, update_ts=False)
                flash(t('.equipment_in_successfully'), 'success')
                dp = e.department
                pj = e.project
                send_mail(subject=t('notifications.equipment_was_in'),
                          to=User.get_emails('project_leader', dp, pj, 'io'),
                          cc=User.get_emails('store_user', dp, pj, 'io'),
                          template='asset_in.html',
                          values=dict(asset=e, io=io),
                          )
                return redirect(url_for('.index', kind='in'))

            fill_form_error(form, io)

    return render_template('iorecords/equipment_in.html',
                           form=form,
                           equipment=e,
                           )


def sparepart_in():
    form = BackSparepartForm()
    fill_sp_choices(form, 'in')
    if form.validate_on_submit():
        code = form.code_text.data.strip().upper() or form.code.data
        sp = Sparepart.find_one(spec=dict(code=code))
        if not sp:
            form.code_text.errors = ['not_found']
        else:
            good_qty = form.good.data
            bad_qty = form.bad.data
            io = create_io(form)
            io.update(kind='1',
                      is_out=False,
                      department=sp.department,
                      project=sp.project,
                      name=sp.name,
                      asset=dict(code=code,
                                 pn=sp.pn,
                                 iogood=good_qty,
                                 iobad=bad_qty,
                                 ),
                      )
            io.save()
            if io.is_valid:
                good_out = sp.out_good - good_qty
                bad_out = sp.out_bad - bad_qty
                if good_out < 0:
                    good_out = 0

                if bad_out < 0:
                    bad_out = 0

                doc = dict(store_good=sp.store_good + good_qty,
                           store_bad=sp.store_bad + bad_qty,
                           out_good=good_out,
                           out_bad=bad_out,
                           )
                sp.save(doc=doc, skip=True, update_ts=False)
                flash(t('.sparepart_in_successfully'), 'success')
                dp = sp.department
                pj = sp.project
                send_mail(subject=t('notifications.sparepart_was_in'),
                          to=User.get_emails('project_leader', dp, pj, 'io'),
                          cc=User.get_emails('store_user', dp, pj, 'io'),
                          template='asset_in.html',
                          values=dict(asset=sp, io=io),
                          )
                return redirect(url_for('.index', kind='in'))

            fill_form_error(form, io)

    return render_template('iorecords/sparepart_in.html',
                           form=form,
                           code_desc=get_sp_desc(form.code.data),
                           )


def equipment_out():
    form = OutEquipmentForm()
    form.to_project.choices = project_choices(True)
    e = None
    if form.validate_on_submit():
        flex_id = form.flex_id.data.strip().upper()
        spec = dict(flex_id=flex_id, is_live=True)
        e = Equipment.find_one(spec=spec)
        if not e:
            form.flex_id.errors = ['not_found']
        elif not e.is_instore:
            form.flex_id.errors = ['.not_in_store']
        elif not g.user.can_io_asset(e):
            form.flex_id.errors = ['permission_denied']
        else:
            io = create_io(form)
            io.update(kind='0',
                      is_out=True,
                      department=e.department,
                      project=e.project,
                      name=e.name,
                      asset=dict(flex_id=flex_id,
                                 sn=e.sn,
                                 fixed_id=e.fixed_id,
                                 model=e.model,
                                 to_project=form.to_project.data,
                                 to_where=form.to_where.data,
                                 to_line=form.line.data,
                                 iogood=e.is_good,
                                 ),
                      )
            io.save()
            if io.is_valid:
                doc = dict(location=form.to_where.data,
                           line=form.line.data,
                           is_instore=False,
                           )
                e.save(doc=doc, skip=True, update_ts=False)
                flash(t('.equipment_out_successfully'), 'success')
                dp = e.department
                pj = e.project
                send_mail(subject=t('notifications.equipment_was_out'),
                          to=User.get_emails('project_leader', dp, pj, 'io'),
                          cc=User.get_emails('store_user', dp, pj, 'io'),
                          template='asset_out.html',
                          values=dict(asset=e, io=io),
                          )
                return redirect(url_for('.index', kind='out'))

            fill_form_error(form, io)

    return render_template('iorecords/equipment_out.html',
                           form=form,
                           equipment=e,
                           )


def sparepart_out_sn():
  form = OutSNForm()
  if form.validate_on_submit():
    code = form.code_text.data.strip().upper()
    sp = Sparepart.find_one(spec=dict(code=code))
    if sp is None:
      form.code_text.errors = ['not_found']
    else:
      return redirect(url_for('.sparepart_out', kind='sparepart', code=code,))
  return render_template('iorecords/sn_out.html',
                 form=form,
                 code_desc=get_sp_desc(form.code_text.data),
                 )

# @mod.route('/<kind>-out/<code>/', methods=('GET', 'POST'))
@mod.route('/<kind>-out/', methods=('GET', 'POST'))
@role_required('store_user')
def sparepart_out(kind,):
    if(not request.args.has_key('code')):
        return redirect(url_for('.outstore', kind='sparepart'))
    code = request.args.get('code').strip().upper()
    form = OutSparepartForm()
    sp = Sparepart.find_one(spec=dict(code=code))
    form.department.data = sp.department
    form.project.data = sp.project
    form.date.data = datetime.now().strftime('%Y-%m-%d')
    form.time.data = datetime.now().strftime('%H:%M')
    form.code_text.data = code
    fill_sp_choices(form, 'out')
    if form.validate_on_submit():
        
       

        code = form.code_text.data.strip().upper() or form.code.data
        good_qty = form.good.data
        bad_qty = form.bad.data
        sp = Sparepart.find_one(spec=dict(code=code))
        if sp is None:
            form.code_text.errors = ['not_found']
        elif sp.store_good < good_qty:
            form.good.errors = ['.not_enough']
        elif sp.store_bad < bad_qty:
            form.bad.errors = ['.not_enough']
        else:
            io = create_io(form)
            io.update(kind='1',
                      is_out=True,
                      department=sp.department,
                      project=sp.project,
                      name=sp.name,
                      asset=dict(code=code,
                                 pn=sp.pn,
                                 iogood=good_qty,
                                 iobad=bad_qty,
                                 to_project=form.to_project.data,
                                 to_where=form.to_where.data,
                                 to_line=form.line.data,
                                 ),
                      )
            io.save()
            if io.is_valid:
                doc = dict(store_good=sp.store_good - good_qty,
                           store_bad=sp.store_bad - bad_qty,
                           out_good=sp.out_good + good_qty,
                           out_bad=sp.out_bad + bad_qty,
                           )
                sp.save(doc=doc, skip=True, update_ts=False)
                flash(t('.sparepart_out_successfully'), 'success')
                dp = sp.department
                pj = sp.project
                send_mail(subject=t('notifications.sparepart_was_out'),
                          to=User.get_emails('project_leader', dp, pj, 'io'),
                          cc=User.get_emails('store_user', dp, pj, 'io'),
                          template='asset_out.html',
                          values=dict(asset=sp, io=io),
                          )
                return redirect(url_for('.index', kind='out'))

            fill_form_error(form, io)
    
    return render_template('iorecords/sparepart_out.html',
                           form=form,
                           code_desc=get_sp_desc(form.code.data),
                           )


@mod.route('/export', methods=('GET', 'POST'))
@login_required
def export():
    spec = session.get('iospec')
    form = ExportForm()
    if request.method == 'POST':
        dbkeys = request.values.getlist('dbkey')
        session['iochecked'] = dbkeys
        if not dbkeys:
            flash(t('no_field_was_selected'), 'error')
            return render_template('iorecords/export.html',
                                   fields=get_fields(),
                                   form=form,
                                   checked=session['iochecked'] or [None],
                                   )

        wb = Workbook()
        ws = wb.add_sheet('IOHistory List')
        fill_header(ws, dbkeys)
        objs = Iorecord.find(spec=spec, sort='created_at')
        row = 1
        for o in objs:
            for i, k in enumerate(dbkeys):
                if k == 'direction':
                    ws.write(row, i, t(o.is_out and 'out_store' or 'in_store'))
                elif k == 'kind_name':
                    ws.write(row, i, t(o.kind_name))
                else:
                    ws.write(row, i, getattr(o, k))

            row += 1

        file_name = 'IOHistory List {}.xls'.format(str(g.user.id))
        file_dir = tempfile.gettempdir()
        file_path = os.path.join(file_dir, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

        session.pop('iospec', None)
        wb.save(file_path)
        return send_from_directory(file_dir,
                                   file_name,
                                   as_attachment=True,
                                   attachment_filename=file_name,
                                   )

    return render_template('iorecords/export.html',
                           fields=get_fields(),
                           form=form,
                           checked=session.get('iochecked', []),
                           )


def fill_header(ws, headers):
    tmaps = dict((k, v) for v, k in get_fields())
    [ws.write(0, i, t(tmaps[k])) for i, k in enumerate(headers)]


@mod.route('/show-equip-desc')
def js_equip_desc():
    text = request.args.get('text', '').strip().upper()
    kind = request.args.get('kind', '')
    if text:
        e = Equipment.find_one(spec=dict(flex_id=text))
        error = False
        if e:
            s = [e.name]
            if kind == 'in' and e.is_instore:
                s.append(t('.already_in_store'))
                error = True
            elif kind == 'out' and not e.is_instore:
                s.append(t('.not_in_store'))
                error = True
        else:
            s = [t('not_found')]
            error = True

        return jsonify(desc=', '.join(s), error=error)

    return jsonify(desc='', error=False)


@mod.route('/show-sparepart-desc')
def js_sp_desc():
    text = request.args.get('text', '').strip().upper()
    kind = request.args.get('kind', '')
    if text:
        sp = Sparepart.find_one(spec=dict(code=text))
        if sp:
            return jsonify(desc=sp.desc, error=False)
        else:
            return jsonify(desc=t('not_found'), error=True)

    return jsonify(desc='', error=False)


@mod.route('/js-auto')
def js_autocomplete():
    text = request.args.get('term', '').strip()
    kind = request.args.get('kind', '').strip().lower()
    s = []
    if text:
        error = False
        if kind.startswith('s'):  # spare part
            spec = {'$or': [dict(code=re.compile(re.escape(text.upper()))),
                            dict(pn=re.compile(re.escape(text.upper()), re.I)),
                            ]
                    }
            fields = ['code', 'pn', 'name']
            for sp in Sparepart.find(spec=spec, limit=15, fields=fields):
                s.append(auto_label(sp))

        # equipment
        else:
            key_re = re.compile(re.escape(text.upper()))
            spec = {'$or': [dict(flex_id=key_re),
                            dict(sn=key_re),
                            dict(fixed_id=key_re),
                            ],
                    }
            if kind == 'ein':
                spec.update(is_instore=False)
            elif kind == 'eout':
                spec.update(is_instore=True)

            fields = ['flex_id', 'name']
            for ep in Equipment.find(spec=spec, limit=15, fields=fields):
                s.append(two_format.format(ep.flex_id, ep.name, ep.flex_id))

    return '[{}]'.format(''.join(s)[:-1])


def auto_label(sp):
    if sp.pn:
        return three_format.format(sp.code, sp.pn, sp.name, sp.code)

    return two_format.format(sp.code, sp.name, sp.code)


def fill_sp_choices(form, kind='in'):
    form.department.choices = limited_department_choices(g.user)
    dept = form.department.data
    project = form.project.data
    form.code.choices = code_choices(dept, project)
    form.project.choices = project_choices()
    if kind == 'out':
        form.to_project.choices = project_choices(with_all=True)


def create_io(form):
    return Iorecord(login=g.user.nick_name,
                    login_id=g.user.badge_id,
                    user=form.user.data.strip(),
                    uid=str(form.uid.data),
                    date=form.date.data,
                    time=form.time.data,
                    hard_copy=form.hard_copy.data,
                    remark=form.remark.data,
                    )


def get_fields():
    return (('department', 'department'),
            ('project', 'project'),
            ('kind', 'kind_name'),
            ('.item_code', 'keyid'),
            ('name', 'name'),
            ('users.store_user', 'login'),
            ('handle_user', 'user'),
            ('.date', 'date'),
            ('.direction', 'direction'),
            ('good_qty', 'good_qty'),
            ('bad_qty', 'bad_qty'),
            ('.to_project', 'to_project'),
            ('.to_where', 'to_where'),
            ('.to_line', 'to_line'),
            )


def get_keyword_spec(keyword):
    ig_key_re = re.compile(re.escape(keyword), re.I)
    key_re = re.compile(re.escape(keyword.upper()))
    return [{'name': ig_key_re},
            {'asset.code': key_re},
            {'asset.flex_id': key_re},
            {'asset.sn': key_re},
            {'asset.fixed_id': key_re},
            {'asset.pn': ig_key_re},  # spare part
            {'asset.model': ig_key_re},  # equipment
            ]
