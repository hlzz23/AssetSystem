#!/usr/bin/env python
#-*- coding: utf-8 -*-

from assetapp import db


# asset likes:
# 1. sparepart
#   {'iogood': xx, 'iobad': xx, 'to': 'xx', [sparepart attributes]}
# 2. equipment
#   {'to': 'xx', [location: 'xx'], [equipment attributes]}
class Iorecord(db.model):
    login = db.str(index=True)
    login_id = db.str(index=True)  # badge id
    user = db.str(index=True, required=True)
    uid = db.str(index=True, required=True)
    date = db.str(index='desc', required=True)
    time = db.str(index='date,time', required=True)
    is_out = db.bool(default=True)

    # 0 = equipment, 1 = sparepart, 2 = goldenboard
    kind = db.str(required=True, default='0')
    department = db.str(index=True)
    project = db.str(index=True)
    asset = db.dict(index=True)
    name = db.str(index=True)
    hard_copy = db.str(index=True)

    remark = db.text()

    @property
    def direction(self):
        return '.out_store' if self.is_out else '.into_store'

    @property
    def from_user(self):
        return self.login if self.is_out else self.user

    @property
    def to_user(self):
        return self.user if self.is_out else self.login

    @property
    def from_uid(self):
        return self.login_id if self.is_out else self.uid

    @property
    def to_uid(self):
        return self.uid if self.is_out else self.login_id

    @property
    def asset_status(self):
        return self.asset.get('iogood', '')

    @property
    def good_qty(self):
        return self.asset.get('iogood', '0')

    @property
    def bad_qty(self):
        return self.asset.get('iobad', '0')

    @property
    def to_project(self):
        return self.asset.get('to_project', '')

    @property
    def to_where(self):
        return self.asset.get('to_where', '')

    @property
    def to_line(self):
        return self.asset.get('to_line', '')

    @property
    def to_location(self):
        location = []
        if self.to_project:
            location.append(self.to_project)

        if self.to_line and self.to_line not in location:
            location.append(self.to_line)

        if self.to_where and self.to_where not in location:
            location.append(self.to_where)

        return ', '.join(location)

    @property
    def kind_name(self):
        if self.is_sparepart:
            return 'sparepart'
        elif self.is_equipment:
            return 'equipment'
        else:
            return 'goldenboard'

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
    def keyid(self):
        if self.is_sparepart:
            return self.asset.get('code', '')
        else:
            return self.asset.get('flex_id', '')
