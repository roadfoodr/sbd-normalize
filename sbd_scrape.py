# -*- coding: utf-8 -*-
"""
Created on Thu Oct  6 13:48:40 2022

@author: MDP
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from collections import namedtuple
from thefuzz import fuzz
from thefuzz import process

YEAR = 2022
WEEK_NUM = 5
WEEK_URL = 'https://fantasyindex.com/2022/10/04/podcast/october-4-episode-of-the-fantasy-index-podcast'

# permutations needed for week 5 only
import itertools
choice_perms = itertools.permutations(
    ("Davante Adams", "Ja'Marr Chase", "Tee Higgins"))
choice4 = tuple(', '.join(perm) for perm in choice_perms)

WEEK_CHOICES = [('Jared Goff', 'Zach Wilson'),
                ('Najee Harris', 'Devin Singletary'),
                ('Mark Andrews', 'Travis Kelce'),
                choice4]

# %% Obtain page and convert to BeautifulSoup object
# Note: we are directly scraping input to a js function rather than the rendered html itself

page = requests.get(f'{WEEK_URL}/comments.js')

# need to do some pre-processing to make the js input parameter look more like html
# more robust possibility: python js intrepreter
pagetext = page.text
pagetext = pagetext.replace("$('#comments').html(", '')
pagetext = pagetext.replace('"    ', '')
pagetext = pagetext.replace('jQuery.localtime.localisePage();', '')
pagetext = pagetext.replace(r'a>  ");','a>')
pagetext = pagetext.replace(r'\n', ' ')
pagetext = pagetext.replace('\\', '')  # need the double backslash to escape the actual backslash

soup = BeautifulSoup(pagetext, features='lxml')


# %% Extract desired elements
tagdict = {'id': ('li', lambda tag: tag['id']),
           'name': ('strong', lambda tag: tag.text),
           # https://regex101.com/r/ZxmxR9/1
           'location': ('h3', 
                        lambda tag: re.search(r'\((.*?)\)', tag.text).group(1)),
           'submission': ('p', lambda tag: tag.text),
           'time': ('h5', lambda tag: tag.text),
           }

df = pd.DataFrame(columns=tagdict.keys())

Tagspec = namedtuple("Tagspec", "tag tagfunc")
for key, vals in tagdict.items():
    tagspec = Tagspec(*vals)
    df[key] = pd.Series(map(tagspec.tagfunc, 
                            soup.find_all(tagspec.tag)))

# %% Populate dataframe with matched choices
# https://stackoverflow.com/questions/17740833/checking-fuzzy-approximate-substring-existing-in-a-longer-string-in-python
# TODO: identify when there is a tie score among top matches
match_threshold = 51

for i, choices in enumerate(WEEK_CHOICES):
    choice_results = []
    ordered = []
    for submission in df['submission']:
        # NOTE: if the choices are strings representing an ordered list, then
        # scorer=fuzz.partial_ratio performs better.  Else the default
        # scorer=fuzz.WRatio is best.
        ordered_choice = any(',' in choice for choice in choices)
        # ordered.append(ordered_choice)
        res = process.extractOne(submission, 
                                 choices, 
                                 score_cutoff=match_threshold, 
                                 scorer=fuzz.partial_ratio if ordered_choice else fuzz.WRatio,
                                 )
        choice_results.append(res)
    df[f'pick_{i+1}'] = pd.Series(result[0] if result else None for result in choice_results)
    df[f'match_{i+1}'] = pd.Series(result[1] if result else None for result in choice_results)


# %% enumerate possible choice combos and add combo id to df
combos = itertools.product(*WEEK_CHOICES)
combo_dict = {combo:i+1 for i, combo in enumerate(combos)}

df['combo'] = pd.Series(
    zip(*[df[f'pick_{i}'] for i in range(1, len(WEEK_CHOICES)+1)]))

df['combo_id'] = df['combo'].map(combo_dict)

df_combo = pd.DataFrame.from_dict(combo_dict, orient='index',
                                  columns=['combo_id']).reset_index()
df_combo.columns = ['combo', 'combo_id']
df_combo = df_combo[['combo_id', 'combo']]

# %% Export to spreadsheet

export_cols = (['id', 'name', 'location']
               + [f'pick_{i}' for i in range(1, len(WEEK_CHOICES)+1)]
               + ['combo_id', 'submission', 'time'])

# https://stackoverflow.com/questions/17326973/is-there-a-way-to-auto-adjust-excel-column-widths-with-pandas-excelwriter
writer = pd.ExcelWriter(f'sbd_w{WEEK_NUM}_{YEAR}.xlsx')

df_export = df[export_cols].copy()
df_export.sort_values(by='combo_id', inplace=True)

df_export.to_excel(writer, sheet_name='submissions', index=False, na_rep='')
for column in df_export:
    column_length = max(df_export[column].astype(str).map(len).max(), len(column))
    col_idx = df_export.columns.get_loc(column)
    writer.sheets['submissions'].set_column(col_idx, col_idx, column_length)

df_combo.to_excel(writer, sheet_name='combos', index=False, na_rep='')
for column in df_combo:
    column_length = max(df_combo[column].astype(str).map(len).max(), len(column))
    col_idx = df_combo.columns.get_loc(column)
    writer.sheets['combos'].set_column(col_idx, col_idx, column_length)

writer.save()
