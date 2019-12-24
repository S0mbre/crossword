# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

import requests
import urllib.parse
from abc import ABC, abstractmethod
from .globalvars import (MW_DIC_KEY, MW_DIC_HTTP, MW_WORD_URL, 
                        YAN_DICT_KEY, YAN_DICT_HTTP,
                        SHAREAHOLIC_KEY, SHAREAHOLIC_HTTP,
                        GOOGLE_KEY, GOOGLE_CSE, GOOGLE_HTTP, GOOGLE_LANG_LR, 
                        GOOGLE_LANG_HL, GOOGLE_COUNTRIES_CR, GOOGLE_COUNTRIES_GL)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class GoogleSearch:

    def __init__(self, settings, search_phrase='', exact_match=False, file_types=None, lang=None,
                 country=None, interface_lang=None, link_site=None, related_site=None, in_site=None, 
                 nresults=-1, safe_search=False, timeout=5000):
        self.settings = settings
        self.init(search_phrase, exact_match, file_types, lang, country, interface_lang, link_site,
                  related_site, in_site, nresults, safe_search, timeout)

    def init(self, search_phrase='', exact_match=False, file_types=None, lang=None,
                 country=None, interface_lang=None, link_site=None, related_site=None, in_site=None, 
                 nresults=-1, safe_search=False, timeout=5000):
        self.search_phrase = search_phrase
        self.exact_match = exact_match
        self.file_types = file_types
        self.lang = lang
        self.country = country
        self.interface_lang = interface_lang
        self.link_site = link_site
        self.related_site = related_site
        self.in_site = in_site
        self.nresults = nresults if nresults < 10 else 10
        self.safe_search = safe_search
        self.timeout = timeout

    def encode_search(self):
        url = GOOGLE_HTTP.format(self.settings['lookup']['google']['api_key'] or GOOGLE_KEY,
                                 self.settings['lookup']['google']['api_cse'] or GOOGLE_CSE,
                                 urllib.parse.quote(self.search_phrase))
        if self.exact_match:
            url += f"&exactTerms={urllib.parse.quote(self.search_phrase)}"
        if self.file_types:
            url += f"&fileType={','.join(self.file_types) if isinstance(self.file_types, list) or isinstance(self.file_types, tuple) else self.file_types}"
        if self.lang:
            url += f"&lr={'|'.join([('lang_' + l.lower()) for l in self.lang]) if isinstance(self.lang, list) or isinstance(self.lang, tuple) else ('lang_' + self.lang.lower())}"
        if self.country:
            url += f"&gl={'|'.join(self.country) if isinstance(self.country, list) or isinstance(self.country, tuple) else self.country}"
        if self.interface_lang:
            url += f"&hl={'|'.join(self.interface_lang) if isinstance(self.interface_lang, list) or isinstance(self.interface_lang, tuple) else self.interface_lang}"
        if self.link_site:
            url += f"&linkSite={self.link_site}"
        if self.related_site:
            url += f"&relatedSite={self.related_site}"
        if self.in_site:
            url += f"&siteSearch={self.in_site}"
        if self.nresults > 0:
            url += f"&num={self.nresults}"
        if self.safe_search:
            url += f"&safe=active"
        return url

    def decode_result(self, txt):
        return urllib.parse.unquote(txt)

    def search(self, method='json'):
        """
        Returns full Google search results for 'self.search_phrase'.
        """
        res = requests.get(self.encode_search(), timeout=self.timeout)
        if res:
            res = res.json() if method == 'json' else res.content
            if isinstance(res, dict) and 'error' in res:
                raise Exception(f"Request returned error '{res.get('message', 'Invalid request')}', code = {res.get('code', 400)}")
            return res
        else:
            raise Exception(f"Request returned error {res.status_code}")

    def search_lite(self):
        """
        Retrieves search results for 'self.search_phrase' as a list in the following format:
        [{'url': 'URL', 'title': 'TITLE', 'summary': 'SNIPPET'}, ...]
        See https://developers.google.com/custom-search/v1/cse/list
        """
        res = self.search()
        if not res: return None
        # if we are here, it means no exceptions have occurred...
        return [{'url': item['link'], 'title': item['title'], 'summary': item['snippet']} for item in res['items']]

    @staticmethod
    def get_interface_languages():
        return GOOGLE_LANG_HL

    @staticmethod
    def get_document_languages():
        return GOOGLE_LANG_LR

    @staticmethod
    def get_document_countries():
        return GOOGLE_COUNTRIES_CR

    @staticmethod
    def get_user_countries():
        return GOOGLE_COUNTRIES_GL
        
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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class Uploader:

    def __init__(self):
        pass        

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class Share:

    def __init__(self, settings, url=SHAREAHOLIC_HTTP, timeout=5000):
        self.settings = settings
        self.url = url
        self.timeout = timeout

    def prepare_request_url(self, *args):
        return self.url.format(SHAREAHOLIC_KEY, *args)

    def share(self, filepath, upload_to='gdrive', social='twitter', 
              title='My new crossword', notes='See my new crossword',
              url_shortener='google', tags=''):
        pass