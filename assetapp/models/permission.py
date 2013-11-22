#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function
from assetapp import db


class Permission(db.model):
    group = db.str(index=True, unique=True)
    role = db.str(index=True, required=True)
    department = db.str(index=True)
    projects = db.list(index=True)
    remark = db.str()
    is_active = db.bool(default=True)

    @property
    def canbe_removed(self):
        return True

    @property
    def dept_name(self):
        return 'all' if self.department == '*' else self.department

    @property
    def is_asset_leader(self):
        return self.role == 'asset_leader'

    @property
    def users(self):
        from .user import User
        return User.find(spec=dict(groups=self.group))

    @property
    def status(self):
        return '.active' if self.is_active else '.disabled'

    @classmethod
    def asset_leader_groups(cls):
        return [p.group for p in cls.find(spec=dict(role='asset_leader'))]

    @classmethod
    def groups_for_user(cls, user):
        spec = dict(group={'$in': user.groups})
        return [p.group for p in cls.find(spec=spec)]

    @classmethod
    def get_groups(cls, role, department, project, is_active=True):
        spec = dict(is_active=is_active,
                    role=role,
                    department={'$in': ['*', department]},
                    projects=project,
                    )
        return [p.group for p in cls.find(spec=spec)]
