#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask.ext.wtf import (Form, TextField, PasswordField, SelectMultipleField,
                           SelectField, required, optional, RadioField,
                           email, equal_to, IntegerField, number_range,
                           )

lang_choices = [('en', 'English'), ('zh', u'简体中文')]


class LoginForm(Form):
    login = TextField('login_name', [required()])
    password = PasswordField('password', [required()])


class SignupForm(Form):
    login = TextField('login_name', [required()])
    badge_id = IntegerField('badge_id', [required(), number_range(min=10000)])
    nick_name = TextField('nick_name', [required()])
    email = TextField('email', [email(), optional()])
    phone = TextField('phone')
    gsm = TextField('gsm')
    short_no = TextField('short_no')
    password = PasswordField('password', [required()])
    password_again = PasswordField('password_again',
                                   [required(),
                                   equal_to('password',
                                            message='password_not_match',
                                            ),
                                    ]
                                   )
    lang = SelectField('page_lang',
                       [required()],
                       choices=lang_choices,
                       default='zh',
                       )
    send_buy = RadioField('users.buy_mail', default='yes')
    send_io = RadioField('users.io_mail', default='yes')
    send_tf = RadioField('users.tf_mail', default='yes')
    send_idle = RadioField('users.idle_mail', default='yes')
    send_scrap = RadioField('users.scrap_mail', default='yes')
    send_alarm = RadioField('users.alarm_mail', default='yes')
    send_notify = RadioField('users.notify_mail', default='yes')


class NewUserForm(SignupForm):
    is_active = SelectField('.is_active', default=1, coerce=int)


class EditUserForm(NewUserForm):
    password = PasswordField('password', [optional()])
    password_again = PasswordField('password_again',
                                   [optional(),
                                    equal_to('password',
                                             message='password_not_match',
                                             )
                                    ],
                                   )


class AuthorizeForm(Form):
    groups = SelectMultipleField('permissions.permission_group')
