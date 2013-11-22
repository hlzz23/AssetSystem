#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from flask.ext.wtf import (Form, TextField, SelectField, TextAreaField,
                           required, FloatField, IntegerField, number_range,
                           RadioField, ValidationError,
                           )
from .general import check_date_format, gbr


class BuyForm(Form):
    department = SelectField('department', [required()])
    project = SelectField('project', [required()])
    source = SelectField('source', [required()])
    source_remark = TextField('source_remark')

    supplier = TextField('supplier')
    mf = TextField('manufacturer')

    po = TextField('.po')
    price = FloatField('price', default=0.0)
    date = TextField('.buy_date', [required(), check_date_format])
    model = TextField('model')
    owner = TextField('owner')

    tn = TextField('.track_no')
    cn = TextField('.custom_no')
    remark = TextAreaField('remark')


class BuyEquipmentForm(BuyForm):
    model = TextField('model', [required()])
    name = TextField('equipment.name', [required()])
    sn = TextField('sn', [required()])
    location = TextField('location', [required()], default='store')
    desc = TextAreaField('description')
    ws = TextField('equipment.warranty_start')
    we = TextField('equipment.warranty_end')
    is_good = RadioField('equipment.is_good', default='good')


class BuySparepartForm(BuyForm):
    code = SelectField('spareparts.code')
    code_text = TextField('iohistory.enter_code')
    good = IntegerField('good_qty', [number_range(min=0), gbr], default=0)
    bad = IntegerField('bad_qty', [number_range(min=0)], default=0)


class ConfirmForm(Form):
    accept = RadioField('.accept', default='reject')
    remark = TextAreaField('.required_if_reject')

    def validate_remark(self, field):
        if self.accept.data == 'reject' and not field.data.strip():
            raise ValidationError('This field is required.')


class AssignForm(ConfirmForm):
    flex_id = TextField('equipment.flex_id')
    fixed_id = TextField('equipment.fixed_id')

    def check_field(self, field):
        if self.accept.data == 'accept' and not field.data.strip():
            raise ValidationError('This field is required.')

    def validate_flex_id(self, field):
        self.check_field(field)


class QueryForm(Form):
    department = SelectField('department')
    project = SelectField('project')
    word = TextField('keyword')
    start_date = TextField('start_date')
    end_date = TextField('end_date')
