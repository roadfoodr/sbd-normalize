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

# https://regex101.com/r/ZxmxR9/1
def extract_parens(tag):
    res = re.search(r'\((.*?)\)', tag.text)
    return res.group(1) if res else ''
    
tagdict = {'id': ('li', lambda tag: tag['id']),
           'name': ('strong', lambda tag: tag.text),
           'location': ('h3', extract_parens),
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
    for submission in df['submission']:
        # NOTE: if the choices are strings representing an ordered list, then
        # scorer=fuzz.partial_ratio performs better.  Else the default
        # scorer=fuzz.WRatio is best.
        ordered_choice = any(',' in choice for choice in choices)
        res = process.extractOne(submission, 
                                 choices, 
                                 score_cutoff=match_threshold, 
                                 scorer=fuzz.partial_ratio if ordered_choice else fuzz.WRatio,
                                 )
        choice_results.append(res)
    df[f'pick_{i+1}'] = pd.Series(result[0] if result else None for result in choice_results)
    df[f'match_{i+1}'] = pd.Series(result[1] if result else None for result in choice_results)


# %% construct dataframe with choice options
df_choices = pd.DataFrame()
for i, choices in enumerate(WEEK_CHOICES):
    df_choices = pd.concat([df_choices, pd.DataFrame(
        {f'choice_{i+1}': choices})], axis=1)

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

combo_choice_cols = [f'choice_{i}' for i in range(1, len(WEEK_CHOICES)+1)]
df_combo[combo_choice_cols] = pd.DataFrame(df_combo['combo'].tolist(), 
                                           index= df_combo.index)

# %% construct weekly info df for export to spreadsheet
df_weeklyinfo = pd.DataFrame([
    ['Week', WEEK_NUM], ['Year', YEAR], ['URL', WEEK_URL]], 
    columns=['attribute','value'])

# %% Export to spreadsheet
export_cols = (['id', 'name', 'location']
               + [f'pick_{i}' for i in range(1, len(WEEK_CHOICES)+1)]
               + ['combo_id', 'submission', 'time'])

df_export = df[export_cols].copy()
df_export.sort_values(by='combo_id', inplace=True)

writer = pd.ExcelWriter(f'sbd_w{WEEK_NUM}_{YEAR}.xlsx')

# https://stackoverflow.com/questions/17326973/is-there-a-way-to-auto-adjust-excel-column-widths-with-pandas-excelwriter
def export_df_to_sheet(writer, df, sheet_name, include_index=False):
    df.to_excel(writer, sheet_name=sheet_name, index=include_index, na_rep='')
    for column in df:
        column_length = max(df[column].astype(str).map(len).max(), len(column))
        col_idx = df.columns.get_loc(column)
        writer.sheets[sheet_name].set_column(col_idx, col_idx, column_length)

export_df_to_sheet(writer, df_export, sheet_name='submissions')
export_df_to_sheet(writer, df_choices, sheet_name='weekly choices')
export_df_to_sheet(writer, df_combo, sheet_name='combos')
export_df_to_sheet(writer, df_weeklyinfo, sheet_name='weekly info')

writer.save()
