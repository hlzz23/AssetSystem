#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

from flask import Flask
from flask.ext.cache import Cache
from flask.ext.yamli18n import YAMLI18N
from flask.ext.mongobit import MongoBit
#from flask.ext.debugtoolbar import DebugToolbarExtension

import configs

APP_NAME = 'assetapp'
cache = Cache()
y18n = YAMLI18N()
db = MongoBit()
t = y18n.t

#toolbar = DebugToolbarExtension()


def create_app(config='prod.cfg'):
    app = Flask(APP_NAME)
    app.config.from_pyfile(config)

    configs.config_cache(cache, app)
    configs.config_database(db, app)
    configs.config_i18n(y18n, app)
    if not app.debug:
        configs.config_logging(app)

    configs.config_errorhandlers(app)
    configs.config_beforehandlers(app)
    #configs.config_debugtoolbar(toolbar, app)
    configs.config_jinja(app, t)
    configs.config_blueprints(app)

    app.y18n = y18n
    return app
