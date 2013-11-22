#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from functools import wraps
from flask import g, session, flash, request, url_for, redirect
from assetapp import t


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user:
            flash(t('please_login'), 'error')
            if 'next_url' not in session:
                session['next_url'] = request.path

            return redirect(url_for('home.login', next=request.path))

        return f(*args, **kwargs)

    return decorated_function


def role_required(role, endpoint='.index', msg='permission_denied'):
    vars = locals()

    def _role_required(f):
        @login_required
        @wraps(f)
        def decorated_function(*args, **kwargs):
            role = vars['role']
            if isinstance(role, basestring):
                role = [role]

            for role_ in role:
                if getattr(g.user, 'is_{}'.format(role_)):
                    return f(*args, **kwargs)

            flash(t(msg), 'error')
            return redirect(url_for(endpoint))

        return decorated_function

    return _role_required
