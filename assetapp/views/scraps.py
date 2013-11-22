#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import re
from flask import (Blueprint, g, request, redirect, url_for, flash,
                   render_template, jsonify,
                   )
from ..models.user import User
from ..models.scrap import Scrap
from ..models.equipment import Equipment
from ..forms.scrap import ScrapForm
from ..utils.auth import login_required, role_required
from ..utils.general import fill_form_error, get_referrer, set_referrer
from ..utils.sendmail import send_mail
from assetapp import t

mod = Blueprint('scraps', __name__)


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
                       {'asset.name': re.compile(re.escape(keyword), re.I)},
                       ]
        search = True

    scraps = Scrap.find(spec=spec,
                        paginate=True,
                        search=search,
                        sort='created_at desc',
                        total='docs',
                        )

    return render_template('scraps/index.html',
                           scraps=scraps,
                           keyword=keyword,
                           )


@mod.route('/new', methods=('GET', 'POST'))
# @role_required(['asset_user', 'asset_leader'])
@login_required
def new():
    set_referrer()
    form = ScrapForm()
    if form.validate_on_submit():
        flex_id = form.flex_id.data.strip().upper()
        e = Equipment.find_one(spec=dict(flex_id=flex_id))
        if not e:
            form.flex_id.errors = ['not_found']
        elif e.get_status == 'scrap':
            form.flex_id.errors = ['.already_scraped']
        elif not g.user.can_scrap_equipment(e):
            form.flex_id.errors = ['permission_denied']
        else:
            scrap = Scrap(login=g.user.nick_name,
                          login_id=g.user.badge_id,
                          user=form.user.data,
                          date=form.date.data,
                          remark=form.remark.data,
                          asset=dict(department=e.department,
                                     project=e.project,
                                     flex_id=flex_id,
                                     sn=e.sn,
                                     fixed_id=e.fixed_id,
                                     tn=e.tn,
                                     cn=e.cn,
                                     prod_date=e.prod_date,
                                     model=e.model,
                                     name=e.name,
                                     desc=e.desc,
                                     )
                          )
            scrap.save()
            if scrap.is_valid:
                doc = dict(status=e.status + ['scrap'], is_live=False)
                e.save(doc=doc, skip=True)
                flash(t('.scraped_successfully'), 'success')
                dp = e.department
                pj = e.project
                project_leaders = User.get_emails('project_leader', dp, pj,
                                                  kind='scrap',
                                                  )
                store_users = User.get_emails('store_user', dp, pj, 'scrap')
                asset_users = User.get_emails('asset_user', dp, pj, 'scrap')
                asset_leaders = User.get_emails('asset_leader', dp, pj,
                                                kind='scrap',
                                                )
                send_mail(subject=t('notifications.equipment_was_scraped'),
                          to=project_leaders,
                          cc=store_users + asset_users + asset_leaders,
                          template='scrap.html',
                          values=dict(scrap=scrap, asset=e),
                          )
                return redirect(get_referrer())

            fill_form_error(form, scrap)

    flex_id = (form.flex_id.data or '').strip().upper()
    spec = dict(flex_id=flex_id)
    return render_template('scraps/new.html',
                           form=form,
                           ep=Equipment.find_one(spec=spec) or dict(),
                           )


@mod.route('/show-equipment')
def show_equipment():
    flex_id = request.args.get('flex_id', '').strip().upper()
    if len(flex_id) > 11:
        e = Equipment.find_one(spec=dict(flex_id=flex_id))
        if e:
            data = e.dict
            data.update(is_good=t('good') if e.is_good else t('bad'),
                        is_instore=t('yes') if e.is_instore else t('no'),
                        status=t(e.get_status),
                        )

            data.pop('updated_at', None)
            data.pop('_id', None)
            return jsonify(found=True, **data)

    return jsonify(found=False, **dict((k, '') for k in Equipment._db_fields))
