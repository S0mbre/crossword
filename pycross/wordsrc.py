# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package pycross.wordsrc
# Implements the Wordsource base class and its derivatives -- various sources of words
# for generating crosswords. These sources include:
#   * DBWordsource - SQLite database source
#   * TextWordsource - string-based source
#   * TextfileWordsource - file-based source
#   * MultiWordsource - combined word source container that can store any number of individual sources
from utils.globalvars import *
import re, csv, numpy as np, itertools
# ******************************************************************************** #

## Base class for word source objects. Provides core methods for fetching, shuffling,
# truncating the results and other bare-bones stuff.
class Wordsource:
    
    ## Constructor.
    # @param max_fetch `int` maximum number of suggestions returned from the word source
    # (None means no limit on suggestions, which may be time/resource consuming!)
    # @param shuffle `bool` if `True`, fetched words will be shuffled
    def __init__(self, max_fetch=None, shuffle=True):
        ## `int` maximum number of suggestions returned from the word source
        self.max_fetch = max_fetch
        ## `bool` if `True`, fetched words will be shuffled
        self.shuffle_words = shuffle
        ## `bool` if `True`, this word source will be used; otherwise it will be ignored
        self.active = True
        
    ## Checks if it is a valid word source
    # @returns `bool` `True` if valid, `False` if not valid
    def isvalid(self):
        return True
        
    ## Truncates the results by the threshold number stored in Wordsource::max_fetch.
    # @param suggestions `list` list of suggested words `str`
    # @returns `list` truncated list of suggested words 
    # or the original list if Wordsource::max_fetch is `None`
    def truncate(self, suggestions):
        if not self.max_fetch: return suggestions
        return suggestions[:self.max_fetch] if suggestions else []
        
    ## Shuffles the results randomly.
    # @param suggestions `list` list of suggested words `str`
    # @returns `list` randomly shuffled list of suggested words 
    # or the original list if Wordsource::shuffle_words == `False`
    def shuffle(self, suggestions):
        if not suggestions: return []
        if self.shuffle_words:
            np.random.seed()
            np.random.shuffle(suggestions)
        return suggestions
    
    ## Fetches suggestions (as a `list` of strings) for a given word pattern (mask).
    # @param word `str` | `None` the word pattern to find suggestions for, e.g. 'f th  '
    # @param blank `str` placeholder character for unknown (blank) letters (default = whitespace)
    # @param pos `str` | `iterable` | `None` part(s) of speech to include in the results:
    #   * `str` a single part of speech, e.g. 'N' (nouns) or 'V' (verbs)
    #   * `iterable` a collection of parts of speech, e.g. ('N', 'V') = nouns AND verbs
    #   * `None` (default) no part-of-speech filter: all words matching the pattern will be included
    # @param filter_func `callable` filtering callback function to exclude words from results.
    # Prototype is: 
    # @code{.py}
    # filter_func(word: str) -> bool
    # @endcode
    # (returns `True` to include the word).
    # If `None` (default), no filtering will be performed.
    # @param shuffle `bool` `True` (default) to shuffle the results randomly
    # @param truncate `bool` `True` (default) to truncate the results by Wordsource::max_fetch
    # @returns `list` list of strings - the words matching the given pattern
    def fetch(self, word=None, blank=' ', pos=None, filter_func=None, shuffle=True, truncate=True):
        if not self.isvalid() or not self.active: return []
        return []
    
    ## Checks if a given word or word pattern is found in the word source.
    # @param word `str` the word (pattern) to find, e.g. 'f ther' or 'father'
    # @param pos `str` | `iterable` | `None` part(s) of speech to include in the results -
    # see fetch()
    # @param filter_func `callable` filtering callback function to exclude words from results -
    # see fetch()
    # @returns `bool` `True` if the given word (pattern) can be found in the source, `False` otherwise
    def check(self, word, pos=None, filter_func=None):
        if not self.isvalid() or not self.active: return True
        return bool(self.fetch(word, pos=pos, filter_func=filter_func, shuffle=False, truncate=False))
    
    ## Retrieves the last suggestion (word) from the list of suggestions, removing
    # that word from the original results.
    # @returns `str` last word from the suggestions or None if the suggestions list is empty
    def pop_word(self, suggestions):
        return suggestions.pop() if suggestions else None
    
    ## Python `repr()` overload.
    # @returns `str` human-readable representation of Wordsource object
    def __repr__(self):
        return f"{type(self)} object :: max_fetch = {self.max_fetch}"
    
    ## Python `bool()` overload.
    # @returns `bool` the result of isvalid()
    def __bool__(self):
        return self.isvalid()

# ******************************************************************************** #

## SQLite database word source implementation.
class DBWordsource(Wordsource):
    
    ## Constructor.
    # @param tables `dict` DB table and field names for words and parts of speech - 
    # see utils::globalvars::SQL_TABLES (default names)
    # @param db `dbapi::Sqlitedb` SQLite database driver object
    # @param diconnect_on_destroy `bool` `True` (default) to disconnect from database on object destruction
    # @param max_fetch `int` maximum number of suggestions returned from the word source
    # @warning `None` means no limit on suggestions, which may be time/resource consuming!
    # @param shuffle `bool` if `True`, fetched words will be shuffled
    # @exception Exception failed DB connection
    def __init__(self, tables, db, diconnect_on_destroy=True, max_fetch=None, shuffle=True):
        ## `dbapi::Sqlitedb` SQLite database driver object
        self.db = db
        if not self.db.connect():
            raise Exception(_('Cannot connect to db!'))
        ## DB connection object (low-level DB driver)
        self.conn = self.db.conn or None
        ## `dict` DB table and field names for words and parts of speech - 
        # see utils::globalvars::SQL_TABLES (default names)
        self.tables = tables
        ## `bool` `True` (default) to disconnect from database on object destruction
        self.diconnect_on_destroy = diconnect_on_destroy
        ## low-level DB cursor object
        self.cur = None
        super().__init__(max_fetch, shuffle)
        
    ## Destructor: disconnects from database if DBWordsource::diconnect_on_destroy == `True`
    def __del__(self):
        if self.diconnect_on_destroy and self.conn:
            try:
                self.conn.close()
            except:
                pass
            
    ## Valid only if the DB connection was successful.
    def isvalid(self):
        return not self.conn is None
            
    ## Executes an SQL query.
    # @param sql `str` SQL query string
    # @returns `DB cursor` DB cursor object that has executed the SQL query
    # @exception Exception failed DB connection
    def _execsql(self, sql):
        if self.cur: self.cur.close()   
        if not self.conn:
            if not self.db.connect():
                raise Exception(_('Cannot connect to db!'))
            self.conn = self.db.conn or None
        self.cur = self.conn.cursor()
        try:
            self.cur.execute(sql)
            return self.cur
        except:
            return None
    
    ## Fetches results from the current SQLite DB.
    def fetch(self, word=None, blank=' ', pos=None, filter_func=None, shuffle=True, truncate=True):
        if not self.isvalid() or not self.active: return []
        conj = '\nwhere' if word is None else '\nand'    
        sql = f"select {self.tables['words']['table']}.{self.tables['words']['fwords']} from {self.tables['words']['table']}"
        bpos = False
        if pos and 'pos' in self.tables and 'fpos' in self.tables['words'] and 'fid' in self.tables['pos'] and 'fpos' in self.tables['pos']:
            bpos = True
            sql += f"\njoin {self.tables['pos']['table']} on {self.tables['pos']['table']}.{self.tables['pos']['fid']} = {self.tables['words']['table']}.{self.tables['words']['fpos']}"
        if not word is None:
            sql += f"""\nwhere ({self.tables['words']['table']}.{self.tables['words']['fwords']} like '{word.lower().replace(blank, "_")}')"""
        if bpos:
            pos_conj = f"in ({repr(pos)[1:-1]})" if (isinstance(pos, list) or isinstance(pos, tuple)) else f"= {repr(pos)}"
            sql += f"{conj} {self.tables['pos']['table']}.{self.tables['pos']['fpos']} {pos_conj}"
            
        cur = None
        try:
            cur = self._execsql(sql)
        except:
            return []
        if not cur: return []
        results = []
        for row in cur:
            r = row[0]
            if filter_func:
                if filter_func(r):
                    results.append(r)
            else:
                results.append(r)
        cur.close()
        if shuffle: results = self.shuffle(results)
        return self.truncate(results) if truncate else results

# ******************************************************************************** #
        
## Word source based on a simple list of strings (stored in memory).
class TextWordsource(Wordsource):
    
    ## Constructor.
    # @param words `list` list of source words, each of which is EITHER:
    #   * `str` a single string, e.g. 'father'; OR
    #   * `2-tuple` a tuple with 2 elements:
    #       ** `str` word string
    #       ** `iterable` parts of speech that word belongs to, e.g. ['N', 'V'] (noun or verb)
    # @param max_fetch `int` maximum number of suggestions returned from the word source
    # @warning `None` means no limit on suggestions, which may be time/resource consuming!
    # @param shuffle `bool` if `True`, fetched words will be shuffled
    def __init__(self, words=[], max_fetch=None, shuffle=True):
        ## `bool` `True` if the source word list contains part-of-speech data
        self.bpos = words and isinstance(words[0], tuple) and len(words[0]) == 2
        if words:
            ## `list` list of 2-tuples, where the first element is the source word
            # and the second element is either a list of parts of speech or `None` if 
            # no part-of-speech data is available 
            self.words = [(w.lower(), list(p)) for (w, p) in words] if self.bpos else [(w.lower(), None) for w in words]
        else:
            self.words = []
        super().__init__(max_fetch, shuffle)
        
    ## Valid only if TextWordsource::words not empty
    def isvalid(self):
        return bool(self.words)
            
    ## Fetches results from TextWordsource::words
    def fetch(self, word=None, blank=' ', pos=None, filter_func=None, shuffle=True, truncate=True):
        if not self.isvalid() or not self.active: return []
        results = []
        regex_w = None if word is None else re.compile(word.lower().replace(blank, r'\w'))
        if pos: pos = list(pos)
        for w in self.words:
            matched = bool(regex_w.fullmatch(w[0])) if regex_w else True
            if filter_func: matched = matched and filter_func(w[0])
            if not matched: continue            
            if w[1] and self.bpos and pos:
                for p in pos:
                    if p in w[1]:
                        matched = True
                        break
                else:
                    matched = False
            if matched:
                results.append(w[0])
        if shuffle: results = self.shuffle(results)
        return self.truncate(results) if truncate else results

# ******************************************************************************** #

## Word source generated from a text file.
# Derives from TextWordsource, so all members are implemented without change.
class TextfileWordsource(TextWordsource):

    ## Constructor.
    # @param path `str` full path to the source text file
    # @param enc `str` file encoding (default = UTF8)
    # @param delimiter `str` field delimiter character in text file (default = whitespace)
    # @param max_fetch `int` maximum number of suggestions returned from the word source
    # @warning `None` means no limit on suggestions, which may be time/resource consuming!
    # @param shuffle `bool` if `True`, fetched words will be shuffled
    def __init__(self, path, enc='utf-8', delimiter=' ', max_fetch=None, shuffle=True):           
        self.words = []
        self.bpos = False
        with open(path, 'r', encoding=enc, newline='') as fin:
            reader = csv.reader(fin, delimiter=delimiter, quoting=csv.QUOTE_NONE)
            for row in reader:
                self.words.append((row[0], row[1:] if len(row) > 1 else None))
                if len(row) > 1 and not self.bpos: self.bpos = True
        Wordsource.__init__(self, max_fetch, shuffle)
                
# ******************************************************************************** #

## @brief Combined word source that stores other Wordsource-derived objects and provides
# the same interface for fetching the results.
# The individual word sources are treated as one single word source when retrieving /
# truncating and extracting suggested words, but each source can be shuffled individually,
# and toggled 'on' and 'off' using their current Wordsource::active values. 
# Being flexible, this is the default implementation for the crossword word source.
# @see crossword::Crossword::wordsource, gui::MainWindow::wordsrc
class MultiWordsource(Wordsource):
    
    ## Constructor.
    # @param order `str` indicates the preference order for individual word sources and words.
    # Can be one of:
    #   * 'prefer-last' (default) implements the 'last items first' principle:
    # new word sources will be added at the end of the source container, words will be 
    # suggested (extracted) starting from the end of the results list; OR
    #   * 'prefer-first' implements the 'first items first' principle:
    # new word sources will be added at the start of the source container, words will be 
    # suggested (extracted) from the start of the results list
    # @param max_fetch `int` maximum number of suggestions returned from the word source
    # @warning `None` means no limit on suggestions, which may be time/resource consuming!
    def __init__(self, order='prefer-last', max_fetch=None):
        ## `str` the preference order for individual word sources and words
        self.order = order
        ## `list` container for Wordsource objects (word sources)
        self.sources = []
        # leave default value of 'shuffle', it's not used here
        super().__init__(max_fetch)
        
    ## Valid if at least one word source is valid
    def isvalid(self):
        return any((bool(src) for src in self.sources))
        
    ## Adds a new word source to MultiWordsource::sources.
    # @param source `Wordsource` a Wordsource-derived object - a single word source
    # @param position `int` | `None` position index in MultiWordsource::sources to add 
    # the word source to; if `None` (default) the index will depend on the value of MultiWordsource::order
    def add(self, source, position=None):
        if position is None:
            if self.order == 'prefer-last':
                self.sources.append(source)
            else:
                self.sources.insert(0, source)
        else:
            self.sources.insert(position, source)
            
    ## Removes all word sources from MultiWordsource::sources.
    def clear(self):
        self.sources.clear()
        
    ## Removes a single word source from MultiWordsource::sources.
    # @param index `int` the position index of the word source to remove
    def remove(self, index):
        self.sources.remove(index)
        
    def pop_word(self, suggestions):
        if not suggestions: return None
        return suggestions.pop(-1 if self.order == 'prefer-last' else 0)
    
    def truncate(self, suggestions):
        if not suggestions: return []
        if not self.max_fetch: return suggestions
        return suggestions[:self.max_fetch]
        
    ## Fetches results from all the word sources and combines them into one list of words.
    def fetch(self, word=None, blank=' ', pos=None, filter_func=None, shuffle=True, truncate=True):
        if not self.isvalid(): return []
        sources = self.sources if self.order == 'prefer-first' else reversed(self.sources)
        suggestions = list(dict.fromkeys(itertools.chain.from_iterable((src.fetch(word, blank, pos, filter_func, shuffle, False) for src in sources))))
        return self.truncate(suggestions) if suggestions and truncate else suggestions
    
    def check(self, word, pos=None, filter_func=None):
        if not self.isvalid(): return False
        return any((src.check(word, pos, filter_func) for src in self.sources))
    
    ## Python `len()` overload.
    # @returns `int` number of word sources in MultiWordsource::sources
    def __len__(self):
        return len(self.sources)