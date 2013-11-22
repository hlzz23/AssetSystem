#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import unicode_literals

table_style = '''border: 1px solid #DDD;
border-left: 0;
border-collapse: separate;
-webkit-border-radius: 4px;
-moz-border-radius: 4px;
border-radius: 4px;
width: 100%;
margin-bottom: 18px;
max-width: 100%;
border-collapse: collapse;
border-spacing: 0;
background-color: transparent;
display: table;
'''

thead_style = '''display: table-header-group;
vertical-align: middle;
border-color: inherit;
'''

tr_style = '''display: table-row;
vertical-align: inherit;
border-color: #DDD;
'''

td_style = '''border-left: 1px solid #DDD;
display: table-cell;
padding: 8px;
line-height: 18px;
text-align: left;
vertical-align: top;
border-top: 1px solid #DDD;
'''

header = '''<h2>{header}</h2>
<h3>Department: {department}</h3>
<h3>Project: {project}</h3>
'''

table_header = '''
<table style="{table_style}">
  <thead style="{thead_style}">
    <tr align="center" style="{tr_style}">
      <th style="{td_style}">#</th>
      <th style="{td_style}">Code</th>
      <th style="{td_style}">Name</th>
      <th style="{td_style}">Min QTY</th>
      <th style="{td_style}">Max QTY</th>
      <th style="{td_style}">Store Good QTY</th>
      <th style="{td_style}">Store Bad QTY</th>
      <th style="{td_style}">Out Good QTY</th>
      <th style="{td_style}">Out Bad QTY</th>
    </tr>
  </thead>
  <tbody style="display: table-row-group;
  vertical-align: middle;
  border-color: inherit;">
'''

td = '''<td style="{td_style}">{data}</td>'''

footer = '''
  </tbody>
</table>
'''
