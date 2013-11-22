#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import os
import os.path
import re
import tempfile
from pyExcelerator import Workbook
from flask import (Blueprint, g, request, session, redirect, url_for,
                   render_template, flash, jsonify, send_from_directory,
                   )
from ..models.user import User
from ..models.transfer import Transfer
from ..models.sparepart import Sparepart
from ..models.equipment import Equipment
from ..forms.transfer import (EquipmentInForm, EquipmentOutForm,
                              SparepartInForm, SparepartOutForm,
                              QueryForm, ExportForm,
                              )
from ..forms.equipment import EquipmentForm
from ..utils.auth import login_required, role_required
from ..utils.general import (fill_form_error, get_sp_desc, set_referrer,
                             get_referrer, get_sp_name,
                             )
from ..utils.sendmail import send_mail
from ..utils.select import (department_choices, project_choices, code_choices,
                            source_choices, limited_department_choices,
                            )
from assetapp import t

mod = Blueprint('transfers', __name__)


@mod.route('/')
@login_required
def index():
    get_referrer()
    kind = request.args.get('kind', '')
    search = False
    spec = dict()
    if kind == 'frozen':
        spec.update(is_in=True, kind='0')
        spec['asset.done'] = False

    keyword = request.args.get('keyword', '')
    if keyword:
        spec['$or'] = get_keyword_spec(keyword)
        search = True

    department = request.args.get('department', '')
    project = request.args.get('project', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    word = request.args.get('word', '')
    form = QueryForm(request.form,
                     department=department,
                     project=project,
                     start_date=start_date,
                     end_date=end_date,
                     word=word,
                     )
    form.department.choices = department_choices()
    form.project.choices = project_choices(with_all=True)
    for k, v in (('department', department),
                 ('project', project),
                 ):
        if v:
            spec[k] = v
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

    session['tfspec'] = spec
    transfers = Transfer.find(spec=spec,
                              search=search,
                              paginate=True,
                              sort='created_at desc',
                              total='docs',
                              )
    return render_template('transfers/index.html',
                           transfers=transfers,
                           kind=kind,
                           form=form,
                           keyword=keyword,
                           )


@mod.route('/show/<id>')
@login_required
def show(id):
    set_referrer()
    tf = Transfer.find_one(id)
    if tf is None:
        flash(t('record_not_found'), 'error')
        return redirect(get_referrer())

    return render_template('transfers/show.html',
                           tf=tf,
                           )


@mod.route('/load/<id>', methods=('GET', 'POST'))
@role_required(['asset_user'])
def load(id):
    set_referrer()
    tf = Transfer.find_one(id)
    if not tf:
        flash(t('record_not_found'), 'error')
        return redirect(get_referrer())

    data = tf.dict
    data.update(tf.asset)
    data.update(is_good='good' if data['is_good'] else 'bad',
                source_text='Transfer From Other',
                )
    form = EquipmentForm(request.form, **data)
    form.department.choices = department_choices()
    form.project.choices = project_choices()
    form.source.choices = source_choices()
    form.is_good.choices = [('good', t('good')), ('bad', t('bad'))]
    form.is_instore.choices = [('in', t('equipment.instore')),
                               ('out', t('equipment.outstore'))
                               ]

    if form.validate_on_submit():
        e = Equipment(department=form.department.data,
                      project=form.project.data,
                      source=form.source_text.data.strip().title(),
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
        e.save()
        if e.is_valid:
            tf.update(model=form.model.data,
                      name=form.name.data,
                      )
            tf.asset.update(done=True,
                            flex_id=form.flex_id.data.strip().upper(),
                            sn=form.sn.data.strip().upper(),
                            fixed_id=form.fixed_id.data.strip().upper(),
                            is_good=form.is_good.data == 'good',
                            )
            tf.save(skip=True)
            flash(t('.activate_successfully'), 'success')
            return redirect(get_referrer())

        fill_form_error(form, e)

    return render_template('transfers/load.html',
                           form=form,
                           )


@mod.route('/equipment-in', methods=('GET', 'POST'))
@login_required
def equipment_in():
    form = EquipmentInForm()
    fill_equip_choices(form)
    if form.validate_on_submit():
        flex_id = form.flex_id.data.strip().upper()
        sn = form.sn.data.strip().upper()
        fixed_id = form.fixed_id.data.strip().upper()
        spec = dict()
        spec_list = []
        if flex_id:
            spec_list.append(dict(flex_id=flex_id))

        if sn:
            spec_list.append(dict(sn=sn))

        if fixed_id:
            spec_list.append(dict(fixed_id=fixed_id))

        if spec_list:
            spec['$or'] = spec_list

        error = False
        if spec:
            e = Equipment.find_one(spec=spec)
            if e:
                if e.flex_id == flex_id:
                    form.flex_id.errors = ['already_exists']
                    error = True

                if e.sn == sn:
                    form.sn.errors = ['already_exists']
                    error = True

                if fixed_id and e.fixed_id == fixed_id:
                    form.fixed_id.errors = ['already_exists']
                    error = True

        if error is False:
            tf = create_tf(form)
            tf.update(name=form.name.data,
                      model=form.model.data,
                      )
            tf.update(kind='0',
                      is_in=True,
                      asset=dict(flex_id=form.flex_id.data.strip().upper(),
                                 sn=form.sn.data.strip().upper(),
                                 prod_date=form.prod_date.data,
                                 fixed_id=form.fixed_id.data.strip().upper(),
                                 department=form.department.data,
                                 project=form.project.data,
                                 cn=form.cn.data.strip().upper(),
                                 tn=form.tn.data.strip().upper(),
                                 is_good=form.is_good.data == 'good',
                                 from_where=form.where.data,
                                 to_where=form.to_where.data,
                                 done=False,
                                 ),
                      )
            tf.save()
            if tf.is_valid:
                flash(t('.equipment_transfer_in_successfully'))
                dp = form.department.data
                pj = form.project.data
                asset_users = User.get_emails('asset_user', dp, pj, 'tf')
                store_users = User.get_emails('store_user', dp, pj, 'tf')
                asset_leaders = User.get_emails('asset_leader', dp, pj, 'tf')
                send_mail(subject=t('notifications.equipment_transfer_in'),
                          to=User.get_emails('project_leader', dp, pj, 'tf'),
                          cc=asset_users + store_users + asset_leaders,
                          template='transfer_in.html',
                          values=dict(tf=tf),
                          )
                return redirect(url_for('.index'))

            fill_form_error(form, tf)

    return render_template('transfers/equipment_in.html',
                           form=form,
                           )


@mod.route('/equipment-out', methods=('GET', 'POST'))
@login_required
def equipment_out():
    form = EquipmentOutForm()
    if form.validate_on_submit():
        flex_id = form.flex_id.data.strip().upper()
        spec = dict(flex_id=flex_id,
                    is_live=True,
                    )
        e = Equipment.find_one(spec=spec)
        if not e:
            form.flex_id.errors = ['not_found']
        elif not e.is_instore:
            form.flex_id.errors = ['iohistory.not_in_store']
        elif not g.user.can_transfer_equipment(e):
            form.flex_id.errors = ['permission_denied']
        else:
            tf = create_tf(form)
            tf.name = e.name
            tf.model = e.model
            tf.update(is_in=False,
                      kind='0',
                      asset=dict(flex_id=flex_id,
                                 sn=e.sn,
                                 fixed_id=e.fixed_id,
                                 prod_date=e.prod_date,
                                 cn=e.cn,
                                 tn=e.tn,
                                 department=e.department,
                                 project=e.project,
                                 is_good=e.is_good,
                                 from_where=e.location,
                                 to_where=form.where.data,
                                 done=True,
                                 ),
                      )
            tf.save()
            if tf.is_valid:
                doc = dict(status=e.status + ['transfer'],
                           is_live=False,
                           is_instore=False,
                           )
                e.save(doc=doc, update_ts=False, skip=True)
                flash(t('.equipment_transfer_out_successfully'))
                dp = form.department.data
                pj = form.project.data
                asset_users = User.get_emails('asset_user', dp, pj, 'tf')
                store_users = User.get_emails('store_user', dp, pj, 'tf')
                asset_leaders = User.get_emails('asset_leader', dp, pj, 'tf')
                send_mail(subject=t('notifications.equipment_transfer_out'),
                          to=User.get_emails('project_leader', dp, pj, 'tf'),
                          cc=asset_users + store_users + asset_leaders,
                          template='transfer_out.html',
                          values=dict(tf=tf, asset=e),
                          )
                return redirect(url_for('.index'))

            fill_form_error(form, tf)

    return render_template('transfers/equipment_out.html',
                           form=form,
                           )


@mod.route('/sparepart-<kind>', methods=('GET', 'POST'))
@role_required(['asset_user'])
def transfer_sparepart(kind='in'):
    if kind.strip().lower() == 'in':
        form = SparepartInForm()
        msg = '.sparepart_transfer_in_successfully'
        tp = 'transfers/sparepart_in.html'
    else:
        form = SparepartOutForm()
        msg = '.sparepart_transfer_out_successfully'
        tp = 'transfers/sparepart_out.html'

    fill_sp_choices(form)
    if form.validate_on_submit():
        code = form.code_text.data.strip().upper() or form.code.data
        sp = Sparepart.find_one(spec=dict(code=code))
        if sp is None:
            form.code_text.errors = ['not_found']
        else:
            good_qty = form.good.data
            bad_qty = form.bad.data
            error = False
            if kind == 'in':
                from_where = form.where.data
                to_where = sp.location
            else:
                from_where = sp.location
                to_where = form.where.data
                if sp.store_good < good_qty:
                    form.good.errors = ['iohistory.not_enough']
                    error = True

                if sp.store_bad < bad_qty:
                    form.bad.errors = ['iohistory.not_enough']
                    error = True

            if error is False:
                tf = create_tf(form)
                tf.name = sp.name
                tf.model = sp.model
                tf.update(kind='1',
                          is_in=kind == 'in',
                          asset=dict(code=code,
                                     good=good_qty,
                                     bad=bad_qty,
                                     department=form.department.data,
                                     project=form.project.data,
                                     from_where=from_where,
                                     to_where=to_where,
                                     ),
                          )
                tf.save()
                if tf.is_valid:
                    if kind == 'in':
                        store_good = sp.store_good + good_qty
                        store_bad = sp.store_bad + bad_qty
                    else:
                        store_good = sp.store_good - good_qty
                        store_bad = sp.store_bad - bad_qty

                    doc = dict(store_good=store_good, store_bad=store_bad)
                    sp.save(doc=doc, skip=True, update_ts=False)
                    flash(t(msg), 'success')
                    dp = form.department.data
                    pj = form.project.data
                    asset_users = User.get_emails('asset_user', dp, pj, 'tf')
                    store_users = User.get_emails('store_user', dp, pj, 'tf')
                    asset_leaders = User.get_emails('asset_leader', dp, pj,
                                                    kind='tf',
                                                    )
                    send_mail(subject=t('notifications.sparepart_transfer_in'),
                              to=User.get_emails('project_leader', dp, pj,
                                                 kind='tf',
                                                 ),
                              cc=asset_users + store_users + asset_leaders,
                              template='transfer_{}.html'.format(kind),
                              values=dict(tf=tf, asset=sp),
                              )
                    return redirect(url_for('.index'))

                fill_form_error(form, tf)

    return render_template(tp,
                           form=form,
                           kind=kind,
                           code_desc=get_sp_desc(form.code.data),
                           code_name=get_sp_name(form.code.data),
                           )


@mod.route('/export', methods=('GET', 'POST'))
@login_required
def export():
    spec = session.get('tfspec')
    form = ExportForm()
    if request.method == 'POST':
        dbkeys = request.values.getlist('dbkey')
        session['tfchecked'] = dbkeys
        if not dbkeys:
            flash(t('no_field_was_selected'), 'error')
            return render_template('transfers/export.html',
                                   fields=get_fields(),
                                   form=form,
                                   checked=session['tfchecked'] or [None],
                                   )

        wb = Workbook()
        ws = wb.add_sheet('Transfers List')
        fill_header(ws, dbkeys)
        objs = Transfer.find(spec=spec, sort='created_at')
        row = 1
        for o in objs:
            for i, k in enumerate(dbkeys):
                if k in ('code', 'sn', 'flex_id', 'fixed_id'):
                    ws.write(row, i, o.asset.get(k, ''))
                else:
                    ws.write(row, i, getattr(o, k))

            row += 1

        file_name = 'Transfers List {}.xls'.format(str(g.user.id))
        file_dir = tempfile.gettempdir()
        file_path = os.path.join(file_dir, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

        session.pop('tfspec', None)
        wb.save(file_path)
        return send_from_directory(file_dir,
                                   file_name,
                                   as_attachment=True,
                                   attachment_filename=file_name,
                                   )

    return render_template('transfers/export.html',
                           fields=get_fields(),
                           form=form,
                           checked=session.get('tfchecked', []),
                           )


def fill_header(ws, headers):
    tmaps = dict((k, v) for v, k in get_fields())
    [ws.write(0, i, t(tmaps[k])) for i, k in enumerate(headers)]


@mod.route('/js-show-model')
def show_model():
    flex_id = request.args.get('flex_id', '').strip().upper()
    if flex_id:
        e = Equipment.find_one(spec=dict(flex_id=flex_id))
        return jsonify(model=e.model if e else '',
                       name=e.name if e else '',
                       )

    return jsonify(model='', name='')


def fill_equip_choices(form):
    form.department.choices = limited_department_choices(g.user)
    form.project.choices = project_choices()
    form.is_good.choices = [('good', t('good')), ('bad', t('bad'))]


def fill_sp_choices(form):
    dept = form.department.data
    project = form.project.data
    form.department.choices = limited_department_choices(g.user)
    form.project.choices = project_choices()
    form.code.choices = code_choices(dept, project)


def create_tf(form):
    return Transfer(login=g.user.nick_name,
                    login_id=g.user.badge_id,
                    user=form.user.data,
                    date=form.date.data,
                    remark=form.remark.data,
                    )


def get_fields():
    return (('department', 'department'),
            ('project', 'project'),
            ('kind', 'kind_name'),
            ('users.store_user', 'login'),
            ('handle_user', 'user'),
            ('.transfer_date', 'date'),
            ('name', 'name'),
            ('model', 'model'),
            ('good_qty', 'good_qty'),
            ('bad_qty', 'bad_qty'),
            ('.from_where', 'from_where'),
            ('.to_where', 'to_where'),
            ('spareparts.code', 'code'),
            ('sn', 'sn'),
            ('equipment.flex_id', 'flex_id'),
            ('equipment.fixed_id', 'fixed_id'),
            )


def get_keyword_spec(keyword):
    key_re = re.compile(re.escape(keyword.upper()))
    return [{'asset.code': key_re},
            {'asset.sn': key_re},
            {'asset.flex_id': key_re},
            {'asset.fixed_id': key_re},
            {'name': re.compile(re.escape(keyword), re.I)}
            ]
