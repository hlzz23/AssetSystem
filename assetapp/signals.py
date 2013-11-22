#!/usr/bin/env python
#-*- coding: utf-8 -*-

from flask.signals import Namespace

signals = Namespace()

user_updated = signals.signal('user-updated')
project_updated = signals.signal('project-updated')
department_updated = signals.signal('department-updated')
