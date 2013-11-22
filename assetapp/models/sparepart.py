#!/usr/bin/env python
#-*- coding: utf-8 -*-

from assetapp import db


# mcq: month consumed qty
# npq: next purchase qty
# cqdp: consumed qty during purchase
# alert_qty: for query fast
# if min_alert < 0, store qty is in dangerous
# if max_alert < 0, store qty is too large
class Sparepart(db.model):
    department = db.str(index=True, required=True)
    project = db.str(index=True, required=True)
    name = db.str(required=True, index=True)
    code = db.str(required=True, unique=True, index=True)
    location = db.str(required=True, index=True)

    desc = db.str(index=True)
    remark = db.str()

    model = db.str(index=True)
    prod_model = db.str(index=True)
    pn = db.str(index=True)
    store_good = db.int(default=0)
    store_bad = db.int(default=0)
    out_good = db.int(default=0)
    out_bad = db.int(default=0)
    buy_good = db.int(default=0)
    buy_bad = db.int(default=0)
    min_store = db.int(default=0)
    max_store = db.int(default=0)
    is_local = db.bool(default=True)
    lead_time = db.int(default=0)
    mcq = db.int(default=0)
    npq = db.int(default=0)
    cqdp = db.int(default=0)
    min_alert = db.int(default=0, index=True)
    max_alert = db.int(default=0, index=True)

    vendor = db.str()
    unit_price = db.float(default=0.0)

    @property
    def canbe_removed(self):
        return True

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
    def can_edit_qty(self):
        if self.has_buys:
            return False

        if self.has_iorecords:
            return False

        if self.has_transfers:
            return False

        return True

    @property
    def has_buys(self):
        from .buy import Buy
        spec = dict(kind='1', workflow='fresh')
        spec['asset.code'] = self.code
        return Buy.find_one(spec=spec)

    @property
    def has_iorecords(self):
        from .iorecord import Iorecord
        spec = dict(kind='1')
        spec['asset.code'] = self.code
        return Iorecord.find_one(spec=spec)

    @property
    def has_transfers(self):
        from .transfer import Transfer
        spec = dict(kind='1')
        spec['asset.code'] = self.code
        return Transfer.find_one(spec=spec)

    @classmethod
    def ok_qty(cls):
        return cls.get_count(spec=dict(min_alert={'$gt': 0},
                                       max_alert={'$gt': 0},
                                       )
                             )

    @classmethod
    def danger_qty(cls):
        return cls.get_count(spec={'$or': [dict(min_alert={'$lt': 0}),
                                           dict(max_alert={'$lt': 0})]
                                   }
                             )

    def get_qty(self, kind='good', tp='store'):
        return getattr(self, kind)[tp]

    def pre_store_alert(self):
        if self.min_store > 0:
            self.min_alert = self.store_good - self.min_store

        if self.max_store > 0:
            self.max_alert = self.max_store - self.store_good
