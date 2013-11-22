#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import sys
sys.path.insert(0, '..')

from assetapp import create_app
create_app()

from assetapp.models.user import User
user = User.find_one(spec=dict(login='root'))
if user is not None:
    print(user)
    print(user.dict)
    print('root account already exists!')
    sys.exit(0)


def get_input(name, required=True, trim_blank=True):
    if required:
        s = 'Please enter [{0}(*)]: '.format(name)
    else:
        s = 'Please enter [{0}]: '.format(name)

    while True:
        v = raw_input(s)
        if trim_blank is True:
            v = v.strip()

        if v or not required:
            return v

print('Creating webmaster ("*" mark is required)...')
print('=' * 50)
print('Login Name: {}'.format('root'))
print('Nick Name: {}'.format('root'))
print('Badge ID: {}'.format(10000))
password = get_input('Password', trim_blank=False)
user = User(login='root',
            badge_id='10000',
            nick_name='root',
            password=password,
            email=get_input('Email', required=False),
            phone=get_input('Office EXT.', required=False),
            gsm=get_input('Mobile Phone', required=False),
            short_no=get_input('Short NO.', required=False),
            )

print('\nSave to database...')
user.save()
# print(user._errors)
print('=' * 50)
print("The root password is {!r}, please keep it safe.".format(password))
