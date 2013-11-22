#!/usr/bin/env python
#-*- coding: utf-8 -*-

from assetapp import db


class Transfer(db.model):
    login = db.str(index=True)
    login_id = db.str(index=True)

    user = db.str(index=True, required=True)
    date = db.str(index=True, required=True)
    name = db.str(index=True, required=True)
    model = db.str(index=True)

    is_in = db.bool(index=True, default=True)

    # kind: 0 = equipment, 1 = sparepart, 2 = goldenboard
    kind = db.str(index=True, default='0')
    asset = db.dict(index=True)

    remark = db.str()

    @property
    def is_activate(self):
        return self.asset['done']

    @property
    def store_user(self):
        return self.login

    @property
    def kind_name(self):
        if self.is_sparepart:
            return 'sparepart'
        elif self.is_equipment:
            return 'equipment'
        else:
            return 'goldenboard'

    @property
    def department(self):
        return self.asset['department']

    @property
    def project(self):
        return self.asset['project']

    @property
    def from_where(self):
        return self.asset['from_where']

    @property
    def to_where(self):
        return self.asset['to_where']

    @property
    def good_qty(self):
        return self.asset['good']

    @property
    def bad_qty(self):
        return self.asset['bad']

    @property
    def is_sparepart(self):
        return self.kind == '1'

    @property
    def is_equipment(self):
        return self.kind == '0'

    @property
    def is_goldenboard(self):
        return self.kind == '2'

    @property
    def sparepart(self):
        from .sparepart import Sparepart
        return Sparepart.find_one(spec=dict(code=self.asset['code'])) or dict()
