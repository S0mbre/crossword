# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 14:56:06 2019

@author: iskander.shafikov
"""

import requests
import urllib.parse
from .globalvars import (GOOGLE_KEY, GOOGLE_CSE, GOOGLE_HTTP, GOOGLE_LANG_LR, 
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
