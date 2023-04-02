# -*- coding: utf-8 -*-
"""
Created on Fri Mar 31 01:37:39 2023

@author: MDP
"""

import pandas as pd
from pathlib import Path


DATA_DIR = '../data/'

# %% identify files to be tidied

p = Path(DATA_DIR)

filenames = [fn for fn in p.glob('*_corrected.xlsx')]
# print(filenames)

# %% construct and concatenate tidy dataframes from each file

df_choices_all = pd.DataFrame()
df_entries_all = pd.DataFrame()

# for fn in filenames[0:1]:
for fn in filenames:
    print(fn)
    df_info = pd.read_excel(fn, sheet_name='weekly info')
    df_info.set_index('attribute', inplace=True)

    df_entries = pd.read_excel(fn, sheet_name='submissions')
    df_entries['year'] = df_info.loc['Year', 'value']
    df_entries['week'] = df_info.loc['Week', 'value']
    
    pick_cols = [col for col in df_entries.columns if 'pick' in col]
    # Only include complete entries (rows with missing picks are likely to be commentary)
    df_entries = df_entries.dropna(subset=pick_cols)
    df_entries = df_entries[df_entries['name'] != 'Justin Eleff']
    df_entries.rename(columns={'id': 'comment_id'}, inplace=True)
    #TODO: de-dupe?

    entries_id_cols = ['year', 'week', 'comment_id', 'name', 'location', 'combo_id']
    entry_cols = entries_id_cols + pick_cols
    df_entries = df_entries[entry_cols]
    df_entries_tidy = pd.melt(df_entries, 
                              id_vars=entries_id_cols, 
                              var_name='pick_num', value_name='pick')
    df_entries_tidy.sort_values(by=['combo_id', 'comment_id', 'pick_num'],
                                inplace=True)
    df_entries_tidy.dropna(subset='pick', inplace=True)
    df_entries_all = pd.concat([df_entries_all, df_entries_tidy], 
                           axis='index', ignore_index=True)

    df_choices = pd.read_excel(fn, sheet_name='weekly choices')
    df_choices['year'] = df_info.loc['Year', 'value']
    df_choices['week'] = df_info.loc['Week', 'value']

    choice_cols = [col for col in df_choices.columns if 'choice' in col]
    df_choices.reset_index(inplace=True)
    df_choices.rename(columns={'index': 'choice_idx'}, inplace=True)
    # convert choice index ids from 0-based to 1-based
    df_choices['choice_idx'] = df_choices['choice_idx'] + 1
    choice_id_cols = ['year', 'week', 'choice_idx']
    df_choices = df_choices[choice_id_cols + choice_cols]
    df_choices_tidy = pd.melt(df_choices, 
                              id_vars=choice_id_cols, 
                              var_name='choice_num', value_name='choice')
    df_choices_tidy = df_choices_tidy[['year', 'week', 'choice_num', 
                                       'choice_idx', 'choice']]
    df_choices_tidy.dropna(subset='choice', inplace=True)
    df_choices_all = pd.concat([df_choices_all, df_choices_tidy], 
                           axis='index', ignore_index=True)

# TODO: include weekly number of possible combos in choices_all?
# TODO: include weekly URL in dfs?

