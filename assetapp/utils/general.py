#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import os
import os.path
from datetime import datetime
from time import strftime
import tempfile
from functools import wraps
from PIL import Image

from werkzeug import secure_filename
from flask import make_response, request, session, url_for, current_app
from ..models.sparepart import Sparepart
from ..models.upload import Upload


def get_upload_dir():
    return os.path.join(current_app.static_folder, 'uploads')


def get_page():
    page = request.args.get('page', '1')
    return int(page) if page.isdigit() else 1


def get_per_page():
    return session.get('per_page', 10)


def fill_form_error(form, errors, alias_dict={}):
    if hasattr(errors, '_errors'):
        errors = errors._errors

    for k, v in errors.items():
        if k in alias_dict:
            field = alias_dict[k]
        else:
            field = k

        if hasattr(form, field):
            getattr(form, field).errors = v if isinstance(v, list) else [v]


def not_cache_header(f):
    @wraps(f)
    def _not_cache_header(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        if request.user_agent.browser == 'msie':
            response.headers['Pragma'] = 'no-cache'
            response.headers['Cache-control'] = 'no-cache'
            response.headers['Expires'] = -1

        return response

    return _not_cache_header


def set_referrer():
    if 'referrer' not in session:
        session['referrer'] = request.referrer


def get_referrer(endpoint='.index'):
    return session.pop('referrer', None) or url_for(endpoint)


def get_sp_desc(code):
    if code:
        sp = Sparepart.find_one(spec=dict(code=code))
        if sp:
            return sp.desc

    return ''


def get_sp_name(code):
    if code:
        sp = Sparepart.find_one(spec=dict(code=code))
        if sp:
            return sp.name

    return ''


def save_file(fileobj, filepath):
    folder = os.path.dirname(filepath)
    if not os.path.isdir(folder):
        os.makedirs(folder)
        os.chmod(folder, 0777)

    try:
        fileobj.save(filepath)
    except Exception, e:
        current_app.logger.error(e)


def handle_uploads(ref_id):
    today = datetime.today()
    year = str(today.year)
    month = '{:02d}'.format(today.month)
    ts = strftime('%Y%m%d%H%M%S')
    upload_dir = get_upload_dir()
    for fo in request.files.getlist('pictures'):
        if fo:
            filename = secure_filename(fo.filename)
            newname = '{}_{}'.format(ts, filename)
            file_path = os.path.join(upload_dir, year, month, newname)
            save_file(fo, file_path)
            if os.path.isfile(file_path):
                im = Image.open(file_path)
                pic = Upload(ref_id=ref_id,
                             name=filename,
                             path=file_path,
                             size=list(im.size),
                             filesize=int(os.path.getsize(file_path)),
                             format=im.format,
                             ct='image/{}'.format(im.format),
                             )
                pic.save()
