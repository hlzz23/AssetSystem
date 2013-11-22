#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
sys.path.insert(0, '..')

from assetapp import create_app, db
create_app()

from assetapp.models.user import User
from assetapp.models.sparepart import Sparepart
from assetapp.models.iorecord import Iorecord
from assetapp.models.buy import Buy
from assetapp.models.equipment import Equipment
from assetapp.models.transfer import Transfer
from assetapp.models.idle import Idle
from assetapp.models.scrap import Scrap
from assetapp.models.permission import Permission

alias = db.app.config['alias']
for model in (User, Sparepart, Iorecord, Buy, Equipment,
              Transfer, Idle, Scrap, Permission,
              ):
    for idx in model._index_fields:
        db.mongo.create_index(alias, model, idx)
