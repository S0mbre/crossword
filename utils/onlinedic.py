# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 14:56:06 2019

@author: iskander.shafikov
"""

import requests
import urllib.parse
from abc import ABC, abstractmethod
from .globalvars import (MW_DIC_KEY, MW_DIC_HTTP, MW_WORD_URL, YAN_DICT_KEY, YAN_DICT_HTTP)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class OnlineDictionary(ABC):

    def __init__(self, settings, url_template='', timeout=5000):
        self.url = url_template
        self.timeout = timeout
        self.settings = settings

    def prepare_request_url(self, word):
        return self.url.format(word)

    def get_definitions(self, word, method='json'):
        """
        Returns full definitions for 'word' in JSON (python object) or raw text format.
        """
        res = requests.get(self.prepare_request_url(word), timeout=self.timeout)
        if res:
            return res.json() if method == 'json' else res.content
        else:
            raise Exception(f"Request returned error {res.status_code}")

    @abstractmethod
    def get_short_defs(self, word, exact_match=True, partsofspeech=None, bad_pos='UNKNOWN'):
        """
        Returns the abridged definition for the given entry.
        Params:
        - word [str]: the word query
        - exact_match [bool]: if True, only defitions for the exact word given by 'word' will be returned
        - partsofspeech [list or tuple]: parts of speech to get definitions for
        (None = all available)
        - bad_pos [str]: substitution for part of speech if unavailable        
        Returns:
        - list of short definitions in the format:
        [('word', 'part of speech', [list of defs], 'url'), ...]
        """
        return []

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class MWDict(OnlineDictionary):

    def __init__(self, settings, timeout=5000):
        super().__init__(settings, MW_DIC_HTTP, timeout)

    def prepare_request_url(self, word):
        return self.url.format(word, self.settings['lookup']['dics']['mw_apikey'] or MW_DIC_KEY)

    def get_short_defs(self, word, exact_match=True, partsofspeech=None, bad_pos='UNKNOWN'):
        entry = self.get_definitions(word)
        if not entry or not isinstance(entry, list): return None
        results = []
        for hom in entry:
            if not isinstance(hom, dict): continue
            wd = hom.get('hwi', None)            
            if not wd or not isinstance(wd, dict): continue
            wd = wd.get('hw', None)
            if not wd: continue
            wd = wd.replace('*', '')
            if exact_match and wd.lower() != word.lower(): continue
            pos = hom.get('fl', bad_pos)            
            if (not partsofspeech) or (pos in partsofspeech):
                defs = hom.get('shortdef', None)
                results.append((wd, pos, defs, MW_WORD_URL.format(urllib.parse.quote_plus(wd))))
        return results

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class YandexDict(OnlineDictionary):

    def __init__(self, settings, lang='ru-ru', timeout=5000):
        self.lang = lang
        super().__init__(settings, YAN_DICT_HTTP, timeout)

    def prepare_request_url(self, word):
        return self.url.format(self.settings['lookup']['dics']['yandex_key'] or YAN_DICT_KEY, 
                                word, self.lang)

    def get_short_defs(self, word, exact_match=True, partsofspeech=None, bad_pos='UNKNOWN'):
        entry = self.get_definitions(word)
        if not entry or not isinstance(entry, dict): return None
        defs = entry.get('def', [])
        results = []
        for hom in defs:
            try:
                wd = hom['text']
                if exact_match and wd.lower() != word.lower(): continue
                pos = hom.get('pos', bad_pos)
                if (not partsofspeech) or (pos in partsofspeech):
                    wdefs = []
                    for tr in hom['tr']:
                        wdefs.append(tr['text'])
                        syns = tr.get('syn', [])
                        for syn in syns:
                            wdefs.append(syn['text'])                
                    results.append((wd, pos, wdefs, ''))
            except Exception as err: 
                print(err)
                continue
        return results
