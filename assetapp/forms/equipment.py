#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from flask.ext.wtf import (Form, TextField, SelectField, required,
                           TextAreaField, FloatField,
                           DateField, RadioField, optional,
                           )
from .general import ExportForm, ImportForm, check_date_format


class EquipmentForm(Form):
    department = SelectField('department', [required()])
    project = SelectField('project', [required()])
    source = SelectField('source')
    source_text = TextField('equipment.source_text')
    sr = TextField('source_remark')
    supplier = TextField('supplier')
    mf = TextField('manufacturer')
    name = TextField('name', [required()])
    prod_date = TextField('equipment.prod_date', [check_date_format])
    desc = TextAreaField('description')

    flex_id = TextField('equipment.flex_id', [required()])
    sn = TextField('sn', [required()])
    fixed_id = TextField('equipment.fixed_id')
    tn = TextField('buys.track_no')
    cn = TextField('buys.custom_no')

    owner = TextField('owner')
    model = TextField('model')
    price = FloatField('price', default=0.0)

    line = TextField('line')
    location = TextField('location')
    ws = TextField('equipment.warranty_start', [check_date_format])
    we = TextField('equipment.warranty_end', [check_date_format])

    is_good = RadioField('equipment.is_good', default='good')
    is_instore = RadioField('equipment.is_instore', default='in')

    req_user = TextField('equipment.req_user')
    req_date = TextField('equipment.req_date')
    req_remark = TextAreaField('equipment.req_remark')


class QueryForm(Form):
    department = SelectField('department')
    project = SelectField('project')
    model = TextField('model')
    line = TextField('line')
    word = TextField('keyword')


class LocationForm(Form):
    location = TextField('location', [required()])
    is_good = RadioField('equipment.is_good', default='good')
