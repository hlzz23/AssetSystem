#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import re
from flask import (Blueprint, g, session, redirect, url_for,
                   request, flash, render_template,
                   )

from ..models.user import User
from ..models.buy import Buy
from ..models.iorecord import Iorecord
from ..models.permission import Permission

from ..forms.user import NewUserForm, EditUserForm, AuthorizeForm
from ..utils.auth import login_required, role_required
from ..utils.select import bool_choices
from ..utils.general import (get_page, get_per_page, fill_form_error,
                             not_cache_header,
                             )
from assetapp import t

mod = Blueprint('users', __name__)


@mod.route('/')
@login_required
def index():
    spec = dict()
    search = False
    keyword = request.args.get('keyword', '').strip()
    if keyword:
        search = True
        spec['$or'] = get_keyword_spec(keyword)

    role = request.args.get('role', '').strip().lower()
    if role:
        pspec = dict(role=role)
        spec.update(groups={'$in':
                    [p.group for p in Permission.find(spec=pspec)]}
                    )

    users = User.find(spec=spec,
                      sort='login',
                      search=search,
                      paginate=True,
                      total='docs',
                      )
    urls = []
    urls.append(('asset_leader', get_users_count('asset_leader')))
    urls.append(('asset_user', get_users_count('asset_user')))
    urls.append(('store_user', get_users_count('store_user')))
    urls.append(('project_leader', get_users_count('project_leader')))
    # urls.append(('cal_user', get_users_count('cal_user')))
    return render_template('users/index.html',
                           users=users,
                           keyword=keyword,
                           urls=urls,
                           role=role,
                           )


@mod.route('/new', methods=('GET', 'POST'))
@role_required('asset_leader')
def new():
    if not g.user.can_create_user:
        flash(t('permission_denied'), 'error')
        return redirect(url_for('.index'))

    form = NewUserForm()
    fill_form_choices(form)
    form.is_active.choices = bool_choices('.active', '.disabled')
    if form.validate_on_submit():
        user = User(login=form.login.data.strip().lower(),
                    nick_name=form.nick_name.data.strip(),
                    password=form.password.data,
                    email=form.email.data.strip(),
                    badge_id=str(form.badge_id.data),
                    lang=form.lang.data,
                    is_active=bool(form.is_active.data),
                    gsm=form.gsm.data.strip(),
                    phone=form.phone.data.strip(),
                    short_no=form.short_no.data.strip(),
                    )
        user.can_send = update_send(form)
        user.save()
        if user.is_valid:
            flash(t('created_successfully'), 'success')
            return redirect(url_for('.index'))

        fill_form_error(form, user)

    return render_template('users/new.html',
                           form=form,
                           )


@mod.route('/edit/<id>', methods=('GET', 'POST'))
@login_required
def edit(id):
    user = User.find_one(id)
    if user is None:
        flash(t('record_not_found'), 'error')
        return redirect(url_for('.index'))

    if not g.user.can_edit_user(user):
        flash(t('permission_denied'), 'error')
        return redirect(url_for('.index'))

    data = user.dict
    for k in ('buy', 'io', 'tf', 'idle', 'scrap', 'alarm', 'notify'):
        data['send_{}'.format(k)] = 'yes' if k in data['can_send'] else 'no'

    form = EditUserForm(request.form, **data)
    fill_form_choices(form)
    form.is_active.choices = bool_choices('.active', '.disabled')
    if form.validate_on_submit():
        user.update(nick_name=form.nick_name.data.strip(),
                    email=form.email.data.strip(),
                    badge_id=str(form.badge_id.data),
                    lang=form.lang.data,
                    gsm=form.gsm.data.strip(),
                    phone=form.phone.data.strip(),
                    short_no=form.short_no.data.strip(),
                    )
        user.can_send = update_send(form)
        if not user.is_root:
            user.update(login=form.login.data.strip().lower())

        if g.user.id != user.id:
            user.is_active = bool(form.is_active.data)

        if form.password_again.data:
            user.password = form.password.data

        user.save()
        if user.is_valid:
            session['lang'] = user.lang
            flash(t('updated_successfully'), 'success')
            # password reset?
            if user.email and form.password.data:
                if user.is_active and user.id != g.user.id:
                    send_mail(subject=t('users.your_password_was_reset'),
                              to=[user.email],
                              template='password_reset.html',
                              values=dict(password=form.password.data,
                                          login=user.login,
                                          ),
                              )
            return redirect(url_for('.index'))

        fill_form_error(form, user)

    return render_template('users/edit.html',
                           user=user,
                           form=form,
                           )


@mod.route('/authorize/<id>', methods=('GET', 'POST'))
@role_required('asset_leader')
def authorize(id):
    user = User.find_one(id)
    if user is None:
        flash(t('record_not_found'), 'error')
        return redirect(url_for('.index'))

    # user can not modify his/her own permission
    if g.user.id == user.id:
        flash(t('permission_denied'), 'error')
        return redirect(url_for('.index'))

    groups = [p.group for p in user.permissions]
    form = AuthorizeForm(request.form, groups=groups)
    spec = dict(is_active=True)
    if not g.user.is_root:
        spec.update(role={'$ne': 'asset_leader'})

    form.groups.choices = sorted((p.group, p.group)
                                 for p in Permission.find(spec=spec)
                                 )
    if form.validate_on_submit():
        user.groups = sorted(request.form.getlist('groups'))
        if sorted(groups) != user.groups:
            user.save()

        flash(t('updated_successfully'), 'success')
        return redirect(url_for('.index'))

    return render_template('users/authorize.html',
                           form=form,
                           user=user,
                           )


@mod.route('/destroy/<id>')
@login_required
def destroy(id):
    user = User.find_one(id)
    if user is None:
        flash(t('record_not_found'), 'error')
    elif g.user.can_remove_user(user):
        if user.canbe_removed:
            user.destroy()
            flash(t('destroyed_successfully'), 'success')
        else:
            flash(t('cannot_be_removed'), 'error')
    else:
        flash(t('permission_denied'), 'error')

    return redirect(url_for('.index'))


def get_users_count(role='asset_leader'):
    spec = dict(role=role)
    return User.find(spec=dict(groups={'$in':
                     [p.group for p in Permission.find(spec=spec)]})
                     ).count


def fill_form_choices(form):
    radio_choice = [('yes', t('yes')), ('no', t('no'))]
    form.send_buy.choices = radio_choice
    form.send_io.choices = radio_choice
    form.send_tf.choices = radio_choice
    form.send_idle.choices = radio_choice
    form.send_scrap.choices = radio_choice
    form.send_alarm.choices = radio_choice
    form.send_notify.choices = radio_choice


def update_send(form):
    can_send = []
    for k in ('buy', 'io', 'tf', 'idle', 'scrap', 'alarm', 'notify'):
        if getattr(form, 'send_{}'.format(k)).data == 'yes':
            can_send.append(k)

    return can_send


def get_keyword_spec(keyword):
    keyword = re.escape(keyword)
    return [dict(login=re.compile(keyword.lower())),
            dict(nick_name=re.compile(keyword, re.I)),
            ]
