# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package pycross.dbapi
# Low-level SQLite database driver implementation with a bunch of handy methods
# to create the default DB structure to use as a word source, import words from 
# [Hunspell](https://hunspell.github.io/) open-source dictionaries, etc.
from utils.globalvars import *
from utils.utils import Task, is_iterable
import sqlite3, os, re, codecs, requests, traceback
from urllib.request import urlopen
from PyQt5 import QtCore

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
## SQL query to clear words
SQL_CLEAR_WORDS = f"delete from {SQL_TABLES['words']['table']};"
## SQL query to count entries (words)
SQL_COUNT_WORDS = f"select count(*) from {SQL_TABLES['words']['table']};"
## Hunspell dic repo URL
HUNSPELL_REPO = 'https://raw.githubusercontent.com/wooorm/dictionaries/master'

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
    
# ******************************************************************************** #

class HunspellDownloadSignals(QtCore.QObject):

    sigStart = QtCore.pyqtSignal(int, str, str, str)
    sigGetFilesize = QtCore.pyqtSignal(int, str, str, str, int)
    sigProgress = QtCore.pyqtSignal(int, str, str, str, int, int)
    sigComplete = QtCore.pyqtSignal(int, str, str, str)
    sigError = QtCore.pyqtSignal(int, str, str, str, str)

class HunspellDownloadTask(QtCore.QRunnable):

    def __init__(self, settings, dicfolder, url, lang, overwrite=True, on_stopcheck=None, id=0):
        super().__init__()
        self.signals = HunspellDownloadSignals()
        self.dicfolder = dicfolder
        self.url = url
        self.lang = lang
        self.overwrite = overwrite
        self.id = id
        self.on_stopcheck = on_stopcheck
        self.timeout_ = settings['common']['web']['req_timeout'] * 500
        self.proxies_ = {'http': settings['common']['web']['proxy']['http'], 'https': settings['common']['web']['proxy']['https']} if not settings['common']['web']['proxy']['use_system'] else None

    def get_filesize_url(self, url):
        try:
            site = urlopen(url)
            meta = site.info()
            return int(meta.get('Content-Length', -1))
        except:
            return -1

    def _delete_file(self, filepath):
        try:
            os.remove(filepath)
        except:
            pass
    
    def run(self):
        
        filepath = os.path.join(self.dicfolder, f"{self.lang}.dic")
        if self.on_stopcheck and self.on_stopcheck(self.id, self.url, self.lang, filepath):
            #print(f"Остановили загрузку файла '{self.lang}' (id={self.id})")
            return

        self.signals.sigStart.emit(self.id, self.url, self.lang, filepath)

        if os.path.exists(filepath) and not self.overwrite:
            self.signals.sigComplete.emit(self.id, self.url, self.lang, filepath)      
            return

        try:
            total_bytes = self.get_filesize_url(self.url)
            self.signals.sigGetFilesize.emit(self.id, self.url, self.lang, filepath, total_bytes)

            with requests.get(self.url, stream=True, allow_redirects=True, 
                            headers={'content-type': 'text/plain; charset=utf-8'},
                            timeout=self.timeout_, proxies=self.proxies_) as res:
                if not res or res.status_code != 200:
                    self.signals.sigError.emit(self.id, self.url, self.lang, filepath, 
                                            f"{getattr(res, 'text', 'HTTP error')} - status code {res.status_code}")
                    return            
                try:
                    with open(filepath, 'wb') as f:
                        for chunk in res.iter_content(1024):
                            if self.on_stopcheck and self.on_stopcheck(self.id, self.url, self.lang, filepath):
                                #print(f"Остановили загрузку файла '{self.lang}' (id={self.id})")
                                f.close()
                                self._delete_file(filepath)
                                return
                            f.write(chunk)
                            self.signals.sigProgress.emit(self.id, self.url, self.lang, filepath, f.tell(), total_bytes)
                except Exception as err:
                    f.close()
                    self.signals.sigError.emit(self.id, self.url, self.lang, filepath, str(err))
                    self._delete_file(filepath)
                    return
                except:
                    f.close()
                    self._delete_file(filepath)
                    raise

        except Exception as err:
            self.signals.sigError.emit(self.id, self.url, self.lang, filepath, str(err))
            self._delete_file(filepath)
            return

        except:
            self.signals.sigError.emit(self.id, self.url, self.lang, filepath, traceback.format_exc())
            self._delete_file(filepath)
            return

        #print(f"Завершили загрузку файла '{self.lang}' (id={self.id})")
        self.signals.sigComplete.emit(self.id, self.url, self.lang, filepath)

# ******************************************************************************** #

class HunspellImportSignals(QtCore.QObject):

    sigStart = QtCore.pyqtSignal(int, str, str)
    sigWordWritten = QtCore.pyqtSignal(int, str, str, str, str, int)
    sigCommit = QtCore.pyqtSignal(int, str, str, int)
    sigComplete = QtCore.pyqtSignal(int, str, str, int)
    sigError = QtCore.pyqtSignal(int, str, str, str)

class HunspellImportTask(QtCore.QRunnable):

    def __init__(self, lang, dicfile=None, posrules=None, posrules_strict=False, 
                posdelim='/', lcase=True, replacements=None, remove_hyphens=True,
                filter_out=None, rows=None, commit_each=1000, on_stopcheck=None, id=0):
        super().__init__()
        self.signals = HunspellImportSignals()

        self.lang = lang
        self.dicfile = dicfile or os.path.join(DICFOLDER, f"{lang}.dic")
        self.posrules = posrules
        self.posrules_strict = posrules_strict
        self.posdelim = posdelim
        self.lcase = lcase
        self.replacements = replacements
        self.remove_hyphens = remove_hyphens
        self.filter_out = filter_out
        self.rows = rows
        self.commit_each = commit_each
        self.on_stopcheck = on_stopcheck
        self.id = id

    def _delete_db(self, db):
        try:
            db.disconnect()
            os.remove(db.dbpath)
        except:
            pass

    ## Retrieves the list of parts of speech present in the DB.
    # @returns `list` parts of speech in the short form, e.g. ['N', 'V']
    def _get_pos(self, cur):     
        return [res[0] for res in cur.execute(f"select {SQL_TABLES['pos']['fpos']} from {SQL_TABLES['pos']['table']}").fetchall()]

    def run(self):
        
        if self.on_stopcheck and self.on_stopcheck(self.id, self.lang, self.dicfile):
            #print(f"Остановили импорт файла '{self.lang}' (id={self.id})")
            return

        #print(f"Стартовали импорт файла '{self.lang}' (id={self.id})")
        self.signals.sigStart.emit(self.id, self.lang, self.dicfile)

        db = Sqlitedb()
        if not db.setpath(self.lang):
            self.signals.sigError.emit(self.id, self.lang, self.dicfile, _('Unable to connect to database {}!').format(self.lang))
            return

        stopped = False
        cur = db.conn.cursor()

        if self.posrules:
            poses = self._get_pos(cur)
            for pos in self.posrules:
                if not pos in poses:
                    self.signals.sigError.emit(self.id, self.lang, self.dicfile, _("Part of speech '{}' is absent from the DB!").format(pos))
                    self._delete_db(db)
                    return
       
        cnt = 0
        try:            
            with codecs.open(self.dicfile, 'r', encoding=ENCODING, errors='ignore') as dic:
                if not self.rows:
                    dic_iterate = dic 
                else:
                    if self.rows[1] >= self.rows[0]:
                        dic_iterate = (row for i, row in enumerate(dic) if i in range(self.rows[0], self.rows[1] + 1))
                    else:
                        dic_iterate = (row for i, row in enumerate(dic) if i >= self.rows[0])
                                
                for row in dic_iterate:
                    # check stop request
                    if stopped or \
                            (self.on_stopcheck and \
                             self.on_stopcheck(self.id, self.lang, self.dicfile)):
                        #print(f"Остановили импорт файла '{self.lang}' (id={self.id})")
                        stopped = True
                        break
                    # split the next row to extract the word and part-of-speech
                    w = row.split(self.posdelim)
                    # extract the word (convert to lowercase if specified)
                    word = w[0].lower() if self.lcase else w[0]
                    # extract POS (empty string if none)
                    pos = w[1] if len(w) > 1 else ''
                    # skip non-AZ words
                    if not word.isalpha(): continue
                    # make self.replacements in word
                    if self.remove_hyphens:
                        word = word.replace('-', '')
                    if self.replacements:
                        for repl in self.replacements:
                            word = word.replace(repl, self.replacements[repl])
                    # filter out words and parts of speech according to rules
                    if self.filter_out:
                        if 'word' in self.filter_out:
                            for rex in self.filter_out['word']:
                                if re.match(rex, word, flags=re.I):
                                    continue
                        if 'pos' in self.filter_out and pos:
                            for rex in self.filter_out['pos']:
                                if re.match(rex, pos, flags=re.I):
                                    continue
                    # determine the POS
                    if pos and self.posrules:
                        try:
                            for rex in self.posrules:
                                # check stop request
                                if stopped or \
                                        (self.on_stopcheck and \
                                         self.on_stopcheck(self.id, self.lang, self.dicfile)):
                                    #print(f"Остановили импорт файла '{self.lang}' (id={self.id})")
                                    stopped = True
                                    break
                                if re.match(self.posrules[rex], pos):
                                    pos = rex
                                    # insert into db
                                    cur.execute(SQL_INSERT_WORD.format(word, pos))                    
                                    # increment the counter            
                                    cnt += 1
                                    # commit if necessary
                                    if cnt >= self.commit_each and cnt % self.commit_each == 0:
                                        db.conn.commit()
                                        self.signals.sigCommit.emit(self.id, self.lang, self.dicfile, cnt)
                                    # call on_word
                                    self.signals.sigWordWritten.emit(self.id, self.lang, self.dicfile, word, pos, cnt)
                                else:
                                    if self.posrules_strict: 
                                        continue
                                    else: 
                                        pos = 'MISC'
                                        
                        except Exception as err:
                            self.signals.sigError.emit(self.id, self.lang, self.dicfile, _('DATABASE ERROR: {}').format(str(err)))
                            stopped = True
                            break
                        
                    else:
                        if self.posrules_strict: 
                            continue
                        else: 
                            pos = 'NONE'

                    if stopped:
                        break                        
                    elif pos in ('MISC', 'NONE'):
                        # insert into db
                        try:
                            cur.execute(SQL_INSERT_WORD.format(word, pos))                    
                            # increment the counter            
                            cnt += 1
                            # commit if necessary
                            if cnt >= self.commit_each and cnt % self.commit_each == 0:
                                db.conn.commit()
                                self.signals.sigCommit.emit(self.id, self.lang, self.dicfile, cnt)
                            # call on_word
                            self.signals.sigWordWritten.emit(self.id, self.lang, self.dicfile, word, pos, cnt)
                        except Exception as err:
                            self.signals.sigError.emit(self.id, self.lang, self.dicfile, _('DATABASE ERROR: {}').format(str(err)))
                            stopped = True
                            break

                if stopped:
                    self._delete_db(db)

        except Exception as err:
            self.signals.sigError.emit(self.id, self.lang, self.dicfile, str(err))
            stopped = True

        except:
            self.signals.sigError.emit(self.id, self.lang, self.dicfile, traceback.format_exc())
            stopped = True
                    
        finally:   
            # commit outstanding updates
            if stopped:
                self._delete_db(db)
            else:
                try:
                    db.conn.commit()
                    cur.close()
                except:
                    pass
                else:
                    self.signals.sigComplete.emit(self.id, self.lang, self.dicfile, cnt)                

# ******************************************************************************** #

class HunspellImport:

    def __init__(self, settings, dbmanager=None, dicfolder=DICFOLDER):
        self.settings = settings
        self.db = dbmanager or Sqlitedb()
        self.dicfolder = dicfolder
        self.pool = QtCore.QThreadPool()
        self.timeout_ = settings['common']['web']['req_timeout'] * 500
        self.proxies_ = {'http': settings['common']['web']['proxy']['http'], 'https': settings['common']['web']['proxy']['https']} if not settings['common']['web']['proxy']['use_system'] else None

    def pool_running(self):
        return bool(self.pool.activeThreadCount())

    def pool_threadcount(self):
        return self.pool.activeThreadCount()

    def pool_wait(self):
        if self.pool_running():
            self.pool.waitForDone()

    def get_installed_info(self, lang):
        filepath = os.path.join(self.dicfolder, f"{lang}.db")
        if not os.path.exists(filepath) or not self.db.setpath(filepath, True): 
            return None
        cur = self.db.conn.cursor()
        res = cur.execute(SQL_COUNT_WORDS).fetchone()
        if not res: return None
        return {'entries': int(res[0]), 'path': filepath}
    
    ## Retrieves the list of Hunspell dictionaries available for
    # download from the [public Github repo](https://github.com/wooorm/dictionaries/).
    def list_hunspell(self, stopcheck=None):
        readme = f"{HUNSPELL_REPO}/readme.md"
        dics = []
        res = requests.get(readme, allow_redirects=True, timeout=self.timeout_, proxies=self.proxies_)
        if not res: return []
        if stopcheck and stopcheck(): return []
        res = res.text
        regex = re.compile(r'(\(dictionaries/[\w]+\))(\s*\|\s*)([\w\s]+)(\s*\|\s*)(\[.*?\])(\(.*?\))', re.I)
        try:
            for match in regex.finditer(res):
                if stopcheck and stopcheck(): break
                entry = {}
                m = match[1][1:-1]
                entry['dic_url'] = f"{HUNSPELL_REPO}/{m}/index.dic"
                entry['lang'] = m.split('/')[1]
                entry['lang_full'] = match[3].strip()
                entry['license'] = match[5][1:-1]
                if entry['license'].startswith('(') and entry['license'].endswith(')'):
                    entry['license'] = entry['license'][1:-1]
                entry['license_url'] = f"{HUNSPELL_REPO}/{match[6][1:-1]}"
                dics.append(entry)
        except Exception:
            return []
        return dics

    def list_all_dics(self, stopcheck=None):
        dics = self.list_hunspell(stopcheck)
        for dic in dics:            
            info = self.get_installed_info(dic['lang'])
            if not info: info = {'entries': 0, 'path': ''}
            dic.update(info)
            if stopcheck and stopcheck(): return dics
        return dics

    def download_hunspell(self, url, lang, overwrite=True, on_stopcheck=None,
                          on_start=None, on_getfilesize=None, on_progress=None, 
                          on_complete=None, on_error=None, wait=False):
        task = HunspellDownloadTask(self.settings, self.dicfolder,
                                    url, lang, overwrite, on_stopcheck)
        if on_start:
            task.signals.sigStart.connect(on_start)
        if on_getfilesize:
            task.signals.sigGetFilesize.connect(on_getfilesize)
        if on_progress:
            task.signals.sigProgress.connect(on_progress)
        if on_complete:
            task.signals.sigComplete.connect(on_complete)
        if on_error:
            task.signals.sigError.connect(on_error)
        self.pool.start(task)
        if wait:
            self.pool.waitForDone()

    def download_hunspell_all(self, dics, on_stopcheck=None, on_start=None,
                              on_getfilesize=None, on_progress=None,
                              on_complete=None, on_error=None):
        if not dics: return

        for i, entry in enumerate(dics):
            task = HunspellDownloadTask(self.settings, self.dicfolder, 
                        entry['dic_url'], entry['lang'], True,  
                        on_stopcheck, i)
            if on_start:
                task.signals.sigStart.connect(on_start)
            if on_getfilesize:
                task.signals.sigGetFilesize.connect(on_getfilesize)
            if on_progress:
                task.signals.sigProgress.connect(on_progress)
            if on_complete:
                task.signals.sigComplete.connect(on_complete)
            if on_error:
                task.signals.sigError.connect(on_error)
            self.pool.start(task)
            #print(f"СТАРТ ЗАКАЧКИ '{entry['lang']}' (ID={i})")

    
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
    # @param lang `str` short name of the imported dictionary language, e.g. 'en', 'de' etc.
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
    # on_word(lang: str, dicfile: str, word: str, part_of_speech: str, records_committed: int) -> None
    # @endcode
    # @param on_commit `callable` callback function to be called when a next portion of records 
    # is written to the DB. Callback prototype is: 
    # @code
    # on_commit(lang: str, dicfile: str, records_committed: int) -> None
    # @endcode
    # @returns `int` number of words imported from the dictionary
    # @see add_all_from_hunspell()
    # @param on_error `callable` callback function to be called when an exception
    # occurs
    # Callback prototype is: 
    # @code
    # on_error(lang: str, dicfile: str, error_message: str) -> None
    # @endcode
    def add_from_hunspell(self, lang, posrules=None, posrules_strict=False, 
                          posdelim='/', lcase=True, replacements=None, remove_hyphens=True,
                          filter_out=None, rows=None, commit_each=1000, on_checkstop=None,
                          on_start=None, on_word=None, on_commit=None, 
                          on_finish=None, on_error=None, wait=False):
        dicfile = os.path.join(self.dicfolder, f"{lang}.dic")
        task = HunspellImportTask(lang, dicfile, posrules, posrules_strict,
                                  posdelim, lcase, replacements, remove_hyphens,
                                  filter_out, rows, commit_each, on_checkstop)
        if on_start:
            task.signals.sigStart.connect(on_start)
        if on_word:
            task.signals.sigWordWritten.connect(on_word)
        if on_commit:
            task.signals.sigCommit.connect(on_commit)
        if on_finish:
            task.signals.sigComplete.connect(on_finish)
        if on_error:
            task.signals.sigError.connect(on_error)

        self.pool.start(task)
        if wait:
            self.pool.waitForDone()
    
    ## @brief Imports all Hunspell-formatted dictionaries found in 'assets/dic'.
    # @warning All imported dictionary files must have the '.dic' extension.
    # @param dics `iterable` list of dict containing language info
    # (others found will be skipped).
    # Default = `None` (import all found dictionaries)  
    # @see add_from_hunspell()
    def add_all_from_hunspell(self, dics, 
                            posrules=None, posrules_strict=True, 
                            posdelim='/', lcase=True, replacements=None, remove_hyphens=True,
                            filter_out=None, rows=None, commit_each=1000, on_stopcheck=None, 
                            on_start=None, on_word=None, on_commit=None, on_finish=None, on_error=None):
        
        if not dics: return

        if isinstance(posrules, list) and len(posrules) != len(dics):
            print('ERROR! Number of elements in "posrules" must be equal to "dics"!')
            return
        if isinstance(posrules_strict, list) and len(posrules_strict) != len(dics):
            print('ERROR! Number of elements in "posrules_strict" must be equal to "dics"!')
            return
        if isinstance(posdelim, list) and len(posdelim) != len(dics):
            print('ERROR! Number of elements in "posdelim" must be equal to "dics"!')
            return
        if isinstance(lcase, list) and len(lcase) != len(dics):
            print('ERROR! Number of elements in "lcase" must be equal to "dics"!')
            return
        if isinstance(replacements, list) and len(replacements) != len(dics):
            print('ERROR! Number of elements in "replacements" must be equal to "dics"!')
            return
        if isinstance(remove_hyphens, list)and len(remove_hyphens) != len(dics):
            print('ERROR! Number of elements in "remove_hyphens" must be equal to "dics"!')
            return
        if isinstance(filter_out, list) and len(filter_out) != len(dics):
            print('ERROR! Number of elements in "filter_out" must be equal to "dics"!')
            return
        if isinstance(rows, list) and len(rows) != len(dics):
            print('ERROR! Number of elements in "rows" must be equal to "dics"!')
            return
        if isinstance(commit_each, list) and len(commit_each) != len(dics):
            print('ERROR! Number of elements in "commit_each" must be equal to "dics"!')
            return
        
        #old_dbpath = getattr(self.db, 'dbpath', None)
        self.db.disconnect()

        for i, entry in enumerate(dics):
            task = HunspellImportTask(entry['lang'], 
                            os.path.join(self.dicfolder, f"{entry['lang']}.dic"), 
                            posrules[i] if isinstance(posrules, list) else posrules, 
                            posrules_strict[i] if isinstance(posrules_strict, list) else posrules_strict,
                            posdelim[i] if isinstance(posdelim, list) else posdelim, 
                            lcase[i] if isinstance(lcase, list) else lcase, 
                            replacements[i] if isinstance(replacements, list) else replacements,  
                            remove_hyphens[i] if isinstance(remove_hyphens, list) else remove_hyphens,  
                            filter_out[i] if isinstance(filter_out, list) else filter_out,  
                            rows[i] if isinstance(rows, list) else rows,
                            commit_each[i] if isinstance(commit_each, list) else commit_each, 
                            on_stopcheck, i)
            if on_start:
                task.signals.sigStart.connect(on_start)
            if on_word:
                task.signals.sigWordWritten.connect(on_word)
            if on_commit:
                task.signals.sigCommit.connect(on_commit)
            if on_finish:
                task.signals.sigComplete.connect(on_finish)
            if on_error:
                task.signals.sigError.connect(on_error)
            #print(f"СТАРТ ИМПОРТА '{entry['lang']}' (ID={i})")
            self.pool.start(task)