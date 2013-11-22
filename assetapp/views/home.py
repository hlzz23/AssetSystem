#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from datetime import datetime
from flask import (Blueprint, g, request, session, url_for, redirect,
                   flash, render_template, jsonify,
                   )

from ..models.user import User
from ..models.project import Project
from ..models.equipment import Equipment
from ..models.upload import Upload
from ..models.sparepart import Sparepart
from ..forms.user import LoginForm, SignupForm
from ..utils.auth import login_required
from assetapp import t

mod = Blueprint('home', __name__)


@mod.route('/')
@login_required
def index():
    return render_template('home/index.html',
                           esum=Equipment.total_count(),
                           spsum=Sparepart.total_count(),
                           psum=Project.total_count(),
                           )


@mod.route('/about')
@login_required
def about():
    return render_template('home/about.html')


@mod.route('/change-lang')
def change_lang():
    lang = request.args.get('lang', '').lower()
    if lang and lang in ('en', 'zh'):
        session['lang'] = lang
        # return redirect(url_for('.index'))

    return render_template('home/change_lang.html',
                           lang=session.get('lang', ''),
                           )


@mod.route('/signup', methods=('GET', 'POST'))
def signup():
    form = SignupForm()
    fill_form_choices(form)
    if form.validate_on_submit():
        user = User(login=form.login.data.strip().lower(),
                    password=form.password.data,
                    nick_name=form.nick_name.data.strip(),
                    badge_id=str(form.badge_id.data),
                    email=form.email.data.strip(),
                    phone=form.phone.data.strip(),
                    gsm=form.gsm.data.strip(),
                    short_no=form.short_no.data.strip(),
                    lang=form.lang.data,
                    )
        can_send = []
        for k in ('buy', 'io', 'tf', 'idle', 'scrap', 'alarm', 'notify'):
            if getattr(form, 'send_{}'.format(k)).data == 'yes':
                can_send.append(k)

        user.can_send = can_send
        user.save()
        if user.is_valid:
            flash(t('signup_successfully', 'success'))
            return redirect(url_for('.login'))

        # show the error message
        for k, v in user._errors.items():
            flash('{}: {}'.format(k, t(v)), 'error')

    return render_template('home/signup.html', form=form)


@mod.route('/login', methods=('GET', 'POST'))
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.authenticate(form.login.data.lower().strip(),
                                 form.password.data,
                                 )
        if user is None:
            form.login.errors = [t('.invalid_name_or_password')]
        elif not user.is_active:
            form.login.errors = [t('.not_activated')]
        else:
            session['user_id'] = user.id
            session['lang'] = user.lang
            url = session.pop('next_url', None)
            if not url:
                if user.is_root:
                    url = url_for('users.index')
                elif user.is_store_user:
                    url = url_for('iohistory.index')
                elif user.is_project_leader:
                    url = url_for('spareparts.index')
                elif user.is_asset_user:
                    url = url_for('equipment.index')
                elif user.is_asset_leader:
                    url = url_for('users.index')
                else:
                    url = url_for('.index')

            return redirect(url)

    return render_template('home/login.html', form=form)


@mod.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('.login'))


@mod.route('/checkdate')
def js_check_date():
    d = request.args.get('date', '')
    spec = request.args.get('spec', 'today')
    if spec == 'today':
        spec = datetime.today().strftime('%Y-%m-%d')

    if d and d > spec:
        return jsonify(error=t('invalid_date'))

    return jsonify(error='')


@mod.route('/js-delete-file')
def js_delete_file():
    id = request.args.get('id')
    if id:
        upload = Upload.find_one(id)
        if upload:
            upload.destroy()
            return jsonify(ok=True)

    return jsonify(ok=True)


def fill_form_choices(form):
    radio_choice = [('yes', t('yes')), ('no', t('no'))]
    form.send_buy.choices = radio_choice
    form.send_io.choices = radio_choice
    form.send_tf.choices = radio_choice
    form.send_idle.choices = radio_choice
    form.send_scrap.choices = radio_choice
    form.send_alarm.choices = radio_choice
    form.send_notify.choices = radio_choice
