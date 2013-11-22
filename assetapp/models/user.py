#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from werkzeug import generate_password_hash, check_password_hash
from assetapp import db


# can_send:
#   > buy:      incomings arrived
#   > io:       store in/out
#   > tf:       transfer in/out
#   > idle:     asset idle
#   > scrap:    equipment scrap
#   > alarm:    store qty alarm
#   > notify:   incomings confirmation notification
class User(db.model):
    login = db.str(unique=True, required=True, index=True)
    hash_pass = db.str()
    nick_name = db.str(required=True, unique=True, index=True)
    email = db.str(unique=True, index=True)
    badge_id = db.str(unique=True, required=True)
    lang = db.str(default='zh')
    gsm = db.str()
    phone = db.str()
    short_no = db.str()
    is_active = db.bool(default=True)
    can_send = db.list(index=True,
                       default=['buy', 'io', 'tf', 'idle', 'scrap',
                                'alarm', 'notify',
                                ],

                       )
    groups = db.list()

    def __getattr__(self, attr):
        if attr == 'password':
            return 'Everything is nothing.'

        return dict.__getitem__(self, attr)

    def __setattr__(self, attr, val):
        if attr == 'password':
            attr = 'hash_pass'
            val = generate_password_hash(val)

        object.__setattr__(self, attr, val)

    @property
    def canbe_removed(self):
        return not self.is_root

    @property
    def status(self):
        return '.active' if self.is_active else '.disabled'

    @property
    def is_root(self):
        return self.login == 'root'

    @property
    def projects(self):
        from .permission import Permission
        projects = set()
        spec = dict(is_active=True,
                    group={'$in': self.groups},
                    )
        for p in Permission.find(spec=spec):
            [projects.add(project) for project in p.projects]

        return sorted(projects)

    @property
    def departments(self):
        from .permission import Permission
        departments = set()
        spec = dict(is_active=True,
                    group={'$in': self.groups},
                    )
        for p in Permission.find(spec=spec):
            departments.add(p.department)

        return sorted(departments)

    @property
    def permissions(self):
        from .permission import Permission
        return Permission.find(spec=dict(group={'$in': self.groups}),
                               sort='group',
                               )

    @classmethod
    def authenticate(cls, login, password):
        user = cls.find_one(spec=dict(login=login))
        if user and check_password_hash(user.hash_pass, password):
            return user

        return None

    def is_role(self, role):
        if self.is_root:
            return True

        from .permission import Permission
        spec = dict(role=role,
                    group={'$in': self.groups},
                    is_active=True,
                    )
        return Permission.find_one(spec=spec) is not None

    def check_departments(self, dept):
        departments = self.departments
        return '*' in departments or dept in departments

    @property
    def is_asset_leader(self):
        return self.is_role('asset_leader')

    @property
    def is_asset_user(self):
        return self.is_role('asset_user')

    @property
    def is_store_user(self):
        return self.is_role('store_user')

    @property
    def is_project_leader(self):
        return self.is_role('project_leader')

    # permission operations
    @property
    def can_create_permission(self):
        return self.is_asset_leader

    @property
    def can_add_permission(self):
        return self.can_create_permission

    def can_edit_permission(self, p):
        if self.is_root:
            return True

        if not self.is_asset_leader:
            return False

        if p.role == 'asset_leader':
            return False

        return set(p.projects).issubset(set(self.projects))

    def can_remove_permission(self, p):
        return self.can_edit_permission(p)

    # user operations
    @property
    def can_create_user(self):
        '''asset_leader is required'''
        return self.is_asset_leader

    @property
    def can_add_user(self):
        return self.can_create_user

    def can_edit_user(self, user):
        '''asset_leader is required, user should not be asset_leader'''
        if self.id == user.id or self.is_root:
            return True

        if not self.is_asset_leader or user.is_asset_leader:
            return False

        return set(user.projects).issubset(set(self.projects))

    def can_remove_user(self, user):
        '''asset_leader is required, user cannot be asset_leader'''
        if user.is_root:
            return False

        if self.is_root:
            return True

        if user.is_asset_leader or not self.is_asset_leader:
            return False

        return set(user.projects).issubset(set(self.projects))

    # sparepart operations
    @property
    def can_create_sparepart(self):
        return self.is_store_user

    @property
    def can_add_sparepart(self):
        return self.can_create_sparepart

    def can_edit_sparepart(self, sp):
        '''store_user required'''
        if self.is_root:
            return True

        if not self.is_store_user:
            return False

        if sp.project not in self.projects:
            return False

        return self.check_departments(sp.department)

    def can_remove_sparepart(self, sp):
        return self.can_edit_sparepart(sp)

    def can_set_stock(self, sp):
        if self.is_root:
            return True

        if not (self.is_asset_leader
                or self.is_project_leader
                or self.is_asset_user
                or self.is_store_user
                ):
            return False

        if sp.project not in self.projects:
            return False

        return self.check_departments(sp.department)

    # equipment operations
    @property
    def can_create_equipment(self):
        return self.is_asset_user

    @property
    def can_add_equipment(self):
        return self.can_create_equipment

    def can_edit_equipment(self, e):
        if self.is_root:
            return True

        if not self.is_asset_user:
            return False

        if e.project not in self.projects:
            return False

        return self.check_departments(e.department)

    def can_remove_equipment(self, e):
        # return self.can_edit_equipment(e)

        if self.is_root:
            return True

        if not self.is_asset_user:
            return False

        if e.project not in self.projects:
            return False

        return self.check_departments(e.department)

    def can_update_location(self, e):
        if not e.is_instore:
            return False

        if self.is_root:
            return True

        if not self.is_store_user or not self.is_asset_user:
            return False

        if e.project not in self.projects:
            return False

        return self.check_departments(e.department)

    def can_repair_equipment(self, e):
        if e.is_good:
            return False

        if self.is_root:
            return True

        if not self.is_store_user:
            return False

        return self.check_departments(e.department)

    # buy operations
    @property
    def can_create_buy(self):
        return self.is_store_user

    @property
    def can_add_buy(self):
        return self.can_create_buy

    def can_edit_buy(self, buy):
        # only fresh or rejected can be updated
        if not buy.is_fresh:
            return False

        if self.is_root:
            return True

        if not self.is_store_user:
            return False

        return (buy.project in self.projects
                and self.check_departments(buy.department)
                )

    def can_remove_buy(self, buy):
        if buy.is_done:
            return False

        if self.is_root:
            return True

        if not self.is_store_user:
            return False

        return (buy.project in self.projects
                and self.check_departments(buy.department)
                )

    def can_confirm(self, buy):
        if not buy.is_fresh:
            return False

        if self.is_root:
            return True

        if not self.is_project_leader:
            return False

        return (buy.project in self.projects and
                buy.department in self.departments)

    def can_assign(self, buy):
        # only confirmed equipment can be assigned flex id
        # spare part does not need flex id
        if buy.is_sparepart or not buy.is_confirmed:
            return False

        if self.is_root:
            return True

        if not self.is_asset_user:
            return False

        return (buy.project in self.projects
                and self.check_departments(buy.department)
                )

    # project operations
    @property
    def can_create_project(self):
        return self.is_asset_leader

    @property
    def can_add_project(self):
        return self.can_create_project

    def can_edit_project(self, project):
        '''asset_leader is required'''
        return self.can_create_project

    def can_remove_project(self, project):
        return self.can_edit_project(project)

    @property
    def can_create_scrap(self):
        return self.is_asset_user

    @property
    def can_add_scrap(self):
        return self.can_create_scrap

    def can_scrap_equipment(self, ep):
        if self.is_root:
            return True

        if not self.is_asset_user:
            return False

        return self.check_departments(ep.department)

    @property
    def can_create_idle(self):
        return self.is_asset_user

    @property
    def can_add_idle(self):
        return self.can_create_idle

    def can_idle_equipment(self, ep):
        return self.can_scrap_equipment(ep)

    def can_recall_idle(self, idle):
        from .equipment import Equipment
        flex_id = idle.asset['flex_id']
        e = Equipment.find_one(spec=dict(flex_id=flex_id))
        if not e:
            return False

        return self.can_idle_equipment(e)

    @property
    def can_create_transfer(self):
        return self.is_asset_user

    @property
    def can_add_transfer(self):
        return self.can_create_transfer

    def can_transfer_equipment(self, ep):
        return self.can_scrap_equipment(ep)

    # importings
    def can_import_equipment(self, department, project):
        if self.is_root:
            return True

        if not self.is_asset_user:
            return False

        return (project in self.projects
                and self.check_departments(department)
                )

    def can_update_sparepart_qty(self, department, project):
        if self.is_root:
            return True

        if not self.is_asset_user:
            return False

        return (project in self.projects
                and self.check_departments(department)
                )

    def can_update_sparepart_price(self, department, project):
        if self.can_import_sparepart(department, project):
            return True

        return self.can_update_sparepart_qty(department, project)

    def can_import_sparepart(self, department, project):
        if self.is_root:
            return True

        if not self.is_store_user:
            return False

        return (project in self.projects
                and self.check_departments(department)
                )

    # store user only can in/out his/her depatment and projects assets
    def can_io_asset(self, asset):
        if self.is_root:
            return True

        return (asset.project in self.projects
                and self.check_departments(asset.department)
                )

    @classmethod
    def get_users(cls, role, department, project, kind=None, fields=None):
        from .permission import Permission
        groups = Permission.get_groups(role, department, project)
        spec = dict(is_active=True, groups={'$in': groups})
        if kind:
            spec.update(can_send=kind)

        return [user for user in cls.find(spec=spec, fields=fields)]

    @classmethod
    def get_emails(cls, role, department, project, kind=None):
        emails = []
        for user in cls.get_users(role, department, project,
                                  kind=kind, fields=['email']):
            if user.email:
                emails.append(user.email)

        return emails
