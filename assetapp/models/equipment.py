#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
from assetapp import db


class Equipment(db.model):
    coll_name = 'equipment'

    department = db.str(required=True, index=True)
    project = db.str(required=True, index=True)
    source = db.str(required=True, index=True, default='other')
    sr = db.str()  # source remark
    supplier = db.str(index=True)
    mf = db.str(index=True)  # manufacturer
    name = db.str(required=True, index=True)
    prod_date = db.str(index=True)

    desc = db.text()

    flex_id = db.str(required=True, index=True, unique=True)
    sn = db.str(required=True, index=True, unique=True)
    fixed_id = db.str(index=True, unique=True)
    tn = db.str(index=True)  # tracking no
    cn = db.str(index=True)  # customs no

    owner = db.str(index=True)
    model = db.str(index=True)
    price = db.float(index=True)
    line = db.str(index=True)
    location = db.str(index=True)
    ws = db.str(index=True)  # warranty_start
    we = db.str(index=True)  # warranty_end
    is_good = db.bool(default=True)
    is_instore = db.bool(default=True)
    is_live = db.bool(default=True)
    status = db.list(index=True)  # scrap, idle, transfer

    req_user = db.str(index=True)
    req_date = db.str(index=True)
    req_remark = db.str()

    need_cal = db.bool(default=False)
    need_pm = db.bool(default=False)

    @property
    def canbe_removed(self):
        return True
        return not (self.has_iorecords or self.has_buys)

    @property
    def get_status(self):
        return self.status[-1] if self.status else ''

    @property
    def spec_for_foreign(self):
        spec = dict(kind='0', asset_id=str(self.id))
        return spec

    @property
    def has_iorecords(self):
        from .iorecord import Iorecord
        return Iorecord.find_one(spec=self.spec_for_foreign)

    @property
    def has_buys(self):
        from .buy import Buy
        return Buy.find_one(spec=self.spec_for_foreign)

    @property
    def uploads(self):
        from .upload import Upload
        return Upload.find(spec=dict(ref_id=str(self.id)))

    @property
    def image_link(self):
        from .upload import Upload
        upload = Upload.find_one(spec=dict(ref_id=str(self.id)))
        return upload.link if upload else None

    @property
    def to_project(self):
        from .iorecord import Iorecord
        spec = {'asset.flex_id': self.flex_id}
        io = Iorecord.find_one(spec=spec, sort='updated_at desc')
        return io.to_project if io else ''

    @property
    def to_line(self):
        return self.line

    @property
    def to_location(self):
        return self.location

    @property
    def latest_location(self):
        if self.is_instore:
            return self.location

        location = []
        to_project = self.to_project
        if to_project:
            location.append(to_project)

        if self.to_line:
            location.append(self.to_line)

        if self.to_location and self.to_location not in location:
            location.append(self.to_location)

        return ', '.join(location)

    # def check_unique(self, fields=None, cs=False):
    #     cls = self.__class__
    #     if fields is None:
    #         fields = cls._unique_fields

    #     update = not self._is_new
    #     for field in fields:
    #         spec = self.get_spec(field, self, cs=cs)
    #         if isinstance(spec, dict):
    #             spec.update(is_live=True)
    #             if update is True:
    #                 spec.update(_id={'$ne': self.id})

    #             if cls.find_one(spec=spec):
    #                 self._errors[field] = 'is already taken'
