#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import re
from flask import (Blueprint, g, request, redirect, url_for, flash,
                   render_template, jsonify,
                   )
from ..models.user import User
from ..models.idle import Idle
from ..models.equipment import Equipment
from ..forms.idle import IdleForm, RecallForm
from ..utils.auth import login_required, role_required
from ..utils.general import (fill_form_error, get_referrer, set_referrer,
                             )
from ..utils.sendmail import send_mail
from assetapp import t

mod = Blueprint('idles', __name__)


@mod.route('/')
@login_required
def index():
    get_referrer()
    search = False
    spec = dict()
    keyword = request.args.get('keyword', '').strip()
    if keyword:
        kw_re = re.compile(re.escape(keyword).upper())
        spec['$or'] = [{'asset.flex_id': kw_re},
                       {'asset.sn': kw_re},
                       {'asset.fixed_id': kw_re},
                       ]
        search = True

    idles = Idle.find(spec=spec,
                      paginate=True,
                      search=search,
                      sort='created_at desc',
                      total='docs',
                      )

    return render_template('idles/index.html',
                           idles=idles,
                           keyword=keyword,
                           )


@mod.route('/new', methods=('GET', 'POST'))
@role_required(['asset_user'])
def new():
    set_referrer()
    form = IdleForm()
    if form.validate_on_submit():
        flex_id = form.flex_id.data.strip().upper()
        e = Equipment.find_one(spec=dict(flex_id=flex_id))
        if not e:
            form.flex_id.errors = ['not_found']
        elif e.get_status == 'idle':
            form.flex_id.errors = ['.already_idleed']
        elif not g.user.can_idle_equipment(e):
            form.flex_id.errors = ['permission_denied']
        else:
            idle = create_idle(form, e)
            idle.status.append('idle')
            idle.save()
            if idle.is_valid:
                doc = dict(status=e.status + ['idle'], is_live=False)
                e.save(doc=doc, skip=True)
                flash(t('.idleed_successfully'), 'success')
                dp = e.department
                pj = e.project
                project_leaders = User.get_emails('project_leader', dp, pj,
                                                  kind='idle',
                                                  )
                store_users = User.get_emails('store_user', dp, pj, 'idle')
                asset_users = User.get_emails('asset_user', dp, pj, 'idle')
                asset_leaders = User.get_emails('asset_leader', dp, pj, 'idle')
                send_mail(subject=t('notifications.asset_was_idled'),
                          to=project_leaders,
                          cc=store_users + asset_users + asset_leaders,
                          template='idle.html',
                          values=dict(idle=idle, asset=e),
                          )
                return redirect(get_referrer())

            fill_form_error(form, idle)

    flex_id = (form.flex_id.data or '').strip().upper()
    spec = dict(flex_id=flex_id)
    return render_template('idles/new.html',
                           form=form,
                           ep=Equipment.find_one(spec=spec) or dict(),
                           )


@mod.route('/recall/<id>', methods=('GET', 'POST'))
@login_required
def recall(id):
    set_referrer()
    idle = Idle.find_one(id)
    if not idle:
        flash(t('record_not_found'), 'error')
        return redirect(get_referrer())

    if not g.user.can_recall_idle(idle):
        flash(t('permission_denied'), 'error')
        return redirect(get_referrer())

    flex_id = idle.asset['flex_id']
    e = Equipment.find_one(spec=dict(flex_id=flex_id))

    form = RecallForm(request.form, flex_id=flex_id)
    if form.validate_on_submit():
        if not e:
            form.flex_id.errors = ['not_found']
        elif form.date.data < idle.date:
            form.date.errors = ['invalid_date']
        elif e.get_status != 'idle':
            form.flex_id.errors = ['.not_idled']
        else:
            idle2 = create_idle(form, e)
            idle2.status.append('recall')
            idle2.save()
            if idle2.is_valid:
                # change the record to 'recall' status
                doc = dict(status=idle.status + ['recall'])
                idle.save(doc=doc, skip=True)

                # change equipment status
                doc = dict(status=e.status[:-1])
                if len(e.status) == 1:
                    doc.update(is_live=True)

                e.save(doc=doc, skip=True)
                flash(t('.recalled_successfully'), 'success')
                dp = e.department
                pj = e.project
                project_leaders = User.get_emails('project_leader', dp, pj,
                                                  kind='idle',
                                                  )
                store_users = User.get_emails('store_user', dp, pj, 'idle')
                asset_users = User.get_emails('asset_user', dp, pj, 'idle')
                asset_leaders = User.get_emails('asset_leader', dp, pj, 'idle')
                send_mail(subject=t('notifications.asset_was_recalled'),
                          to=project_leaders,
                          cc=store_users + asset_users + asset_leaders,
                          template='recall.html',
                          values=dict(idle=idle, asset=e),
                          )
                return redirect(get_referrer())

            fill_form_error(form, idle2)

    form.flex_id.data = flex_id
    return render_template('idles/recall.html',
                           form=form,
                           ep=e,
                           idle=idle,
                           )


def create_idle(form, ep):
    return Idle(login=g.user.nick_name,
                login_id=g.user.badge_id,
                user=form.user.data,
                date=form.date.data,
                remark=form.remark.data,
                asset=dict(department=ep.department,
                           project=ep.project,
                           flex_id=ep.flex_id,
                           sn=ep.sn,
                           fixed_id=ep.fixed_id,
                           tn=ep.tn,
                           cn=ep.cn,
                           prod_date=ep.prod_date,
                           model=ep.model,
                           name=ep.name,
                           desc=ep.desc,
                           is_good=ep.is_good,
                           )
                )
