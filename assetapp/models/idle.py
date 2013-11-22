#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals
from assetapp import db


class Idle(db.model):
    login = db.str(index=True, required=True)
    login_id = db.str(index=True)

    user = db.str(index=True, required=True)
    date = db.str(index=True, required=True)
    asset = db.dict(index=True)

    status = db.list(index=True)
    remark = db.str()

    @property
    def idle_date(self):
        spec = dict(status=['idle', 'recall'])
        spec['$or'] = [{'asset.flex_id': self.asset['flex_id']},
                       {'asset.sn': self.asset['sn']},
                       ]
        return self.__class__.find_one(spec=spec) or dict()

    @property
    def store_user(self):
        if self.login_id:
            from .user import User
            return User.find_one(self.login_id) or dict()

        return dict()

    @property
    def get_login(self):
        user = self.store_user
        return user.nick_name if user else self.login

    @property
    def get_status(self):
        return self.status[-1] if self.status else ''
