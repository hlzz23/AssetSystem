#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function
from assetapp import db, cache


# history likes
# {'user': 'xx', 'time': 'xxx',
#   'accept': True/False, 'remark': 'xxx', 'flow': 'xx'}
class Buy(db.model):
    login = db.str(index=True)
    login_id = db.str(index=True)
    department = db.str(required=True, index=True)
    project = db.str(required=True, index=True)
    source = db.str(index=True, required=True, default='other')
    source_remark = db.str()

    po = db.str(index=True)
    mf = db.str(index=True)
    supplier = db.str(index=True)
    model = db.str(index=True)
    owner = db.str(index=True)

    price = db.float(default=0.0)
    date = db.str(index=True)
    tn = db.str(index=True)
    cn = db.str(index=True)

    # 0: equipment, 1: sparepart, 2: goldenboard
    kind = db.str(index=True, required=True, default='0')
    name = db.str(index=True)
    asset = db.dict(index=True)
    history = db.list(index=True)
    workflow = db.str(index=True, default='fresh')
    remark = db.str()

    @property
    def canbe_removed(self):
        return not self.is_done

    @property
    def last_history(self):
        h = self.history
        return h[-1] if h else None

    @property
    def sparepart(self):
        from .sparepart import Sparepart
        return Sparepart.find_one(spec=dict(code=self.asset['code']))

    @classmethod
    def fresh_count(cls):
        return cls.get_count(spec=dict(workflow='fresh'))

    @classmethod
    def assign_count(cls):
        return cls.get_count(spec=dict(workflow='accept',
                                       kind='0',
                                       )
                             )

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
    def routing(self):
        if self.is_fresh:
            return '.wait_for_confirm'

        if self.is_confirmed:
            return '.wait_for_assign_id'

        return '.finished'

    @property
    def who_can_confirm(self):
        dp = self.department
        pj = self.project
        k = 'wcc{}{}'.format(dp, pj)
        rv = cache.get(k)
        if rv:
            return rv

        from .user import User
        args = ('project_leader', dp, pj)
        users = []
        for user in User.get_users(*args, fields=['nick_name']):
            users.append(user.nick_name)

        cache.set(k, sorted(users))
        return cache.get(k)

    @property
    def who_can_assign(self):
        dp = self.department
        pj = self.project
        k = 'wca{}{}'.format(dp, pj)
        rv = cache.get(k)
        if rv:
            return rv

        from .user import User
        args = ('asset_user', self.department, self.project)
        users = []
        for user in User.get_users(*args, fields=['nick_name']):
            users.append(user.nick_name)

        cache.set(k, sorted(users))
        return cache.get(k)

    @property
    def is_confirmed(self):
        return self.workflow == 'accept'

    @property
    def is_fresh(self):
        return self.workflow == 'fresh'

    @property
    def is_done(self):
        return self.workflow == 'done'
