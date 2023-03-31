# -*- coding: utf-8 -*-
"""
Created on Tue Mar 28 21:04:48 2023

@author: MDP
"""
import pandas as pd
import datetime

import sys
sys.path.append('../')
from sbd_scrape import main as sbd_scrape

DATA_DIR = '../data/'

# %% construct dataframe of URLs to be scraped

df = pd.DataFrame(columns=['year', 'week', 'month', 'day', 'monthname', 
                           'url'])

def add_row(df, year, month, day, week, suffix_flag, zfill_flag):
    month_z = str(month).zfill(2) if zfill_flag else month
    day_z = str(day).zfill(2) if zfill_flag else day
    
    row_df = pd.DataFrame.from_dict({'year': [year], 'month': [month_z], 
                                     'day': [day_z], 'week': [week],
                })
    # https://stackoverflow.com/questions/37625334/convert-month-int-to-month-name-in-pandas
    row_df['monthname'] = pd.to_datetime(row_df['month'], format='%m').dt.strftime('%B')

    suffix_str = '-available-now' if suffix_flag else ''

    url = (f'https://fantasyindex.com/{year}/{month_z}/{day_z}/podcast/'
           f"{row_df.iloc[0]['monthname'].lower()}-{day}"
           f'-episode-of-the-fantasy-index-podcast{suffix_str}')
    row_df['url'] = url

    df = pd.concat([df, row_df], ignore_index=True)
    # TODO: dedupe
    return df

def add_rows(df, start_date, wk_range, suffix_flag=0, zfill_flag=0):
    for offset, wk in enumerate(wk_range):
        next_date = start_date + datetime.timedelta(days=offset*7)
        df = add_row(df, next_date.year, next_date.month, 
                         next_date.day, wk, suffix_flag, zfill_flag)
    return df


# 2020: wks 11 through 16, starting 11/17/20
start_date = datetime.date(2020, 11, 17)
df = add_rows(df, start_date, range(11, 17), suffix_flag=1)

# 2020: wks 17 through 17, starting 12/30/20
start_date = datetime.date(2020, 12, 30)
df = add_rows(df, start_date, range(17, 18), suffix_flag=1)
    
# 2021: wks 1 through 1, starting 9/3/21
start_date = datetime.date(2021, 9, 3)
df = add_rows(df, start_date, range(1, 2), suffix_flag=1)
    
# 2021: wks 2 through 16, starting 9/14/21
start_date = datetime.date(2021, 9, 14)
df = add_rows(df, start_date, range(2, 17), suffix_flag=1)

# 2021: wks 17 through 17, starting 12/29/21
start_date = datetime.date(2021, 12, 29)
df = add_rows(df, start_date, range(17, 18), suffix_flag=1)

# 2021: wks 18 through 18, starting 1/4/22
start_date = datetime.date(2022, 1, 4)
df = add_rows(df, start_date, range(18, 19), suffix_flag=1)

# 2022: wks 1 through 1, starting 9/9/22
start_date = datetime.date(2022, 9, 9)
df = add_rows(df, start_date, range(1, 2), suffix_flag=0, zfill_flag=1)
# special case url
df.loc[(df['year'] == 2022) & (df['week'] == 1), ['url']] = 'https://fantasyindex.com/2022/09/09/podcast/supply-by-demand-is-back-september-9-episode-of-the-fantasy-index-podcast'

# 2022: wks 2 through 17, starting 9/13/22
start_date = datetime.date(2022, 9, 13)
df = add_rows(df, start_date, range(2, 18), suffix_flag=0, zfill_flag=1)


# %% loop and scrape

# TODO: option specifying whether to rewrite existing files
for row_idx in range(len(df)):
    weeknum = df.iloc[row_idx]['week']
    url = df.iloc[row_idx]['url']
    try:
        sbd_scrape(weeknum, url)
    except:
        print(f'Exception: {url=}')
