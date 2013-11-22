#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import datetime
from flask import flash

# translate excel date from int to date
__s_date = datetime.date(1899, 12, 31).toordinal() - 1


def get_date(d):
    if isinstance(d, float):
        d = int(d)
    elif isinstance(d, basestring):
        return d

    d = datetime.date.fromordinal(__s_date + d)
    return d.strftime("%Y-%m-%d")


def get_department(dp):
    return dp.replace('COMPUTING', '').replace('PDG', '').strip().upper()


def check_empty(name, val, row, t, errors):
    if not isinstance(val, basestring):
        val = unicode(val)

    if val.strip():
        return True

    errors.append(t('require_with').format(row=row + 1, name=t(name)))
    return False


def check_unique(model, name, row, spec, t, errors, update=False):
    objs = model.find(spec=spec, limit=2)
    if objs.count == 0:
        return True
    elif objs.count == 1 and update:
        return True

    val = objs.next()[name.split('.')[-1]]
    errors.append(t('exists_with').format(row=row + 1,
                                          val=val,
                                          name=t(name),
                                          )
                  )
    return False


def check_str(name, val, row, t, errors):
    if instance(val, basestring):
        return True

    errors.append(t('require_string').format(row=row + 1,
                                             name=t(name),
                                             val=val,
                                             )
                  )
    return False


# null = True, the value can be empty
def check_int(name, val, row, t, errors, null=True):
    if isinstance(val, float) and val.is_integer():
        return True

    if isinstance(val, basestring):
        if null and not val.strip():
            return True

        try:
            float(val)
            return True
        except:
            pass

    errors.append(t('require_int').format(row=row + 1,
                                          name=t(name),
                                          val=val,
                                          )
                  )
    return False


# null = True, the value can be empty
def check_float(name, val, row, t, errors, null=True):
    if isinstance(val, float):
        return True

    if isinstance(val, basestring):
        if null and not val.strip():
            return True

        try:
            float(val)
            return True
        except:
            pass

    errors.append(t('require_float').format(row=row + 1,
                                            name=t(name),
                                            val=val,
                                            )
                  )
    return False


def show_dup_error(name, val, row, t, lines, errors):
    errors.append(t('dup_with').format(row=row + 1,
                                       name=t(name),
                                       val=val,
                                       lines=lines,
                                       )
                  )


def validate_headers(maps, required_keys):
    for k in required_keys:
        if k not in maps:
            return False

    return True


def check_dup(name, rv, i, pool, t, errors):
    val = rv[name.split('.')[-1]]
    if isinstance(val, (int, float)):
        val = unicode(float(val)).split('.')[0]

    val = val.strip().upper()
    if not val:
        return False, val

    error = False
    if val not in pool:
        pool[val] = []
    else:
        error = True
        lines = [line for line in pool[val]]
        show_dup_error(name, val, i, t, lines, errors)

    pool[val].append(i + 1)
    return error, val
