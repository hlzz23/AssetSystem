#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from flask import g
from ..models.permission import Permission
from ..models.equipment import Equipment
from ..models.buy import Buy
from ..models.user import User
from ..models.project import Project
from ..models.sparepart import Sparepart
from ..models.iorecord import Iorecord
from assetapp import t

two_format = '{} -> {}'
three_format = '{} -> {} -> {}'


sc_choices = [('Customer Consigned', 'Customer Consigned'),
              ('New Order', 'New Order'),
              ('Other', 'Other'),
              ('Rent', 'Rent'),
              ('Transfer From Others', 'Transfer From Others'),
              ]


def bool_choices(yes='yes', no='no'):
    return [(1, t(yes)), (0, t(no))]


def all_choices(label='all'):
    return [('*', t(label))]


def blank_choices(label='please_select'):
    return [('', t(label))]


def department_choices(with_all=False):
    departments = set()
    [departments.add((d, d)) for d in Permission.distinct('department')
     if d != '*']
    [departments.add((d, d)) for d in Equipment.distinct('department')]
    [departments.add((d, d)) for d in Sparepart.distinct('department')]
    if with_all:
        return blank_choices() + all_choices() + sorted(departments)

    return blank_choices() + sorted(departments)


def limited_department_choices(user):
    if user.is_root:
        return department_choices()

    departments = user.departments
    if '*' in departments:
        return department_choices()

    return [(d, d) for d in departments]


def project_choices(with_all=None):
    if with_all is None:
        with_all = g.user.is_root

    if with_all is True:
        return blank_choices() + sorted((p.name, p.name)
                                        for p in Project.find())

    return blank_choices() + sorted((project, project)
                                    for project in g.user.projects)


def source_choices():
    return blank_choices() + sc_choices

    lst = set()
    for m in (Buy, Equipment):
        [lst.add((s, s)) for s in m.distinct('source')]

    return blank_choices() + (sorted(list(lst)) or sc_choices)


def code_choices(dept=None, project=None):
    choices = blank_choices()
    if dept and project:
        spec = dict(department=dept, project=project)
        fields = ['code', 'name', 'pn']
        for sp in Sparepart.find(spec=spec, fields=fields, sort='code'):
            choices.append(get_choice(sp))

        return choices

    return choices


def get_choice(sp):
    if sp.pn:
        return (sp.code, three_format.format(sp.code, sp.pn, sp.name))

    return (sp.code, two_format.format(sp.code, sp.name))


def role_choices(asset_leader=False):
    s = 'permissions'
    lst = [('asset_user', t('{}.asset_user'.format(s))),
           ('store_user', t('users.store_user')),
           ('project_leader', t('{}.project_leader'.format(s))),
           # ('cal_user', t('{}.cal_user'.format(s))),
           ]
    if asset_leader is True:
        lst.insert(0, ('asset_leader', t('{}.asset_leader'.format(s))))

    return blank_choices() + lst


def get_users_for_permission(p):
    spec = dict(login={'$ne': 'root'})
    return [(u.login, u.nick_name) for u in User.find(spec=spec)]
    if g.user.is_root:
        spec['$or'] = [dict(groups={'$size': 0}),
                       dict(groups={'$in': Permission.asset_leader_groups()}),
                       ]
        return [(u.login, u.nick_name) for u in User.find(spec=spec)]

    spec['$or'] = [dict(groups=[]), dict(groups=p.group), ]
    return [(u.login, u.nick_name) for u in User.find(spec=spec)]


def iouser_list():
    return Iorecord.distinct('user')


def badgeid_list():
    return Iorecord.distinct('uid')
