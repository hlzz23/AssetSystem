#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals
import re
from flask.ext.wtf import Form, ValidationError
date_re = re.compile(r'^\d{4}-\d{2}-\d{2}$')
time_re = re.compile(r'^\d{2}:\d{2}$')


# good_or_bad_required
def gbr(form, field):
    if form.good.data == 0 and form.bad.data == 0:
        raise ValidationError('This field is required.')


def check_date_format(form, field):
    text = unicode(field.data).strip()
    if text and not date_re.match(text):
        raise ValidationError('invalid_date')


def check_time_format(form, field):
    text = unicode(field.data).strip()
    if text and not time_re.match(text):
        raise ValidationError('invalid_time')


class ExportForm(Form):
    pass


class ImportForm(Form):
    pass
