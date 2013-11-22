#!/usr/bin/env python
#-*- coding: utf-8 -*-

from flask.ext.wtf import Form, TextField, TextAreaField, required


class ProjectForm(Form):
    name = TextField('name', [required()])
    remark = TextAreaField('remark')
