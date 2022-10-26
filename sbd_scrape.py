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
import itertools
from thefuzz import fuzz
from thefuzz import process
import os.path
import warnings

DATA_DIR = './data/'
# YEAR = 2022
# WEEK_NUM = 5
# WEEK_URL = 'https://fantasyindex.com/2022/10/04/podcast/october-4-episode-of-the-fantasy-index-podcast'
# WEEK_NUM = 6
# WEEK_URL = 'https://fantasyindex.com/2022/10/11/podcast/october-11-episode-of-the-fantasy-index-podcast'
# WEEK_NUM = 7
# WEEK_URL = 'https://fantasyindex.com/2022/10/18/podcast/october-18-episode-of-the-fantasy-index-podcast'
WEEK_NUM = 8
WEEK_URL = 'https://fantasyindex.com/2022/10/25/podcast/october-25-episode-of-the-fantasy-index-podcast'
date_res = re.search(r'https:\/\/fantasyindex\.com\/(\d+)\/(\d+)\/(\d+)\/.*', 
                     WEEK_URL)
if date_res:
    YEAR, MONTH, DAY = date_res.group(1), date_res.group(2), date_res.group(3)
else:
    raise ValueError("Date not found in URL")

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
def extract_paren(tag):
    res = re.search(r'\((.*?)\)', tag.text)
    return res.group(1) if res else ''
    
tagdict = {'id': ('li', lambda tag: tag['id']),
           'name': ('strong', lambda tag: tag.text),
           'location': ('h3', extract_paren),
           'submission': ('p', lambda tag: tag.text),
           'time': ('h5', lambda tag: tag.text),
           }

df = pd.DataFrame(columns=tagdict.keys())

Tagspec = namedtuple("Tagspec", "tag tagfunc")
for key, vals in tagdict.items():
    tagspec = Tagspec(*vals)
    df[key] = pd.Series(map(tagspec.tagfunc, 
                            soup.find_all(tagspec.tag)))

# %% Attempt to extract weekly choices from existing spreadsheet or first comment
def extract_parens(tag):
    res = re.findall(r'\((.*?)\)', tag)
    return tuple(res)

def extract_choices_from_comments(df):
    choicecomment = df[(df['name'] == 'Justin Eleff')
                          & (df['submission'].str.lower().str.replace(
                              ' ','').str.contains('-or-'))].iloc[0]['submission']
    choicecomment = choicecomment.replace('- OR -', '-or-')
    choicecomment = choicecomment.replace('- or -', '-or-')
    choicecomment = choicecomment.replace('-OR-', '-or-')
    choicecomment = choicecomment.split(':')[-1]
    choicecomment = choicecomment.replace(' and ', '').strip()
    choicerows = choicecomment.split(';')
    
    week_hosts = [extract_parens(row) for row in choicerows]

    # https://regex101.com/r/8efiNw/1
    choicerows = [re.sub(r'\([^)]*\)', '', row).strip() for row in choicerows]
    choicerows = [row.split('-or-') for row in choicerows]
    
    # choices that do not involve exactly two options will have to be built manually
    week_choices = [(row[0].strip(), row[1].strip()) for row in choicerows 
                    if (len(row) == 2) ]
    
    if len(week_choices) < len (choicerows):
        warnings.warn("Some choices were unable to be parsed and must be built manually.")

    return week_choices, week_hosts

def extract_choices_from_spreadsheet(filename):
    df_choice_from_sheet = pd.read_excel(filename, sheet_name='weekly choices')
    df_choice_from_sheet.fillna(value='', inplace=True)
    week_choices = [tuple(df_choice_from_sheet[colname])
                    for colname in df_choice_from_sheet.columns
                    if 'choice' in colname]
    week_hosts = [tuple(df_choice_from_sheet[colname])
                    for colname in df_choice_from_sheet.columns
                    if 'host' in colname]
    return week_choices, week_hosts

choice_filename = f'{DATA_DIR}sbd_w{WEEK_NUM}_{YEAR}_choices.xlsx'
WEEK_CHOICES, week_hosts = (extract_choices_from_spreadsheet(choice_filename)
                            if os.path.isfile(choice_filename)
                            else extract_choices_from_comments(df))
# clean these up
def row_cleanup(row):
    return tuple(item.strip() for item in row if item)
    
WEEK_CHOICES = [row_cleanup(choicerow) for choicerow in WEEK_CHOICES]
week_hosts = [row_cleanup(hostrow) for hostrow in week_hosts]

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
    df_choices = pd.concat([df_choices, pd.DataFrame(
        {f'host_{i+1}': week_hosts[i]})], axis=1)

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
    ['Week', str(WEEK_NUM)], ['Year', YEAR], ['Month', MONTH], ['Day', DAY], 
    ['URL', WEEK_URL]], 
    columns=['attribute','value'])

# %% Export to spreadsheet
export_cols = (['id', 'name', 'location']
               + [f'pick_{i}' for i in range(1, len(WEEK_CHOICES)+1)]
               + ['combo_id', 'submission', 'time'])

df_export = df[export_cols].copy()
df_export.sort_values(by='combo_id', inplace=True)

# https://stackoverflow.com/questions/17326973/is-there-a-way-to-auto-adjust-excel-column-widths-with-pandas-excelwriter
def export_df_to_sheet(writer, df, sheet_name, include_index=False):
    df.to_excel(writer, sheet_name=sheet_name, index=include_index, na_rep='')
    for column in df:
        column_length = max(df[column].astype(str).map(len).max(), len(column))
        col_idx = df.columns.get_loc(column)
        writer.sheets[sheet_name].set_column(col_idx, col_idx, column_length)

with pd.ExcelWriter(f'{DATA_DIR}sbd_w{WEEK_NUM}_{YEAR}.xlsx') as writer:
    export_df_to_sheet(writer, df_export, sheet_name='submissions')
    export_df_to_sheet(writer, df_choices, sheet_name='weekly choices')
    export_df_to_sheet(writer, df_combo, sheet_name='combos')
    export_df_to_sheet(writer, df_weeklyinfo, sheet_name='weekly info')

