# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package pycross.dbapi
# Low-level SQLite database driver implementation with a bunch of handy methods
# to create the default DB structure to use as a word source, import words from 
# [Hunspell](https://hunspell.github.io/) open-source dictionaries, etc.
from utils.globalvars import *
import sqlite3, os, re, codecs

# ******************************************************************************** #

## SQL query to create default table structure
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
## SQL query to insert part of speech data
SQL_INSERT_POS = \
f"insert into {SQL_TABLES['pos']['table']}({SQL_TABLES['pos']['fpos']}, posdesc) values (?, ?);"
## SQL query to insert words and part of speech data
SQL_INSERT_WORD = \
f"insert or replace into {SQL_TABLES['words']['table']} ({SQL_TABLES['words']['fwords']}, {SQL_TABLES['words']['fpos']})\n" \
f"values('{BRACES}', (select {SQL_TABLES['pos']['fid']} from {SQL_TABLES['pos']['table']} where {SQL_TABLES['pos']['fpos']} = '{BRACES}'));"


# ******************************************************************************** #

## @brief SQLite database driver implementation wrapping the standard Python sqlite3 methods.
# Some handy methods are added to connect / disconnect to / from the DB,
# create / recreate the DB with the default set of tables (to use as a word source),
# and import [Hunspell](https://hunspell.github.io/) dictionary data.
class Sqlitedb:
    
    ## Constructor initializes DB driver connection.
    # @param dbname `str` path to database file (*.db) or an abbreviated language name
    # for preinstalled DB files stored in 'assets/dic', e.g. 'en' (='assets/dic/en.db')
    def __init__(self, dbname=None):
        if dbname: self.setpath(dbname) 
        
    ## Destructor disconnects from DB.
    def __del__(self):
        self.disconnect()
        
    ## Initializes the path to the DB file and establishes a connection if required.
    # @param dbname `str` path to database file (*.db) or an abbreviated language name -
    # see init()
    # @param fullpath `bool` `True` to indicate that the 'dbname' argument is the full file path
    # (default = `False`)
    # @param recreate `bool` `True` to recreate the database file with the default table structure
    # (default = `False`).
    # @warning If set to `True`, all data in the DB file (if present) will be lost!
    # @param connect `bool` `True` (default) to attempt connecting to the DB immediately
    # @returns `bool` `True` on success, `False` on failure
    def setpath(self, dbname, fullpath=False, recreate=False, connect=True):
        ## `str` full path to the DB
        self.dbpath = os.path.abspath(dbname if fullpath else os.path.join(DICFOLDER, dbname + '.db')) \
            if not dbname is None else None
        #print(f'Set database path: {self.dbpath}')
        if connect and self.dbpath:
            if self.create_db(recreate):
                return self.connect() 
            else:
                return False
        return True
        
    ## Connects to the DB file (Sqlitedb::dbpath).
    # @returns `bool` `True` on success, `False` on failure
    def connect(self):
        if not os.path.isfile(self.dbpath):
            #print(f'Database path {self.dbpath} is unavailable!')
            return False
        try:
            self.disconnect()
            ## internal DB connection object (SQLite driver)
            self.conn = sqlite3.connect(self.dbpath)
            #print(f'Connected to database {self.dbpath}')
            return True
        except Exception as err:
            #print(str(err))
            self.disconnect()
            return False
        except:
            self.disconnect()
            return False
        
    ## Disconnects from the currently open DB.
    # @param commit_trailing `bool` `True` (default) to commit all pending changes 
    # to the DB before disconnecting
    def disconnect(self, commit_trailing=True):
        if getattr(self, 'conn', None): 
            try:
                if commit_trailing: self.conn.commit()
                self.conn.close()
                #print(f'Disconnected from database {self.dbpath}')
            except:
                pass

    ## Creates the DB in Sqlitedb::dbpath, optionally overwriting the existing file.
    # @param overwrite `bool` True to overwrite the existing file (default = `False`)
    # @warning If set to `True`, all data in the DB file (if present) will be lost!
    # @returns `bool` `True` on success, `False` on failure
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
            print(str(err))
            self.disconnect()
            return False
        
        except:
            self.disconnect()
            return False
            
    ## Creates the default table structure in the DB.
    # @returns `bool` `True` on success, `False` on failure
    # @see utils::globalvars::SQL_TABLES
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
            print(_('DATABASE ERROR: {}').format(str(err)))
            self.disconnect()
            return False
        except:
            self.disconnect()
            return False
    
    ## Retrieves the list of parts of speech present in the DB.
    # @returns `list` parts of speech in the short form, e.g. ['N', 'V']
    def get_pos(self):
        self.connect()
        cur = self.conn.cursor()
        return [res[0] for res in cur.execute(f"select {SQL_TABLES['pos']['fpos']} from {SQL_TABLES['pos']['table']}").fetchall()]
    
    ## @brief Returns the default Hunspell-formatted metadata patterns for the three common
    # parts of speech (noun, verb, adjective).
    # The returned patterns depend on the language.
    # @param lang `str` language for which the matching patterns are requested, e.g. 'en' or 'ru'
    # @returns `dict` POS to regex pattern matching table in the format:
    # @code
    # {'N': 'regex pattern for nouns', 'V': 'regex pattern for verbs', 'ADJ': 'regex pattern for adjectives'}
    # @endcode 
    # If the language is invalid (none of 'en', 'ru', 'fr' or 'de'), `None` is returned.\n 
    # Reimplement this method as needed to support other languages / parts of speech formats.
    # @see add_from_hunspell()
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
        
    ## Returns the default replacement rules for a language to use in Hunspell imports.
    # @param lang `str` language for which the matching patterns are requested, e.g. 'en' or 'ru'
    # @returns `dict` default replacements in the format:
    # @code
    # {'character to replace': 'replacement character'}
    # @endcode
    # If the language is invalid (currently only 'ru' or 'fr'), `None` is returned.\n 
    # Reimplement this method as needed to add other languages / replaced characters.
    # @see add_from_hunspell()
    def standard_replacements(self, lang):
        if lang == 'fr':
            return {'é': 'e', 'ê': 'e', 'è': 'e', 'â': 'a', 'î': 'i', 'ï': 'i', 'ç': 'c', 'û': 'u', 'ô': 'o'}
        if lang == 'ru':
            return {'ё': 'е'}
        return None
            
    ## @brief Imports a Hunspell-formatted dictionary file into the DB.
    # [Hunspell](https://hunspell.github.io/) dictionaries can be downloaded
    # from [LibreOffice](https://cgit.freedesktop.org/libreoffice/dictionaries/tree/)
    # or [Github](https://github.com/wooorm/dictionaries). Default dictionaries and
    # prebuilt SQLite databases are found in assets/dic.
    # @param dicfile `str` path to imported dictionary file (*.dic).
    # @warning The file must be in _plain text_ format, with each word on a new line,
    # optionally followed by a slash (see 'posdelim' argument) and meta-data (parts of speech etc.)
    # @param posrules `dict` part-of-speech regular expression parsing rules in the format:
    # @code {'N': 'regex for nouns', 'V': 'regex for verb', ...} @endcode
    # <pre>
    #     Possible keys are: 'N' [noun], 'V' [verb], 'ADV' [adverb], 'ADJ' [adjective], 
    #     'P' [participle], 'PRON' [pronoun], 'I' [interjection], 
    #     'C' [conjuction], 'PREP' [preposition], 'PROP' [proposition], 
    #     'MISC' [miscellaneous / other], 'NONE' [no POS]
    # </pre>
    # @param posrules_strict `bool` if `True` (default), only the parts of speech present in posrules dict
    # will be imported [all other words will be skipped]. If `False`, such words
    # will be imported with 'MISC' and 'NONE' POS markers.
    # @param posdelim `str` delimiter delimiting the word and its part of speech [default = '/']
    # @param lcase `bool` if `True` (default), found words will be imported in lower case; otherwise, the
    # original case will remain
    # @param replacements `dict`: character replacement rules in the format:
    # @code 
    # {'char_from': 'char_to', ...}
    # @endcode
    # Default = `None` (no replacements)
    # @param remove_hyphens `bool` if `True` (default), all hyphens ['-'] will be removed from the words
    # @param filter_out `dict` regex-based rules to filter out [exclude] words in the format:
    # @code 
    # {'word': ['regex1', 'regex2', ...], 'pos': ['regex1', 'regex2', ...]}
    # @endcode
    # These words will not be imported. One of the POS rules can be used to screen off
    # specific parts of speech. Match rules for words will be applied AFTER replacements and
    # in the sequential order of the regex list. Default = `None` (no filter rules apply).
    # @param commit_each `int` threshold of insert operations after which the transaction will be committed
    # (default = 1000)
    # @param on_word `callable` callback function to be called when a word is imported into the DB.           
    # Callback prototype is: 
    # @code
    # on_word([word: str, part_of_speech: str, records_committed: int]) -> None
    # @endcode
    # @param on_commit `callable`: callback function to be called when a next portion of records 
    # is written to the DB. Callback prototype is: 
    # @code
    # on_commit(records_committed: int, dic_file: str) -> None
    # @endcode
    # @returns `int` number of words imported from the dictionary
    # @see add_all_from_hunspell()
    def add_from_hunspell(self, dicfile, posrules, posrules_strict=True, 
                          posdelim='/', lcase=True, replacements=None, remove_hyphens=True,
                          filter_out=None, commit_each=1000, on_word=None, on_commit=None):
        poses = self.get_pos()
        for pos in posrules:
            if not pos in poses:
                raise Exception(_("Part of speech '{}' is absent from the DB!").format(pos))
                
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
                            print(_('DATABASE ERROR: {}').format(str(err)))
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
                            print(_('DATABASE ERROR: {}').format(str(err)))
                            break
                    
        finally:   
            # commit outstanding updates
            self.conn.commit()
            cur.close()
            
        return cnt
    
    ## @brief Imports all Hunspell-formatted dictionaries found in 'assets/dic'.
    # @warning All imported dictionary files must have the '.dic' extension.
    # @param languages `iterable` list of languages to import, e.g. ['en', 'fr']
    # (others found will be skipped).
    # Default = `None` (import all found dictionaries)
    # @param on_commit `callable` callback function to be called when a next portion of records is written to the DB.\n 
    # Callback prototype is:
    # @code
    # on_commit(records_committed: int, dic_file: str) -> None
    # @endcode
    # @param on_dict_add `callable` callback function to be called when a next dictionary has been imported.\n 
    # Callback prototype is: 
    # @code
    # on_dict_add(dic_file: str, lang: str, records_from_file: int, total_records: int) -> None
    # @endcode
    # @returns `int` number of words imported from the dictionaries (aggregate)
    # @see add_from_hunspell()
    def add_all_from_hunspell(self, languages=None, on_commit=None, on_dict_add=None):
        old_dbpath = getattr(self, 'dbpath', None)
        cnt = 0
        for r, _, f in os.walk(DICFOLDER):
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
                        print(str(err))
                        break
                    
        self.setpath(old_dbpath, fullpath=True)
        return cnt
    
