#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals
from assetapp import db


class Scrap(db.model):
    login = db.str(index=True, required=True)
    login_id = db.str(index=True)

    user = db.str(index=True, required=True)
    date = db.str(index=True, required=True)
    asset = db.dict(index=True)

    remark = db.str()
