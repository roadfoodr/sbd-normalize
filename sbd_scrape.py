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

PAGE_URL = 'https://fantasyindex.com/2022/10/04/podcast/october-4-episode-of-the-fantasy-index-podcast'


# %% Obtain page and convert to BeautifulSoup object
# Note: we are directly scraping input to a js function rather than the rendered html itself

page = requests.get(f'{PAGE_URL}/comments.js')

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
    
    



