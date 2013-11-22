#!/usr/bin/env python
#-*- coding: utf-8 -*-

from assetapp import create_app

app = create_app(config='dev.cfg')
app.run(host='0.0.0.0', port=5000)
