# -*- coding: utf-8 -*-
"""
Created on Thu Oct  6 13:48:40 2022

@author: MDP
"""

import requests
from bs4 import BeautifulSoup

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
litags = soup.find_all('li')
litags_text = [tag.text for tag in litags]

ids = [tag['id'] for tag in litags]

ptags = soup.find_all('p')
submissions = [tag.text for tag in ptags]

strongtags = soup.find_all('strong')
names = [tag.text for tag in strongtags]

h5tags = soup.find_all('h5')
times = [tag.text for tag in h5tags]
