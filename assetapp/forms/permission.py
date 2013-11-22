#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask.ext.wtf import (Form, SelectField, SelectMultipleField, TextField,
                           required, ValidationError,
                           )


class PermissionForm(Form):
    group = TextField('.permission_name', [required()])
    role = SelectField('role', [required()])
    department = SelectField('department')
    department_text = TextField('.or_enter_department_manually')
    projects = SelectMultipleField('projects')
    is_active = SelectField('.is_active', default=1, coerce=int)
    remark = TextField('remark')

    def validate_department(self, field):
        if not (self.department.data or self.department_text.data.strip()):
            raise ValidationError('This field is required.')


class AddUserForm(Form):
    users = SelectMultipleField('users')
