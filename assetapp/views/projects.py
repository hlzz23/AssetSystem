#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import re
from flask import (Blueprint, session, request, g, url_for, redirect,
                   render_template, flash,
                   )
from ..models.project import Project
from ..models.equipment import Equipment
from ..models.sparepart import Sparepart
from ..models.iorecord import Iorecord
from ..models.permission import Permission

from ..forms.project import ProjectForm
from ..utils.auth import login_required, role_required
from ..utils.general import fill_form_error
from assetapp import t

mod = Blueprint('projects', __name__)


@mod.route('/')
@login_required
def index():
    keyword = request.args.get('keyword', '').strip()
    spec = {}
    search = False
    if keyword:
        spec.update(name=re.compile(re.escape(keyword), re.I))
        search = True

    projects = Project.find(spec=spec,
                            sort='name',
                            search=search,
                            paginate=True,
                            total='docs',
                            )
    return render_template('projects/index.html',
                           projects=projects,
                           keyword=keyword,
                           )


@mod.route('/new', methods=('GET', 'POST'))
@role_required('asset_leader')
def new():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(name=form.name.data.strip(),
                          remark=form.remark.data,
                          )
        project.save()
        if project.is_valid:
            flash(t('created_successfully'), 'success')
            return redirect(url_for('.index'))

        fill_form_error(form, project)

    return render_template('projects/new.html',
                           form=form,
                           )


@mod.route('/edit/<id>', methods=('GET', 'POST'))
@login_required
def edit(id):
    project = Project.find_one(id)
    if project is None:
        flash(t('record_not_found'), 'error')
        return redirect(url_for('.index'))

    if not g.user.can_edit_project(project):
        flash(t('permission_denied'), 'error')
        return redirect(url_for('.index'))

    form = ProjectForm(request.form, **project.dict)
    if form.validate_on_submit():
        old_project = project.name
        project.update(name=form.name.data.strip(),
                       remark=form.remark.data,
                       )
        project.save()
        if project.is_valid:
            # if project changes its name
            # update the project name for equipment/sparepart/permission
            if old_project != project.name:
                spec = dict(project=old_project)
                kwargs = dict(doc=dict(project=project.name),
                              skip=True,
                              update_ts=False,
                              )
                [e.save(**kwargs) for e in Equipment.find(spec=spec)]
                [s.save(**kwargs) for s in Sparepart.find(spec=spec)]

                kwargs = dict(skip=True, update_ts=False)
                for p in Permission.find(spec=dict(projects=old_project)):
                    p.projects.remove(old_project)
                    p.projects.append(project.name)
                    p.projects.sort()
                    p.save(doc=dict(projects=p.projects), **kwargs)

            flash(t('updated_successfully'), 'success')
            return redirect(url_for('.index'))

        fill_form_error(form, project)

    return render_template('projects/edit.html',
                           form=form,
                           )


@mod.route('/destroy/<id>')
@login_required
def destroy(id):
    project = Project.find_one(id)
    if g.user.can_remove_project(project):
        if project.canbe_removed:
            project.remove()
            kwargs = dict(skip=True, update_ts=False)
            spec = dict(projects=project.name)
            # project deleted, remove it from permission
            for p in Permission.find(spec=spec):
                p.projects.remove(project.name)
                p.projects.sort()
                p.save(doc=dict(projects=p.projects), **kwargs)

            flash(t('destroyed_successfully'), 'success')
        else:
            flash(t('cannot_be_removed'), 'error')
    else:
        flash(t('permission_denied'), 'error')

    return redirect(request.referrer)
