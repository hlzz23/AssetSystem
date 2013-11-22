#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals
from datetime import datetime
from flask.ext.wtf import (Form, SelectField, TextField, TextAreaField,
                           IntegerField, required, ValidationError,
                           number_range, RadioField,
                           )
from .general import ExportForm, check_date_format, gbr


class GeneralForm(Form):
    name = TextField('name', [required()])
    model = TextField('model')
    date = TextField('date', [required(), check_date_format])
    user = TextField('handle_user', [required()])
    where = TextField('.from_where', [required()])
    remark = TextAreaField('remark')

    def validate_date(self, field):
        if field.data > datetime.today().strftime('%Y-%m-%d'):
            raise ValidationError('invalid_date')


class InForm(Form):
    department = SelectField('department', [required()])
    project = SelectField('project', [required()])


class EquipmentForm(GeneralForm):
    pass


class EquipmentInForm(EquipmentForm, InForm):
    flex_id = TextField('equipment.flex_id')
    sn = TextField('sn', [required()])
    fixed_id = TextField('equipment.fixed_id')
    prod_date = TextField('equipment.prod_date', [check_date_format])
    cn = TextField('buys.custom_no')
    tn = TextField('buys.track_no')
    is_good = RadioField('equipment.is_good', default='good')
    to_where = TextField('.to_where', [required()])


class EquipmentOutForm(EquipmentForm):
    flex_id = TextField('equipment.flex_id', [required()])
    name = TextField('name')
    model = TextField('model')


class SparepartForm(GeneralForm, InForm):
    name = TextField('name')
    code = SelectField('spareparts.code')
    code_text = TextField('iohistory.enter_code')
    good = IntegerField('good_qty', [number_range(min=0), gbr], default=0)
    bad = IntegerField('bad_qty', [number_range(min=0)], default=0)


class SparepartInForm(SparepartForm):
    pass


class SparepartOutForm(SparepartForm):
    pass


class QueryForm(Form):
    department = SelectField('department')
    project = SelectField('project')
    start_date = TextField('start_date')
    end_date = TextField('end_date')
    word = TextField('keyword')
