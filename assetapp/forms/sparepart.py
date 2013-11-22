#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask.ext.wtf import (Form, SelectField, TextField, TextAreaField,
                           required, IntegerField, RadioField, number_range,
                           FloatField,
                           )
from .general import ExportForm, ImportForm


class SparepartForm(Form):
    department = SelectField('department', [required()])
    project = SelectField('project', [required()])
    name = TextField('name', [required()])
    code = TextField('.number', [required()])
    unit_price = FloatField('.unit_price', default=0.0)
    vendor = TextField('.vendor')
    location = TextField('location', [required()])
    model = TextField('model')
    prod_model = TextField('.prod_model')
    pn = TextField('pn')
    out_good = IntegerField('.out_good', [number_range(min=0)], default=0)
    out_bad = IntegerField('.out_bad', [number_range(min=0)], default=0)
    store_good = IntegerField('.store_good', [number_range(min=0)], default=0)
    store_bad = IntegerField('.store_bad', [number_range(min=0)], default=0)
    desc = TextAreaField('description')
    remark = TextAreaField('remark')


class StockForm(Form):
    max_store = IntegerField('.max_store', [number_range(min=0)], default=0)
    # min store spec
    min_store = IntegerField('.min_store', [number_range(min=0)], default=0)
    is_local = RadioField('.vendor_type', default='local')
    mcq = IntegerField('.month_consumed_qty', [number_range(min=0)], default=0)
    lead_time = IntegerField('.lead_time', [number_range(min=0)], default=0)


class QueryForm(Form):
    dp = SelectField('department')
    pj = SelectField('project')
    word = TextField('keyword')
