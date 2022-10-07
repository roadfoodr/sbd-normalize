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


# %%

# https://stackoverflow.com/questions/17740833/checking-fuzzy-approximate-substring-existing-in-a-longer-string-in-python
from thefuzz import fuzz
from thefuzz import process

ls = df.iloc[16]['submission']
# qs = WEEK_CHOICES[3][0]
# qs2 = WEEK_CHOICES[3][2]
threshold = 1

# results = process.extractBests(qs, (ls,), score_cutoff=threshold, scorer=fuzz.partial_ratio)
# results2 = process.extractBests(qs2, (ls,), score_cutoff=threshold, scorer=fuzz.partial_ratio)

# print(qs, results[0][1])
# print(qs2, results2[0][1])

choices = WEEK_CHOICES[3]
# NOTE: if the choices are strings representing an ordered list, then
# scorer=fuzz.partial_ratio performs better.  Else the default
# scorer=fuzz.WRatio is best.
# ordered_choice = any(',' in choice for choice in choices)

for qs in choices:
    ordered_choice = (',' in qs)
    res = process.extractOne(qs, 
                             (ls,), 
                             score_cutoff=threshold, 
                             scorer=fuzz.partial_ratio if ordered_choice else fuzz.WRatio,
                             )
    print(qs, res[1])
print('====')

res2 = process.extractOne(ls, 
                          choices, 
                          score_cutoff=threshold, 
                          scorer=fuzz.partial_ratio if ordered_choice else fuzz.WRatio,
                          )
print(res2)

