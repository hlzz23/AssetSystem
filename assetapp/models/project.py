#!/usr/bin/env python
#-*- coding: utf-8 -*-

from assetapp import db


class Project(db.model):
    name = db.str(index=True, unique=True, required=True)
    remark = db.str()

    @property
    def canbe_removed(self):
        return not self.has_permissions

    @property
    def has_permissions(self):
        from .permission import Permission
        spec = dict(projects=self.name)
        return Permission.find_one(spec=spec)
