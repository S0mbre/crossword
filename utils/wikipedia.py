# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 14:56:06 2019

@author: iskander.shafikov
"""

import wikipedia

class WikiSearch:

    @staticmethod
    def set_lang(lang='en'):
        try:
            wikipedia.set_lang(lang)
        except:
            wikipedia.set_lang('en')

    @staticmethod
    def get_available_languages():
        return wikipedia.languages()

    @staticmethod
    def get_titles(what, nresults=5):        
        results = wikipedia.search(what, results=nresults, suggestion=True)
        return results[0] or results[1]

    @staticmethod
    def get_summary(title, sentences=0):
        return wikipedia.summary(title, sentences=sentences)

    @staticmethod
    def get_fulltext(title, html=True):
        return wikipedia.page(title).html() if html else wikipedia.page(title).content

    @staticmethod
    def get_page(title):
        try:
            return wikipedia.page(title)
        except:
            return None

    @staticmethod
    def get_url(title):
        return wikipedia.page(title).url

    @staticmethod
    def get_title(title):
        return wikipedia.page(title).title

    @staticmethod
    def get_images(title):
        return wikipedia.page(title).images