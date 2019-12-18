# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

from utils.globalvars import *
import sqlite3, os, re, codecs

## ******************************************************************************** ##

SQL_CREATE_TABLES = \
f"create table if not exists {SQL_TABLES['pos']['table']} (\n" \
f"{SQL_TABLES['pos']['fid']} integer primary key autoincrement,\n" \
f"{SQL_TABLES['pos']['fpos']} text not null,\n" \
f"posdesc text default '');\n" \
f"create table if not exists {SQL_TABLES['words']['table']} (\n" \
f"id integer primary key autoincrement,\n" \
f"{SQL_TABLES['words']['fwords']} text not null,\n" \
f"{SQL_TABLES['words']['fpos']} integer,\n" \
f"foreign key ({SQL_TABLES['words']['fpos']}) references {SQL_TABLES['pos']['table']}({SQL_TABLES['pos']['fid']}) on delete set null on update no action);\n" \
f"create unique index word_idx on {SQL_TABLES['words']['table']}({SQL_TABLES['words']['fwords']}, {SQL_TABLES['words']['fpos']});"

SQL_INSERT_POS = \
f"insert into {SQL_TABLES['pos']['table']}({SQL_TABLES['pos']['fpos']}, posdesc) values (?, ?);"

SQL_INSERT_WORD = \
f"insert or replace into {SQL_TABLES['words']['table']} ({SQL_TABLES['words']['fwords']}, {SQL_TABLES['words']['fpos']})\n" \
f"values('{BRACES}', (select {SQL_TABLES['pos']['fid']} from {SQL_TABLES['pos']['table']} where {SQL_TABLES['pos']['fpos']} = '{BRACES}'));"


## ******************************************************************************** ##
class Sqlitedb:
    
    def __init__(self, dbname=None):
        if dbname: self.setpath(dbname) 
        
    def __del__(self):
        self.disconnect()
        
    def setpath(self, dbname, fullpath=False, recreate=False, connect=True):
        self.dbpath = os.path.abspath(dbname if fullpath else os.path.join(DICFOLDER, dbname + '.db')) \
            if not dbname is None else None
        #print(f'Set database path: {self.dbpath}')
        if connect and self.dbpath:
            if self.create_db(recreate):
                return self.connect() 
            else:
                return False
        return True
        
    def connect(self):
        if not os.path.isfile(self.dbpath):
            #print(COLOR_ERR + f'Database path {self.dbpath} is unavailable!')
            return False
        try:
            self.disconnect()
            self.conn = sqlite3.connect(self.dbpath)
            #print(f'Connected to database {self.dbpath}')
            return True
        except Exception as err:
            #print(COLOR_ERR + str(err))
            self.disconnect()
            return False
        except:
            self.disconnect()
            return False
        
    def disconnect(self, commit_trailing=True):
        if getattr(self, 'conn', None): 
            try:
                if commit_trailing: self.conn.commit()
                self.conn.close()
                #print(f'Disconnected from database {self.dbpath}')
            except:
                pass

    def create_db(self, overwrite=False):
        if os.path.isfile(self.dbpath) and not overwrite: return True
        try:
            self.disconnect()
            if os.path.isfile(self.dbpath):
                os.remove(self.dbpath)
            con = sqlite3.connect(':memory:')
            con.executescript(f"attach database '{self.dbpath}' as words;")
            con.close()
            if self.create_tables():
                #print(f'Created database: {self.dbpath}')
                return True
            return False
        
        except Exception as err:
            print(COLOR_ERR + str(err))
            self.disconnect()
            return False
        
        except:
            self.disconnect()
            return False
            
    def create_tables(self):
        if not self.connect(): return False
        try:
            #print(SQL_CREATE_TABLES)
            cur = self.conn.cursor()
            cur.executescript(SQL_CREATE_TABLES)
            self.conn.commit()
            #print(SQL_INSERT_POS)
            cur.executemany(SQL_INSERT_POS, POS)
            self.conn.commit()
            #print(f'Created objects for database: {self.dbpath}')
            return True
        except Exception as err:
            print(COLOR_ERR + f'DATABASE ERROR: {str(err)}')
            self.disconnect()
            return False
        except:
            self.disconnect()
            return False
    
    def get_pos(self):
        self.connect()
        cur = self.conn.cursor()
        return [res[0] for res in cur.execute(f"select {SQL_TABLES['pos']['fpos']} from {SQL_TABLES['pos']['table']}").fetchall()]
    
    def standard_posrules(self, lang):
        if lang == 'en':
            return {'N': '.*M.*', 'V': '.*[ADGS].*', 'ADJ': '.*[UY].*'}
        if lang == 'ru':
            return {'N': 'I.*', 'V': 'B.*', 'ADJ': 'C.*'}
        if lang == 'de':
            return {'N': '.*m.*', 'V': '.*(DI)|(XY).*', 'ADJ': '.*A.*'}
        if lang == 'fr':
            return {'N': '.*[SX].*', 'V': '.*[adfp].*', 'ADJ': '.*F.*'}
        return None
        
    def standard_replacements(self, lang):
        if lang == 'fr':
            return {'é': 'e', 'ê': 'e', 'è': 'e', 'â': 'a', 'î': 'i', 'ï': 'i', 'ç': 'c', 'û': 'u', 'ô': 'o'}
        if lang == 'ru':
            return {'ё': 'е'}
        return None
            
    def add_from_hunspell(self, dicfile, posrules, posrules_strict=True, 
                          posdelim='/', lcase=True, replacements=None, remove_hyphens=True,
                          filter_out=None, commit_each=1000, on_word=None, on_commit=None):
        """
        Imports a Hunspell-formatted (*.dic) dictionary file into the DB.
            - dicfile (str): path to imported dictionary
            - posrules (dict): part-of-speech parsing rules in the format:
                {'N': 'regex for nouns', 'V': 'regex for verb', ...}
                Possible keys are: 'N' (noun), 'V' (verb), 'ADV' (adverb), 'ADJ' (adjective), 
                'P' (participle), 'PRON' (pronoun), 'I' (interjection), 
                'C' (conjuction), 'PREP' (preposition), 'PROP' (proposition), 
                'MISC' (miscellaneous / other), 'NONE' (no POS)
            - posrules_strict (bool): if True, only the parts of speech present in posrules dict
                will be imported (all other words will be skipped). If False, such words
                will be imported with 'MISC' and 'NONE' POS markers
            - posdelim (str): delimiter delimiting the word and its part of speech (default = '/')
            - lcase (bool): if True, found words will be imported in lower case; otherwise, the
                original case will remain
            - replacements (dict): character replacement rules in the format:
                {'char_from': 'char_to', ...}
                Default = None (no replacements)
            - remove_hyphens (bool): if True, all hyphens ('-') will be removed from the words
            - filter_out (dict): regex-based rules to filter out (exclude) words in the format:
                {'word': ['regex1', 'regex2', ...], 'pos': ['regex1', 'regex2', ...]}
                These words will not be imported. One of the POS rules can be used to screen off
                specific parts of speech. Match rules for words will be applied AFTER replacements and
                in the sequential order of the regex list.
            - commit_each (int): threshold of insert operations after which the transaction will be committed
            - on_word (callable): callback function to be called when a word is imported into the DB            
            - on_commit (callable): 
        """
        poses = self.get_pos()
        for pos in posrules:
            if not pos in poses:
                raise Exception(f"Part of speech '{pos}' is absent from the DB!")
                
        if not self.connect(): return 0
        cur = self.conn.cursor()
        cnt = 0
        
        try:            
            with codecs.open(dicfile, 'r', encoding='utf-8', errors='ignore') as dic:
                for row in dic:
                    # split the next row to extract the word and part-of-speech
                    w = row.split(posdelim)
                    # extract the word (convert to lowercase if specified)
                    word = w[0].lower() if lcase else w[0]
                    # extract POS (empty string if none)
                    pos = w[1] if len(w) > 1 else ''
                    # skip non-AZ words
                    if not word.isalpha(): continue
                    # make replacements in word
                    if remove_hyphens:
                        word = word.replace('-', '')
                    if replacements:
                        for repl in replacements:
                            word = word.replace(repl, replacements[repl])
                    # filter out words and parts of speech according to rules
                    if filter_out:
                        if 'word' in filter_out:
                            for rex in filter_out['word']:
                                if re.match(filter_out['word'][rex], word, flags=re.I):
                                    continue
                        if 'pos' in filter_out and pos:
                            for rex in filter_out['pos']:
                                if re.match(filter_out['pos'][rex], pos, flags=re.I):
                                    continue
                    # determine the POS
                    if pos and posrules:
                        try:
                            for rex in posrules:
                                if re.match(posrules[rex], pos):
                                    pos = rex
                                    # insert into db
                                    cur.execute(SQL_INSERT_WORD.format(word, pos))                    
                                    # increment the counter            
                                    cnt += 1
                                    # commit if necessary
                                    if cnt >= commit_each and cnt % commit_each == 0:
                                        self.conn.commit()
                                        if on_commit: on_commit(cnt, dicfile)
                                    # call on_word
                                    if on_word: on_word(word, pos, cnt)
                                else:
                                    if posrules_strict: 
                                        continue
                                    else: 
                                        pos = 'MISC'
                                        
                        except Exception as err:
                            print(COLOR_ERR + f'DATABASE ERROR: {str(err)}')
                            break
                        
                    else:
                        if posrules_strict: 
                            continue
                        else: 
                            pos = 'NONE'
                        
                    if pos in ('MISC', 'NONE'):
                        # insert into db
                        try:
                            cur.execute(SQL_INSERT_WORD.format(word, pos))                    
                            # increment the counter            
                            cnt += 1
                            # commit if necessary
                            if cnt >= commit_each and cnt % commit_each == 0:
                                self.conn.commit()
                                if on_commit: on_commit(cnt, dicfile)
                            # call on_word
                            if on_word: on_word(word, pos, cnt)
                        except Exception as err:
                            print(COLOR_ERR + f'DATABASE ERROR: {str(err)}')
                            break
                    
        finally:   
            # commit outstanding updates
            self.conn.commit()
            cur.close()
            
        return cnt
    
    def add_all_from_hunspell(self, languages=None, on_commit=None, on_dict_add=None):
        """
        Inserts ALL Hunspell dictionaries found in 'assets/dic'.
        """
        old_dbpath = getattr(self, 'dbpath', None)
        cnt = 0
        for r, d, f in os.walk(DICFOLDER):
            for file in f:
                if file.lower().endswith('.dic'):                    
                    dicfile = os.path.abspath(os.path.join(r, file))
                    lang = file[:2].lower()
                    if (not lang in LANG) or (languages and not lang in languages): continue
                    if not self.setpath(lang, recreate=True): continue
                    try:
                        k = self.add_from_hunspell(dicfile=dicfile, 
                                                      posrules=self.standard_posrules(lang),
                                                      replacements=self.standard_replacements(lang),
                                                      on_commit=on_commit)
                        cnt += k
                        if on_dict_add: on_dict_add(dicfile, lang, k, cnt)
                    except Exception as err:
                        print(COLOR_ERR + str(err))
                        break
                    
        self.setpath(old_dbpath, fullpath=True)
        return cnt
    
