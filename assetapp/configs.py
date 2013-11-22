#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import re
import os
import os.path
import logging
from logging import Formatter
from logging.handlers import SMTPHandler, RotatingFileHandler

from flask import g, redirect, url_for, request, session

hl_css = '<span class="hl-query">{}</span>'


def config_cache(cache, app):
    cache.init_app(app)


def config_i18n(y18n, app):
    y18n.reload = app.debug
    y18n.init_app(app)


def config_database(db, app):
    db.init_app(app)


def config_blueprints(app):
    from .views import home
    from .views import users
    from .views import projects
    from .views import buys
    from .views import equipment
    from .views import spareparts
    from .views import permissions
    from .views import iorecords
    from .views import transfers
    from .views import scraps
    from .views import idles

    app.register_blueprint(home.mod)
    app.register_blueprint(users.mod, url_prefix='/users')
    app.register_blueprint(permissions.mod, url_prefix='/permissions')
    app.register_blueprint(projects.mod, url_prefix='/projects')
    app.register_blueprint(spareparts.mod, url_prefix='/spareparts')
    app.register_blueprint(equipment.mod, url_prefix='/equipment')
    app.register_blueprint(buys.mod, url_prefix='/buys')
    app.register_blueprint(iorecords.mod, url_prefix='/iohistory')
    app.register_blueprint(transfers.mod, url_prefix='/transfers')
    app.register_blueprint(scraps.mod, url_prefix='/scraps')
    app.register_blueprint(idles.mod, url_prefix='/idles')


def config_jinja(app, t):
    def hl_query(text, keyword):
        if keyword:
            match = re.search(re.escape(keyword), text, re.I)
            if match:
                s = match.start()
                e = match.end()
                return '{}{}{}'.format(text[:s],
                                       hl_css.format(text[s:e]),
                                       text[e:]
                                       )

        return text

    def bool_msg(bs, yes='yes', no='no'):
        return t(yes) if bs else t(no)

    def get_args(req_args):
        args = req_args.to_dict()
        args.pop('page', None)
        return args

    app.jinja_env.filters['t'] = t
    app.jinja_env.filters['hl_query'] = hl_query
    app.jinja_env.filters['bool_msg'] = bool_msg
    app.jinja_env.filters['get_args'] = get_args
    app.jinja_env.add_extension('jinja2.ext.do')


def config_errorhandlers(app):
    @app.errorhandler(404)
    def page_not_found(error):
        return redirect(url_for('home.index'))

    @app.errorhandler(500)
    def server_error(error):
        return render_template('home/500.html'), 500


def config_beforehandlers(app):
    from .models.user import User

    @app.before_first_request
    def before_first_request():
        session['per_page'] = 10
        if 'lang' not in session:
            session['lang'] = 'en'

        session.permanent = True

    @app.before_request
    def before_request():
        endpoint = request.endpoint
        if 'user_id' in session:
            g.user = User.find_one(session['user_id'])
        else:
            g.user = None

        if 'lang' not in session:
            session['lang'] = g.user.lang if g.user else 'zh'

        blueprint = request.blueprint
        url = str(request.url)
        if endpoint == 'iohistory.outstore' or 'kind=out' in url:
            g.css_id = 'outstore'
        elif endpoint == 'iohistory.instore' or 'kind=in' in url:
            g.css_id = 'instore'
        elif blueprint == 'permissions':
            g.css_id = 'users'
        elif blueprint in ('users', 'iohistory', 'buys', 'scraps',
                           'spareparts', 'equipment', 'projects',
                           'transfers', 'idles'):
            g.css_id = blueprint
        else:
            g.css_id = 'home'


def config_debugtoolbar(toolbar, app):
    toolbar.init_app(app)


def config_logging(app):
    config = app.config
    smtp = config.get('SMTP')
    sender = config.get('SENDER')
    webmaster = ['{}@cn.flextronics.com'.format(name)
                 for name in config.get('WEBMASTER', [])]
    use_email = (smtp and sender and webmaster)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    )

    log_dir = os.path.join(app.root_path, 'logs')
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
        os.chmod(log_dir, 0755)

    # error logger
    error_log = os.path.join(log_dir, config['ERROR_LOG'])
    log_handler = RotatingFileHandler(error_log,
                                      maxBytes=100000,
                                      backupCount=10, )
    log_handler.setLevel(logging.WARN)
    log_handler.setFormatter(formatter)
    app.logger.addHandler(log_handler)

    # email logger
    fmt = '''
        Message type:        %(levelname)s
        Location:            %(pathname)s:%(lineno)d
        Module:              %(module)s
        Function:            %(funcName)s
        Time:                %(asctime)s

        Message:

        %(message)s
        '''
    if use_email:
        mail_handler = SMTPHandler(smtp,
                                   sender,
                                   webmaster,
                                   'Your application failed'
                                   )
        mail_handler.setLevel(logging.ERROR)
        mail_handler.setFormatter(Formatter(fmt))
        app.logger.addHandler(mail_handler)
