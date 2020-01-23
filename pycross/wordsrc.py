# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

from utils.globalvars import *

import re, csv, numpy as np, itertools
# ******************************************************************************** #

class Wordsource:
    
    def __init__(self, max_fetch=None, shuffle=True):
        """
        * max_fetch (int): maximum number of suggestions returned from the word source
            (None means no limit on suggestions, which may be time/resource consuming!)
        * shuffle (bool): if True, fetched words will be shuffled
        """
        self.max_fetch = max_fetch
        self.shuffle_words = shuffle
        self.active = True
        
    def isvalid(self):
        return True
        
    def truncate(self, suggestions):
        if not self.max_fetch: return suggestions
        return suggestions[:self.max_fetch] if suggestions else []
        
    def shuffle(self, suggestions):
        if not suggestions: return []
        if self.shuffle_words:
            np.random.seed()
            np.random.shuffle(suggestions)
        return suggestions
    
    def fetch(self, word=None, blank=' ', pos=None, filter_func=None, shuffle=True, truncate=True):
        if not self.isvalid() or not self.active: return []
        return []
    
    def check(self, word, pos=None, filter_func=None):
        if not self.isvalid() or not self.active: return True
        return bool(self.fetch(word, pos=pos, filter_func=filter_func, shuffle=False, truncate=False))
    
    def pop_word(self, suggestions):
        return suggestions.pop() if suggestions else None
    
    def __repr__(self):
        return f"{type(self)} object :: max_fetch = {self.max_fetch}"
    
    def __bool__(self):
        return self.isvalid()

# ******************************************************************************** #

class DBWordsource(Wordsource):
    
    def __init__(self, tables, db, diconnect_on_destroy=True, max_fetch=None, shuffle=True):
        self.db = db
        if not self.db.connect():
            raise Exception(_('Cannot connect to db!'))
        self.conn = self.db.conn or None
        self.tables = tables
        self.diconnect_on_destroy = diconnect_on_destroy
        self.cur = None
        super().__init__(max_fetch, shuffle)
        
    def __del__(self):
        if self.diconnect_on_destroy and self.conn:
            try:
                self.conn.close()
            except:
                pass
            
    def isvalid(self):
        return not self.conn is None
            
    def _execsql(self, sql):
        if self.cur: self.cur.close()   
        if not self.conn:
            if not self.db.connect():
                raise Exception(_('Cannot connect to db!'))
            self.conn = self.db.conn or None
        self.cur = self.conn.cursor()
        self.cur.execute(sql)
        return self.cur
    
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
            
        cur = self._execsql(sql)
        results = []
        if not cur: return []
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
        
class TextWordsource(Wordsource):
    
    def __init__(self, words=[], max_fetch=None, shuffle=True):
        self.bpos = words and isinstance(words[0], tuple) and len(words[0]) == 2
        if words:
            self.words = [(w.lower(), list(p)) for (w, p) in words] if self.bpos else [(w.lower(), None) for w in words]
        else:
            self.words = []
        super().__init__(max_fetch, shuffle)
        
    def isvalid(self):
        return bool(self.words)
            
    def fetch(self, word=None, blank=' ', pos=None, filter_func=None, shuffle=True, truncate=True):
        if not self.isvalid() or not self.active: return []
        results = []
        regex_w = None if word is None else re.compile(word.lower().replace(blank, r'\w'))
        if pos: pos = list(pos)
        for w in self.words:
            matched = bool(regex_w.fullmatch(w[0])) if regex_w else True
            if filter_func: matched = matched and filter_func(w[0])
            if not matched: continue            
            if self.bpos and pos:
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

class TextfileWordsource(TextWordsource):

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
        
class MultiWordsource(Wordsource):
    
    def __init__(self, order='prefer-last', max_fetch=None):
        self.order = order
        self.sources = []
        # leave default value of 'shuffle', it's not used here
        super().__init__(max_fetch)
        
    def isvalid(self):
        return any((bool(src) for src in self.sources))
        
    def add(self, source, position=None):
        if position is None:
            if self.order == 'prefer-last':
                self.sources.append(source)
            else:
                self.sources.insert(0, source)
        else:
            self.sources.insert(position, source)
            
    def clear(self):
        self.sources.clear()
        
    def remove(self, index):
        self.sources.remove(index)
        
    def pop_word(self, suggestions):
        if not suggestions: return None
        return suggestions.pop(-1 if self.order == 'prefer-last' else 0)
    
    def truncate(self, suggestions):
        if not suggestions: return []
        if not self.max_fetch: return suggestions
        return suggestions[:self.max_fetch]
        
    def fetch(self, word=None, blank=' ', pos=None, filter_func=None, shuffle=True, truncate=True):
        if not self.isvalid(): return []
        sources = self.sources if self.order == 'prefer-first' else reversed(self.sources)
        suggestions = list(dict.fromkeys(itertools.chain.from_iterable((src.fetch(word, blank, pos, filter_func, shuffle, False) for src in sources))))
        return self.truncate(suggestions) if suggestions and truncate else suggestions
    
    def check(self, word, pos=None, filter_func=None):
        if not self.isvalid(): return False
        return any((src.check(word, pos, filter_func) for src in self.sources))
    
    def __len__(self):
        return len(self.sources)

    def __bool__(self):
        return len(self.sources) > 0