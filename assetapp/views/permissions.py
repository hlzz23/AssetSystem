#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import re
from flask import (Blueprint, g, session, request, redirect, url_for,
                   render_template, flash, jsonify,
                   )

from ..models.user import User
from ..models.permission import Permission
from ..models.equipment import Equipment
from ..models.sparepart import Sparepart
from ..forms.permission import PermissionForm, AddUserForm
from ..utils.auth import login_required, role_required
from ..utils.select import (department_choices, project_choices, role_choices,
                            bool_choices, all_choices,
                            get_users_for_permission,
                            blank_choices,
                            )
from ..utils.general import fill_form_error, set_referrer, get_referrer
from assetapp import t

mod = Blueprint('permissions', __name__)


@mod.route('/')
@login_required
def index():
    search = False
    spec = {}
    keyword = request.args.get('keyword', '').strip()
    if keyword:
        spec.update(group=re.compile(keyword, re.I))
        search = True

    if g.user.is_root:
        role = 'asset_leader'
    elif g.user.is_store_user:
        role = 'store_user'
    elif g.user.is_asset_user:
        role = 'asset_user'
    elif g.user.is_project_leader:
        role = 'project_leader'
    else:
        role = 'store_user'

    role = request.args.get('role', role).strip().lower()
    spec.update(role=role)

    permissions = Permission.find(spec=spec,
                                  sort='group',
                                  search=search,
                                  paginate=True,
                                  total='docs',
                                  )
    urls = []
    urls.append(('asset_leader', get_role_count('asset_leader')))
    urls.append(('asset_user', get_role_count('asset_user')))
    urls.append(('store_user', get_role_count('store_user')))
    urls.append(('project_leader', get_role_count('project_leader')))
    return render_template('permissions/index.html',
                           permissions=permissions,
                           keyword=keyword,
                           urls=urls,
                           role=role,
                           )


@mod.route('/show/<id>')
@login_required
def show(id):
    set_referrer()
    p = Permission.find_one(id)
    if p is None:
        flash(t('record_not_found'), 'error')
        return redirect(get_referrer())

    return render_template('permissions/show.html',
                           permission=p,
                           )


@mod.route('/new', methods=('GET', 'POST'))
@role_required('asset_leader')
def new():
    form = PermissionForm()
    role = form.role.data
    if role not in ('None', ''):
        dc = department_choices(with_all=(role != 'project_leader'))
    else:
        dc = blank_choices()

    form.department.choices = dc
    form.projects.choices = project_choices(with_all=g.user.is_root)
    form.role.choices = role_choices(asset_leader=g.user.is_root)
    form.is_active.choices = bool_choices('.active', '.disabled')
    if form.validate_on_submit():
        dp = form.department_text.data.strip().upper() or form.department.data
        p = Permission(group=form.group.data.strip().upper(),
                       role=form.role.data,
                       department=dp,
                       projects=request.form.getlist('projects'),
                       is_active=bool(form.is_active.data),
                       remark=form.remark.data,
                       )
        p.save()
        if p.is_valid:
            flash(t('created_successfully'), 'success')
            return redirect(url_for('.index', role=p.role))

        fill_form_error(form, p)

    return render_template('permissions/new.html',
                           form=form,
                           )


@mod.route('/edit/<id>', methods=('GET', 'POST'))
@login_required
def edit(id):
    p = Permission.find_one(id)
    if p is None:
        flash(t('record_not_found'), 'error')
        return redirect(url_for('.index'))

    if not g.user.can_edit_permission(p):
        flash(t('permission_denied'), 'error')
        return redirect(url_for('.index'))

    form = PermissionForm(request.form, **p.dict)
    role = form.role.data
    if role not in ('None', ''):
        dc = department_choices(with_all=(role != 'project_leader'))
    else:
        dc = blank_choices()

    form.department.choices = dc
    form.projects.choices = project_choices(with_all=g.user.is_root)
    form.role.choices = role_choices(asset_leader=g.user.is_root)
    form.is_active.choices = bool_choices('.active', '.disabled')
    if form.validate_on_submit():
        dp = form.department_text.data.strip().upper() or form.department.data
        old_group = p.group
        old_department = p.department
        p.update(group=form.group.data.strip().upper(),
                 role=form.role.data,
                 department=dp,
                 projects=request.form.getlist('projects'),
                 is_active=bool(form.is_active.data),
                 remark=form.remark.data,
                 )
        p.save()
        if p.is_valid:
            if old_group != p.group:
                for user in User.find(spec=dict(groups=old_group)):
                    user.groups.remove(old_group)
                    user.groups.append(p.group)
                    user.save(doc=dict(groups=user.groups),
                              skip=True,
                              update_ts=False,
                              )

            if old_department != dp:
                spec = dict(department=old_department)
                kwargs = dict(doc=dict(department=dp),
                              skip=True,
                              update_ts=False,
                              )
                [s.save(**kwargs) for s in Sparepart.find(spec=spec)]
                spec.update(is_live=True)
                [e.save(**kwargs) for e in Equipment.find(spec=spec)]

            flash(t('updated_successfully'), 'success')
            return redirect(url_for('.index', role=p.role))

        fill_form_error(form, p)

    return render_template('permissions/edit.html',
                           form=form,
                           )


@mod.route('/destroy/<id>')
@login_required
def destroy(id):
    p = Permission.find_one(id)
    if p is None:
        flash(t('record_not_found'), 'error')
    elif g.user.can_remove_permission(p):
        p.destroy()
        group = p.group
        kwargs = dict(skip=True, update_ts=False)
        for user in User.find(spec=dict(groups=group)):
            user.groups.remove(group)
            user.save(doc=dict(groups=user.groups), **kwargs)

        flash(t('destroyed_successfully'), 'success')
    else:
        flash(t('permission_denied'), 'error')

    return redirect(url_for('.index', role=p.role if p else ''))


@mod.route('/authorize/<id>', methods=('GET', 'POST'))
@login_required
def authorize(id):
    p = Permission.find_one(id)
    if p is None:
        flash(t('record_not_found'), 'error')
        return redirect(url_for('.index'))

    if not g.user.can_edit_permission(p):
        flash(t('permission_denied'), 'error')
        return redirect(url_for('.index'))

    users = [user.login for user in p.users]
    form = AddUserForm(request.form, users=users)
    spec = dict(login={'$ne': 'root'}, is_active=True)
    uc = ((u.login, u.nick_name) for u in User.find(spec=spec))
    form.users.choices = sorted(uc, key=lambda s: s[1].lower())
    if form.validate_on_submit():
        kwargs = dict(skip=True, update_ts=False)
        form_users = request.form.getlist('users')
        # add the new added permissions
        for login in set(form_users) - set(users):
            user = User.find_one(spec=dict(login=login))
            if p.group not in user.groups:
                user.groups.append(p.group)
                user.save(doc=dict(groups=sorted(user.groups)), **kwargs)

        # remove the deleted permissions
        for login in set(users) - set(form_users):
            user = User.find_one(spec=dict(login=login))
            if p.group in user.groups:
                user.groups.remove(p.group)
                user.save(doc=dict(groups=sorted(user.groups)), **kwargs)

        flash(t('updated_successfully'), 'success')
        return redirect(url_for('.index', role=p.role))

    return render_template('permissions/authorize.html',
                           form=form,
                           permission=p,
                           )


@mod.route('/change-role')
def change_role():
    role = request.args.get('role', '')
    if role:
        with_all = (role != 'project_leader')
        return jsonify(choices=department_choices(with_all=with_all))

    return jsonify(choices=blank_choices())


def get_role_count(role='asset_leader'):
    return Permission.find(spec=dict(role=role)).count
