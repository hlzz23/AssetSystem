#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import os
import os.path
from assetapp import db, t


class Upload(db.model):
    ref_id = db.str(index=True, required=True)
    name = db.str(index=True, required=True)
    path = db.str()
    size = db.list()
    filesize = db.int()
    format = db.str()
    ct = db.str()  # content type

    @property
    def link(self):
        return self.path.replace('\\', '/').split('/static/')[-1]

    @property
    def width(self):
        if 'image' in self.ct and self.size:
            return self.size[0]

        return 0

    @property
    def img_width(self):
        if self.width > 800:
            return '{}%'.format(self.width_rate * 100)
            width = self.width * self.width_rate
            return width if width < 800 else 800

        return self.width

    @property
    def img_height(self):
        if self.height > 600:
            return '{}%'.format(self.height_rate * 100)
            height = self.height * self.height_rate
            return height if height > 600 else 600

        return self.height

    @property
    def width_rate(self):
        if self.width > 0 and self.height > 0:
            return 1.0 * self.width / (self.height + self.width)

        return 1

    @property
    def height_rate(self):
        if self.width > 0 and self.height > 0:
            return 1.0 * self.height / (self.height + self.width)

        return 1

    @property
    def height(self):
        if 'image' in self.ct and self.size:
            return self.size[1]

        return 0

    def remove_file(self):
        if os.path.isfile(self.path):
            try:
                os.remove(self.path)
            except:
                pass

    def delete_file(self):
        self.remove_file()

    def destroy(self, safe=True):
        self.delete_file()
        super(Upload, self).destroy(safe=safe)
