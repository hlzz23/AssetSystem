#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
import os.path
import re
import tempfile
from datetime import datetime, timedelta

from pyExcelerator import Workbook, Borders, XFStyle, Alignment
from pymongo import Connection

one_hour = timedelta(hours=1)
borders = Borders()
borders.left = 1
borders.right = 1
borders.top = 1
borders.bottom = 1

align = Alignment()
align.horz = Alignment.HORZ_CENTER
align.vert = Alignment.VERT_CENTER

style = XFStyle()
style.borders = borders

# center style
cs = XFStyle()
cs.borders = borders
cs.alignment = align

date_fmt = '%Y-%m-%d'
time_fmt = '{:02d}:00 - {:02d}:00'
st_fmt = '%Y-%m-%d %H:%M:%S'


def get_dept_ids():
    data = dict()
    for dp in depts:
        spec = dict(name=dp)
        data[dp] = [o['_id'] for o in db.departments.find(spec)]

    return data


def write_header(ws):
    ws.write(0, 0, '', cs)
    ws.write(0, 1, '', cs)
    ws.write(0, 2, 'Dept', cs)
    ws.write(1, 0, 'Day', cs)
    ws.write(1, 1, 'Shift', cs)
    ws.write(1, 2, 'Time', cs)

    col = 3
    for dp in depts:
        ws.write_merge(0, 0, col, col + 1, dp, cs)
        ws.write(1, col, 'In', cs)
        ws.write(1, col + 1, 'Out', cs)
        col += 2


def handle_one_day(day, ws, row):
    ws.write_merge(row, row + 23, 0, 0, day.strftime('%d-%b'), cs)
    ws.write_merge(row, row + 11, 1, 1, 'Dayshift', cs)
    ws.write_merge(row + 12, row + 23, 1, 1, 'Nightshift', cs)

    # dayshift begins at 08:00
    st = datetime(day.year, day.month, day.day, 8)
    for i in range(24):
        spec = dict(time={'$gte': st.format('%H:00'),
                          '$lte': st.format('%H:59'),
                          },
                    date=st.strftime(date_fmt),
                    )
        ws.write(row, 2, time_fmt.format(st.hour, st.hour + 1), cs)
        col = 3
        for dp in depts:
            spec.update(department=dp)

            # in-store
            spec.update(is_out=False)
            ws.write(row, col, db.iorecords.find(spec).count(), style)

            # out-store
            spec.update(is_out=True)
            ws.write(row, col + 1, db.iorecords.find(spec).count(), style)

            col += 2

        row += 1
        st += one_hour


if __name__ == '__main__':
    depts = ('EE', 'TE', 'PE')
    conn = Connection('teasset')
    db = conn.flexasset
    # db = conn.engasset
    # dept_ids = get_dept_ids()

    wb = Workbook()
    ws = wb.add_sheet('In-Out Summary')
    write_header(ws)
    today = datetime.today()
    days = 7
    start_day = today - one_hour * 24 * days
    row = 2
    for i in range(days):
        handle_one_day(start_day + i * 24 * one_hour, ws, row)
        row += 24

    conn.disconnect()
    dir_path = tempfile.gettempdir()
    file_name = 'WK{} IOSummary.xls'.format(today.strftime('%W'))
    file_path = os.path.join(dir_path, file_name)
    wb.save(file_path)

    from sendmail import send_mail
    subject = 'Engineering Asset IO Weekly Summary'
    fmt = '%Y-%m-%d 08:00'
    body = '<h1>Time Range:<br /> {} - {}</h1>'
    body = body.format(start_day.strftime(fmt),
                       today.strftime(fmt),
                       )
    kwargs = dict(attachments=[file_path],
                  to=['Lisa.Ramos', 'Elva.Shao'],
                  bcc=['Colin.Qi', 'Sucre.Su'],
                  )
    send_mail(subject, body, **kwargs)
    os.remove(file_path)
