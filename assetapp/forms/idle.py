#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask.ext.wtf import (Form, TextField, TextAreaField, required)
from .general import check_date_format


class IdleForm(Form):
    flex_id = TextField('flex_id', [required()])
    user = TextField('handle_user', [required()])
    date = TextField('.idle_date', [required(), check_date_format])
    remark = TextAreaField('remark')


class RecallForm(IdleForm):
    flex_id = TextField('flex_id')
