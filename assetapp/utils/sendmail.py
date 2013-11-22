#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import os
from turbomail.control import interface
from turbomail import Message

from flask import request, render_template

cmd = """/sbin/ifconfig eth0 |awk '/inet/ {split($2,x,":");print x[2]}'"""
ip = os.popen(cmd).read().strip()
sender_address = (('FMC EngAsset', 'FMCEngAsset@cn.flextronics.com'))
email_config = {
    'mail.on': True,
    'mail.transport': "smtp",
    'mail.smtp.server': '10.201.13.88',
    'mail.manager': 'demand',
    'mail.message.encoding': "utf-8",
    'mail.smtp.debug': False,
}


def send_mail(subject='',
              to=[],
              cc=[],
              bcc=[],
              template='',
              lang='zh',
              values={},
              ip=ip,
              ):
    interface.start(email_config)
    msg = Message(sender_address,
                  to,
                  subject,
                  cc=cc,
                  bcc=bcc,
                  plain=subject if template else 'Plain Text',
                  )

    if template:
        try:
            url_root = request.url_root
        except:
            url_root = 'http://{}'.format(ip)

        if 'http://localhost' in url_root:
            url_root = 'http://{}'.format(ip)

        msg.rich = render_template('notifications/{}'.format(template),
                                   lang=lang,
                                   url_root=url_root,
                                   **values
                                   )
        msg.send()
        interface.stop()
