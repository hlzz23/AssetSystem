#!/usr/bin/env python
#-*- coding: utf-8 -*-

from turbomail.control import interface
from turbomail import Message

from_ = (('Asset Summary', 'Asset.Summary@cn.flextronics.com'))
debug_list = ['Colin.Qi', 'Sucre.Su']
email_config = {'mail.on': True,
                'mail.transport': "smtp",
                'mail.smtp.server': '10.201.13.88',
                'mail.manager': 'demand',
                'mail.message.encoding': "utf-8",
                'mail.smtp.debug': False,
                }


def parse_mail(mail_list):
    mails = []
    for mail in mail_list:
        mails.append((mail.replace('.', ' '), mail + '@cn.flextronics.com'))

    return mails


def send_mail(subject, body, author=None, **kwargs):
    interface.start(email_config)
    msg = Message(author or from_, parse_mail(kwargs.get('to', [])), subject)
    msg.cc = parse_mail(kwargs.get('cc', []))
    bcc = kwargs.get('bcc', [])
    if not bcc:
        if kwargs.get('debug', True):
            bcc = debug_list

    msg.bcc = parse_mail(bcc)
    msg.plain = subject
    msg.rich = body
    [msg.attach(attachment) for attachment in kwargs.get('attachments', [])]
    msg.send()
    interface.stop()
