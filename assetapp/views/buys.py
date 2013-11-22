#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import re
from datetime import datetime
from flask import (Blueprint, g, request, redirect, render_template, flash,
                   url_for, jsonify,
                   )
from ..models.user import User
from ..models.buy import Buy
from ..models.equipment import Equipment
from ..models.sparepart import Sparepart
from ..forms.buy import (BuyEquipmentForm, BuySparepartForm, ConfirmForm,
                         AssignForm, QueryForm,
                         )
from ..utils.auth import login_required, role_required
from ..utils.general import get_page, get_per_page, fill_form_error
from ..utils.sendmail import send_mail
from ..utils.select import (department_choices, project_choices,
                            source_choices, blank_choices, code_choices,
                            limited_department_choices,
                            )
from assetapp import t

mod = Blueprint('buys', __name__)


@mod.route('/')
@login_required
def index():
    spec = dict()
    search = False
    routing = request.args.get('routing', '').strip().lower()
    keyword = request.args.get('keyword', '').strip().upper()
    if keyword:
        search = True
        spec['$or'] = get_keyword_spec(keyword)

    if routing:
        if routing not in ('fresh', 'accept'):
            routing = 'fresh'

        spec.update(workflow=routing)

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

    buys = Buy.find(spec=spec,
                    search=search,
                    sort='updated_at desc',
                    paginate=True,
                    total='docs',
                    )
    return render_template('buys/index.html',
                           buys=buys,
                           keyword=keyword,
                           word=word,
                           routing=routing,
                           form=form,
                           fresh_count=Buy.fresh_count(),
                           assign_count=Buy.assign_count(),
                           )


@mod.route('/show/<id>')
@login_required
def show(id):
    buy = Buy.find_one(id)
    if buy is None:
        flash(t('record_not_found'), 'error')
        return redirect(url_for('.index'))

    return render_template('buys/show.html',
                           buy=buy,
                           )


@mod.route('/<kind>-incoming', methods=('GET', 'POST'))
@role_required('store_user')
def new(kind):
    if kind == 'equipment':
        return receive_equipment()
    elif kind == 'sparepart':
        return receive_sparepart()
    else:
        return receive_goldenboard()


@mod.route('/edit/<id>', methods=('GET', 'POST'))
@login_required
def edit(id):
    error, buy = get_buy(id)
    if error:
        return buy

    if not g.user.can_edit_buy(buy):
        flash(t('permission_denied'), 'error')
        return redirect(url_for('.index'))

    if buy.is_equipment:
        return receive_equipment(buy)
    elif buy.is_sparepart:
        return receive_sparepart(buy)
    else:
        return receive_goldenboard(buy)


@mod.route('/confirm/<id>', methods=('GET', 'POST'))
@login_required
def confirm(id):
    error, buy = get_buy(id)
    if error:
        return buy

    if not g.user.can_confirm(buy):
        flash(t('permission_denied'), 'error')
        return redirect(url_for('.index'))

    form = ConfirmForm()
    form.accept.choices = [('accept', t('.accept')), ('reject', t('.reject'))]
    if form.validate_on_submit():
        accept = form.accept.data
        is_accept = accept == 'accept'
        history = dict(user=g.user.nick_name,
                       time=datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                       accept=is_accept,
                       flow='1',  # 1: confirm
                       remark=form.remark.data,
                       )
        if is_accept:
            if buy.is_sparepart:
                buy.workflow = 'done'
            else:
                buy.workflow = 'accept'
        else:
            # if reject, then back to the beginning
            buy.workflow = 'fresh'

        buy.history.append(history)
        if not buy.is_sparepart and is_accept:
            buy.asset['req_user'] = g.user.nick_name
            buy.asset['req_date'] = datetime.now().strftime('%Y-%m-%d')

        buy.save(skip=True)
        if buy.is_sparepart and is_accept:
            sp = buy.sparepart
            if sp:
                sp.buy_good += buy.asset['good']
                sp.store_good += buy.asset['good']
                sp.buy_bad += buy.asset['bad']
                sp.store_bad += buy.asset['bad']
                kwargs = dict(skip=True, update_ts=False)
                sp.save(**kwargs)

        if is_accept:
            subject = 'notifications.accepted_the_incoming'
            flash(t(subject), 'success')
        else:
            subject = 'notifications.rejected_the_incoming'
            flash(t(subject), 'error')

        dp = buy.department
        pj = buy.project
        send_mail(subject=t(subject),
                  to=User.get_emails('project_leader', dp, pj, kind='buy'),
                  cc=User.get_emails('store_user', dp, pj, kind='buy'),
                  template='confirm_asset.html',
                  values=dict(buy=buy,
                              is_accept=is_accept,
                              user=g.user,
                              ),
                  )
        return redirect(url_for('.index'))

    return render_template('buys/confirm.html',
                           form=form,
                           buy=buy,
                           )


@mod.route('/assign/<id>', methods=('GET', 'POST'))
@login_required
def assign(id):
    error, buy = get_buy(id)
    if error:
        return buy

    if not g.user.can_assign(buy):
        flash(t('permission_denied'), 'error')
        return redirect(url_for('.index'))

    form = AssignForm()
    form.accept.choices = [('accept', t('.accept')), ('reject', t('.reject'))]
    if form.validate_on_submit():
        flex_id = form.flex_id.data.strip().upper()
        fixed_id = form.fixed_id.data.strip().upper()
        accept = form.accept.data
        is_accept = accept == 'accept'
        error = False
        if is_accept:
            spec = dict(flex_id=flex_id)
            if Equipment.find_one(spec=spec, fields=['_id']):
                form.flex_id.errors = ['already_exists']
                error = True
            elif fixed_id:
                spec = dict(fixed_id=fixed_id)
                if Equipment.find_one(spec=spec, fields=['_id']):
                    form.flex_id.errors = ['already_exists']
                    error = True

        if error is False:
            history = dict(user=g.user.nick_name,
                           time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           accept=is_accept,
                           flow='2',  # 2 means assign flex id action
                           remark=form.remark.data,
                           )
            # reset to fresh if rejected
            buy.workflow = 'done' if is_accept else 'fresh'
            buy.history.append(history)
            buy.asset.update(flex_id=flex_id,
                             fixed_id=fixed_id,
                             )

            # TODO create equipment and send mail
            need_send = False
            if is_accept:
                data = buy.dict
                data.update(**data['asset'])
                data.update(sr=data['source_remark'])
                for k in ('_id', 'updated_at', 'history', 'asset'):
                    data.pop(k, None)

                e = Equipment(**data)
                e.save()
                if e.is_valid:
                    buy.save(skip=True)
                    need_send = True
                    subject = 'notifications.assigned_the_equipment'
                    flash(t('assigned_successfully'), 'success')
                else:
                    for k, v in e._errors.items():
                        flash('{}: {}'.format(k, v), 'error')
            else:
                buy.save(skip=True)
                need_send = True
                subject = 'notifications.refused_assign_flex_id'
                flash(t('refused_assign_flex_id'), 'error')

            if need_send:
                dp = buy.department
                pj = buy.project
                project_leaders = User.get_emails('project_leader', dp, pj,
                                                  kind='assign',
                                                  )
                asset_users = User.get_emails('asset_user', dp, pj,
                                              kind='assign',
                                              )
                store_users = User.get_emails('store_user', dp, pj,
                                              kind='assign',
                                              )
                send_mail(subject=t(subject),
                          to=store_users,
                          cc=project_leaders + asset_users,
                          template='assign_asset.html',
                          values=dict(buy=buy, user=g.user),
                          )

            return redirect(url_for('.index'))

    return render_template('buys/assign.html',
                           form=form,
                           buy=buy,
                           )


def receive_equipment(obj=None):
    if obj is None:
        form = BuyEquipmentForm()
    else:
        data = obj.dict
        data.update(data['asset'])
        data.update(is_good='good' if data['is_good'] else 'bad')
        form = BuyEquipmentForm(request.form, **data)

    fill_choices(form)
    if form.validate_on_submit():
        sn = form.sn.data.strip().upper()
        # updated on 2012/09/26
        # sn is always unique
        # spec = dict(sn=sn, is_live=True)
        spec = dict(sn=sn)
        if Equipment.find_one(spec=spec, fields=['_id']):
            form.sn.errors = ['already_exists']
        else:
            spec = {'asset.sn': sn}
            buy = Buy.find_one(spec=spec)
            if obj:
                if buy and buy.id != obj.id:
                    form.sn.errors = ['already_exists']
            elif buy:
                form.sn.errors = ['already_exists']
            else:
                buy = obj if obj else Buy()
                update_equipment(buy=buy, form=form)
                if buy.date > str(datetime.today())[:10]:
                    form.date.errors = ['invalid_date']
                else:
                    buy.save()
                    if buy.is_valid:
                        if obj:
                            s = 'updated_successfully'
                        else:
                            s = 'created_successfully'

                        flash(t(s), 'success')

                        # send mail
                        dp = buy.department
                        pj = buy.project
                        project_leaders = User.get_emails('project_leader',
                                                          dp, pj,
                                                          kind='buy',
                                                          )
                        store_users = User.get_emails('store_user', dp, pj,
                                                      kind='buy',
                                                      )
                        send_mail(subject=t('notifications.incoming_arrived'),
                                  to=project_leaders,
                                  cc=store_users,
                                  template='incoming_arrived.html',
                                  values=dict(buy=buy),
                                  )
                        return redirect(url_for('.index'))

                    fill_form_error(form, buy)

    return render_template('buys/equipment.html',
                           form=form,
                           )


def receive_sparepart(obj=None):
    if obj is None:
        form = BuySparepartForm()
    else:
        data = obj.dict
        data.update(data['asset'])
        data.update(code=data['code'])
        form = BuySparepartForm(request.form, **data)

    fill_choices(form, kind='sparepart')
    if form.validate_on_submit():
        buy = obj if obj else Buy()
        if update_sparepart(buy=buy, form=form) is True:
            if buy.date > str(datetime.today())[:10]:
                form.date.errors = ['invalid_date']
            else:
                buy.save()
                if buy.is_valid:
                    if obj:
                        s = 'updated_successfully'
                    else:
                        s = 'created_successfully'

                    flash(t(s), 'success')
                    # send mail
                    dp = buy.department
                    pj = buy.project
                    send_mail(subject=t('notifications.incoming_arrived'),
                              to=User.get_emails('project_leader',
                                                 dp, pj, 'buy'),
                              cc=User.get_emails('store_user', dp, pj, 'buy'),
                              template='incoming_arrived.html',
                              values=dict(buy=buy),
                              )
                    return redirect(url_for('.index'))

                fill_form_error(form, buy)

    return render_template('buys/sparepart.html',
                           form=form,
                           )


@mod.route('/destroy/<id>')
@login_required
def destroy(id):
    buy = Buy.find_one(id)
    if buy is None:
        flash(t('record_not_found'), 'error')

    if buy.canbe_removed:
        if g.user.can_remove_buy(buy):
            buy.destroy()
            flash(t('destroyed_successfully'), 'success')
        else:
            flash(t('permission_denied'), 'error')
    else:
        flash(t('can_not_be_removed'), 'error')

    return redirect(url_for('.index'))


@mod.route('/js-code')
def js_code():
    department = request.args.get('department', '')
    project = request.args.get('project', '')
    return jsonify(choices=code_choices(department, project))


@mod.route('/js-desc')
def js_code_desc():
    text = request.args.get('text', '')
    if text:
        sp = Sparepart.find_one(spec=dict(code=text))
        return jsonify(desc=sp.name if sp else '', input_value=sp.name)

    return jsonify(desc='', input_value='')


def get_buy(id):
    buy = Buy.find_one(id)
    if buy is None:
        flash(t('record_not_found'), 'error')
        return True, redirect(url_for('.index'))

    return False, buy


def fill_choices(form, kind='equipment'):
    form.department.choices = limited_department_choices(g.user)
    form.project.choices = project_choices()
    form.source.choices = source_choices()
    if kind == 'equipment':
        form.is_good.choices = [('good', t('good')), ('bad', t('bad'))]
    else:
        dept = form.department.data
        project = form.project.data
        form.code.choices = code_choices(dept, project)


def update_buy(buy, form):
    buy.update(department=form.department.data,
               project=form.project.data,
               login_id=g.user.badge_id,
               login=g.user.nick_name,
               source=form.source.data,
               source_remark=form.source_remark.data,
               po=form.po.data.strip().upper(),
               price=form.price.data,
               date=form.date.data,
               tn=form.tn.data.strip().upper(),
               cn=form.cn.data.strip().upper(),
               mf=form.mf.data,
               supplier=form.supplier.data,
               model=form.model.data,
               owner=form.owner.data,
               )


def update_equipment(buy, form):
    asset = dict(sn=form.sn.data.strip().upper(),
                 location=form.location.data,
                 desc=form.desc.data,
                 ws=form.ws.data,
                 we=form.we.data,
                 is_good=form.is_good.data == 'good',
                 )
    update_buy(buy, form)
    buy.update(asset=asset, kind='0', name=form.name.data)


def update_sparepart(buy, form):
    code = form.code_text.data.strip().upper() or form.code.data
    sp = Sparepart.find_one(spec=dict(code=code))
    if sp:
        asset = dict(good=form.good.data,
                     bad=form.bad.data,
                     code=code,
                     desc=sp.desc if sp else '',
                     )
        update_buy(buy, form)
        buy.update(asset=asset, kind='1', name=sp.name if sp else '')
        return True
    else:
        form.code_text.errors = ['not_found']
        return False


def get_keyword_spec(keyword):
    key_re = re.compile(re.escape(keyword))
    return [{'name': re.compile(re.escape(keyword), re.I)},
            {'asset.code': key_re},
            {'asset.sn': key_re},
            {'asset.flex_id': key_re},
            {'asset.fixed_id': key_re},
            ]
