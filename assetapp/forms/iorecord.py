#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from datetime import datetime
from flask.ext.wtf import (Form, TextField, TextAreaField, SelectField,
                           RadioField, IntegerField, required, number_range,
                           ValidationError,
                           )
from .general import ExportForm, check_date_format, gbr, check_time_format


class GeneralForm(Form):
    user = TextField('.user', [required()])
    uid = IntegerField('badge_id', [required(), number_range(min=10000)])
    date = TextField('.io_date', [required(), check_date_format])
    time = TextField('.io_time', [required(), check_time_format])
    hard_copy = TextField('.hard_copy')
    remark = TextAreaField('remark', [required()])

    def validate_date(self, field):
        if field.data > datetime.today().strftime('%Y-%m-%d'):
            raise ValidationError('invalid_date')

class OutSNForm(Form):
    code_text = TextField('.enter_code', [required()])

class BackEquipmentForm(GeneralForm):
    flex_id = TextField('equipment.flex_id', [required()])
    location = TextField('location', [required()])
    is_good = RadioField('equipment.is_good', default='good')


class SparepartForm(GeneralForm):
    department = SelectField('department', [required()])
    project = SelectField('project', [required()])
    code = SelectField('spareparts.code')
    code_text = TextField('.enter_code')
    good = IntegerField('good_qty', [number_range(min=0), gbr], default=0)
    bad = IntegerField('bad_qty', [number_range(min=0)], default=0)


class BackSparepartForm(SparepartForm):
    pass


class OutEquipmentForm(GeneralForm):
    flex_id = TextField('equipment.flex_id', [required()])
    to_project = SelectField('.to_project', [required()])
    to_where = TextField('.to_where', [required()])
    line = TextField('line')


class OutSparepartForm(SparepartForm):
    to_project = SelectField('.to_project', [required()])
    to_where = TextField('.to_where', [required()])
    line = TextField('line')


class QueryForm(Form):
    department = SelectField('department')
    project = SelectField('project')
    word = TextField('keyword')
    start_date = TextField('start_date')
    end_date = TextField('end_date')
