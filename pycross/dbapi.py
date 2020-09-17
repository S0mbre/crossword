# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package pycross.dbapi
# @brief Implements classes to work with SQLite databases created from [Hunspell dictionaries](https://github.com/wooorm/dictionaries).
#
# pycrossword can download raw DIC files from the repo for each available language and
# convert them to SQLite database files (*.db) stored locally in pycross/assets/dic.
# Each language is denoted by its 2-character short name, e.g. 'en' = English,
# 'de' = German (deutsch), 'ru' = Russian, etc. So a file stored as pycross/assets/dic/it.db
# means there is an Italian word source (database) installed and usable to create crosswords.
# By default, a Hunspell DIC file represents a list of words followed by part-of-speech
# markers, e.g.:
# <pre>
# confederacy/SM
# confederate/M
# confer/S
# conferee/SM
# conference/MGS
# ...
# </pre>
# See part-of-speech names: utils::globalvars::POS
# Accordingly, the default structure of the SQLite DB file is as follows:
# <pre>
# 1. Table 'tpos': parts of speeches
#   * Field 'id': unique record ID
#   * Field 'pos': short part-of-speech name, e.g. 'N' (=noun)
#   * Field 'posdesc': full part-of-speech name, e.g. 'Noun'
# 2. Table 'twords': words
#   * Field 'id': unique record ID
#   * Field 'word': word proper (in lower case), e.g. 'conference'
#   * Field 'idpos': cross-reference to a part of speech ('id' field in 'tpos' table)
# </pre>
# See default table and field names: utils::globalvars::SQL_TABLES

from utils.globalvars import *
from utils.utils import Task, is_iterable
import sqlite3, os, re, codecs, requests, traceback
from urllib.request import urlopen
from PyQt5 import QtCore

# ******************************************************************************** #

## `str` newline symbol
NEWLINE = '\n'
## `str` SQL query to create default table structure
SQL_CREATE_TABLES = \
f"create table if not exists {SQL_TABLES['pos']['table']} ({NEWLINE}" \
f"{SQL_TABLES['pos']['fid']} integer primary key autoincrement,{NEWLINE}" \
f"{SQL_TABLES['pos']['fpos']} text not null,{NEWLINE}" \
f"{SQL_TABLES['pos']['fposdesc']} text default '');{NEWLINE}" \
f"create table if not exists {SQL_TABLES['words']['table']} ({NEWLINE}" \
f"{SQL_TABLES['words']['fid']} integer primary key autoincrement,{NEWLINE}" \
f"{SQL_TABLES['words']['fwords']} text not null,{NEWLINE}" \
f"{SQL_TABLES['words']['fpos']} integer,{NEWLINE}" \
f"foreign key ({SQL_TABLES['words']['fpos']}) references {SQL_TABLES['pos']['table']}({SQL_TABLES['pos']['fid']}) on delete set null on update no action);{NEWLINE}" \
f"create unique index word_idx on {SQL_TABLES['words']['table']}({SQL_TABLES['words']['fwords']}, {SQL_TABLES['words']['fpos']});"
## `str` SQL query to insert part of speech data
SQL_INSERT_POS = \
f"insert into {SQL_TABLES['pos']['table']}({SQL_TABLES['pos']['fpos']}, {SQL_TABLES['pos']['fposdesc']}) values (?, ?);"
## `str` SQL query to insert words and part of speech data
SQL_INSERT_WORD = \
f"insert or replace into {SQL_TABLES['words']['table']} ({SQL_TABLES['words']['fwords']}, {SQL_TABLES['words']['fpos']}){NEWLINE}" \
f"values('{BRACES}', (select {SQL_TABLES['pos']['fid']} from {SQL_TABLES['pos']['table']} where {SQL_TABLES['pos']['fpos']} = '{BRACES}'));"
## `str` SQL query to clear words
SQL_CLEAR_WORDS = f"delete from {SQL_TABLES['words']['table']};"
## `str` SQL query to count entries (words)
SQL_COUNT_WORDS = f"select count(*) from {SQL_TABLES['words']['table']};"
## `str` SQL query to display all words
SQL_GET_WORDS = f"select {SQL_TABLES['words']['table']}.{SQL_TABLES['words']['fid']}, " \
f"{SQL_TABLES['words']['table']}.{SQL_TABLES['words']['fwords']}, " \
f"{SQL_TABLES['pos']['table']}.{SQL_TABLES['pos']['fpos']}, " \
f"{SQL_TABLES['pos']['table']}.{SQL_TABLES['pos']['fposdesc']} " \
f"from {SQL_TABLES['words']['table']}{NEWLINE}" \
f"join {SQL_TABLES['pos']['table']} on {SQL_TABLES['words']['table']}.{SQL_TABLES['words']['fpos']} = {SQL_TABLES['pos']['table']}.{SQL_TABLES['pos']['fid']};"
## `str` SQL query to display all POS
SQL_GET_POS = f"select * from {SQL_TABLES['pos']['table']};"
## `str` Hunspell dic repo URL
HUNSPELL_REPO = 'https://raw.githubusercontent.com/wooorm/dictionaries/main'

# ******************************************************************************** #

## @brief SQLite database driver implementation wrapping the standard Python sqlite3 methods.
# Some handy methods are added to connect / disconnect to / from the DB,
# create / recreate the DB with the default set of tables (to use as a word source),
# and import [Hunspell](https://hunspell.github.io/) dictionary data.
class Sqlitedb:

    ## Constructor initializes DB driver connection.
    # @param dbname `str` path to database file (*.db) or an abbreviated language name
    # for preinstalled DB files stored in 'assets/dic', e.g. 'en' (='assets/dic/en.db')
    def __init__(self, dbname=None, fullpath=False, recreate=False, connect=True):
        if dbname:
            self.setpath(dbname, fullpath, recreate, connect)

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

    ## Retrieves all words from the database.
    # @returns `list` list of retrieved words as tuples: (ID, WORD, POS SHORT NAME, POS FULL NAME)
    def get_words(self):
        return self.conn.cursor().execute(SQL_GET_WORDS)

    ## Retrieves all parts of speech from the database.
    # @returns `list` list of POS as tuples: (ID, POS SHORT NAME, POS FULL NAME)
    def get_pos(self):
        return self.conn.cursor().execute(SQL_GET_POS)

# ******************************************************************************** #

## Container for Qt signals used by HunspellDownloadTask.
class HunspellDownloadSignals(QtCore.QObject):

    ## Emitted before the download starts.
    # @param id `int` ID of task in the thread pool
    # @param url `str` URL of the downloaded file (dictionary)
    # @param lang `str` short language name for the dictionary (e.g. 'en', 'de')
    # @param filepath `str` full path to the downloaded dictionary (saved in pycross/assets/dic by default)
    sigStart = QtCore.pyqtSignal(int, str, str, str)
    ## Emitted when the target file size is received
    # @param id `int` ID of task in the thread pool
    # @param url `str` URL of the downloaded file (dictionary)
    # @param lang `str` short language name for the dictionary (e.g. 'en', 'de')
    # @param filepath `str` full path to the downloaded dictionary (saved in pycross/assets/dic by default)
    # @param total_bytes `int` length of file to be downloaded (in bytes) 
    sigGetFilesize = QtCore.pyqtSignal(int, str, str, str, int)
    ## Emitted during the download progress (for each kilobyte dowloaded).
    # @param id `int` ID of task in the thread pool
    # @param url `str` URL of the downloaded file (dictionary)
    # @param lang `str` short language name for the dictionary (e.g. 'en', 'de')
    # @param filepath `str` full path to the downloaded dictionary (saved in pycross/assets/dic by default)
    # @param bytes_written `int` number of bytes downloaded so far
    # @param total_bytes `int` length of file to be downloaded (in bytes)
    sigProgress = QtCore.pyqtSignal(int, str, str, str, int, int)
    ## Emitted when the download task completes.
    # @param id `int` ID of task in the thread pool
    # @param url `str` URL of the downloaded file (dictionary)
    # @param lang `str` short language name for the dictionary (e.g. 'en', 'de')
    # @param filepath `str` full path to the downloaded dictionary (saved in pycross/assets/dic by default)
    sigComplete = QtCore.pyqtSignal(int, str, str, str)
    ## Emitted when an exception occurs during the download.
    # @param id `int` ID of task in the thread pool
    # @param url `str` URL of the downloaded file (dictionary)
    # @param lang `str` short language name for the dictionary (e.g. 'en', 'de')
    # @param filepath `str` full path to the downloaded dictionary (saved in pycross/assets/dic by default)
    # @param message `str` the error message
    sigError = QtCore.pyqtSignal(int, str, str, str, str)

## A single download task to download one Hunspell dictionary from the remote repo
# and store it as a DIC file.
# Derived from QtCore.QRunnable so the task can be run in a thread pool 
# concurrently with other downloads.
class HunspellDownloadTask(QtCore.QRunnable):

    ## @param settings `dict` pointer to the app global settings (`utils::guisettings::CWSettings::settings`)
    # @param dicfolder `str` path to the target folder where to store the downloaded DIC file
    # @param url `str` URL of the DIC file to download (generally, https://raw.githubusercontent.com/wooorm/dictionaries/main/dictionaries/<LANG>/index.dic)
    # @param lang `str` short name of the language, e.g. 'en'
    # @param overwrite `bool` whether to overwrite the existing file (if any)
    # @param on_stopcheck `callback` callback function called periodically to check
    # for interrupt condition; takes 4 parameters:
    #   * id `int` unique ID of this task (in the thread pool)
    #   * url `str` URL of the DIC file to download
    #   * lang `str` short name of the language, e.g. 'en'
    #   * filepath `str` full path to the downloaded (target) file
    # Must return a Boolean value: `True` to stop the download task, `False` to continue
    # @param id `int` unique ID of this task (in the thread pool)
    def __init__(self, settings, dicfolder, url, lang, overwrite=True, on_stopcheck=None, id=0):
        super().__init__()
        ## `HunspellDownloadSignals` signals emitted by the download task
        self.signals = HunspellDownloadSignals()
        ## `str` path to the target folder where to store the downloaded DIC file
        self.dicfolder = dicfolder
        ## `str` URL of the DIC file to download (generally, https://raw.githubusercontent.com/wooorm/dictionaries/main/dictionaries/<LANG>/index.dic)
        self.url = url
        ## `str` short name of the language, e.g. 'en'
        self.lang = lang
        ## `bool` whether to overwrite the existing file (if any)
        self.overwrite = overwrite
        ## `int` unique ID of this task (in the thread pool)
        self.id = id
        ## `callback` callback function called periodically to check for interrupt condition
        self.on_stopcheck = on_stopcheck
        ## `int` timeout for HTTP(S) requests (in milliseconds)
        self.timeout_ = settings['common']['web']['req_timeout'] * 500
        ## `dict` HTTP(S) proxy server settings
        self.proxies_ = {'http': settings['common']['web']['proxy']['http'], 'https': settings['common']['web']['proxy']['https']} if not settings['common']['web']['proxy']['use_system'] else None

    ## Gets the file size (in bytes) of a given web resource by URL.
    # @param url `str` URL of the web resource (file)
    # @returns `int` file size in bytes (-1 on error)
    def get_filesize_url(self, url):
        try:
            site = urlopen(url)
            meta = site.info()
            return int(meta.get('Content-Length', -1))
        except:
            return -1

    ## Deletes a locally stored file (without raising errors on failure).
    # @param filepath `str` full path of the file to delete
    def _delete_file(self, filepath):
        try:
            os.remove(filepath)
        except:
            pass

    ## Overridden worker method called when the task is started: does the download job.
    def run(self):

        # make target file path from target folder and language short name
        filepath = os.path.join(self.dicfolder, f"{self.lang}.dic")
        # interrupt if requested
        if self.on_stopcheck and self.on_stopcheck(self.id, self.url, self.lang, filepath):
            return
        # emit OnStart signal
        self.signals.sigStart.emit(self.id, self.url, self.lang, filepath)

        # cancel if file exists and HunspellDownloadTask::overwrite == `False`
        if os.path.exists(filepath) and not self.overwrite:
            self.signals.sigComplete.emit(self.id, self.url, self.lang, filepath)
            return

        try:
            # get file size
            total_bytes = self.get_filesize_url(self.url)
            # emit OnGetFilesize signal
            self.signals.sigGetFilesize.emit(self.id, self.url, self.lang, filepath, total_bytes)

            # make download request
            with requests.get(self.url, stream=True, allow_redirects=True,
                            headers={'content-type': 'text/plain; charset=utf-8'},
                            timeout=self.timeout_, proxies=self.proxies_) as res:
                # received HTTP error, must cancel
                if not res or res.status_code != 200:
                    # emit OnError signal
                    self.signals.sigError.emit(self.id, self.url, self.lang, filepath,
                                            f"{getattr(res, 'text', 'HTTP error')} - status code {res.status_code}")
                    return
                try:
                    # create target file stream
                    with open(filepath, 'wb') as f:
                        # for every 1024 bytes...
                        for chunk in res.iter_content(1024):
                            # interrupt if requested
                            if self.on_stopcheck and self.on_stopcheck(self.id, self.url, self.lang, filepath):
                                f.close()
                                self._delete_file(filepath)
                                return
                            # write next kilobyte to file stream
                            f.write(chunk)
                            # emit OnProgress signal
                            self.signals.sigProgress.emit(self.id, self.url, self.lang, filepath, f.tell(), total_bytes)
                except Exception as err:
                    # on error, close file stream
                    f.close()
                    # emit OnError signal
                    self.signals.sigError.emit(self.id, self.url, self.lang, filepath, str(err))
                    # delete incomplete target file
                    self._delete_file(filepath)
                    return
                except:
                    f.close()
                    self._delete_file(filepath)
                    raise

        except Exception as err:
            # emit OnError signal
            self.signals.sigError.emit(self.id, self.url, self.lang, filepath, str(err))
            # delete incomplete target file
            self._delete_file(filepath)
            return

        except:
            # emit OnError signal
            self.signals.sigError.emit(self.id, self.url, self.lang, filepath, traceback.format_exc())
            # delete incomplete target file
            self._delete_file(filepath)
            return
        # emit OnComplete signal
        self.signals.sigComplete.emit(self.id, self.url, self.lang, filepath)

# ******************************************************************************** #

## Container for Qt signals used by HunspellImportTask.
class HunspellImportSignals(QtCore.QObject):

    ## Emitted before the import starts.
    # @param id `int` ID of task in the thread pool
    # @param lang `str` short language name for the dictionary (e.g. 'en', 'de')
    # @param filepath `str` full path to the downloaded dictionary (saved in pycross/assets/dic by default)
    sigStart = QtCore.pyqtSignal(int, str, str)
    ## Emitted when a next word is written to the database.
    # @param id `int` ID of task in the thread pool
    # @param lang `str` short language name for the dictionary (e.g. 'en', 'de')
    # @param filepath `str` full path to the downloaded dictionary (saved in pycross/assets/dic by default)
    # @param word `str` the word string, e.g. 'father'
    # @param pos `str` the word's part of speech, e.g. 'n' (=noun)
    # @param count `int` number of entries (words) written so far
    sigWordWritten = QtCore.pyqtSignal(int, str, str, str, str, int)
    ## Emitted when a commit is made to the database (by default, after each 1000 words).
    # @param id `int` ID of task in the thread pool
    # @param lang `str` short language name for the dictionary (e.g. 'en', 'de')
    # @param filepath `str` full path to the downloaded dictionary (saved in pycross/assets/dic by default)
    # @param count `int` number of entries (words) written so far
    sigCommit = QtCore.pyqtSignal(int, str, str, int)
    ## Emitted when the import task completes.
    # @param id `int` ID of task in the thread pool
    # @param lang `str` short language name for the dictionary (e.g. 'en', 'de')
    # @param filepath `str` full path to the downloaded dictionary (saved in pycross/assets/dic by default)
    # @param count `int` total number of entries (words) written
    sigComplete = QtCore.pyqtSignal(int, str, str, int)
    ## Emitted when an exception occurs during the import operation.
    # @param id `int` ID of task in the thread pool
    # @param lang `str` short language name for the dictionary (e.g. 'en', 'de')
    # @param filepath `str` full path to the downloaded dictionary (saved in pycross/assets/dic by default)
    # @param message `str` the error message
    sigError = QtCore.pyqtSignal(int, str, str, str)

## A single import task to import words from a DIC file (downloaded from the Hunspell repo)
# to an SQLite database *.db file.
# Derived from QtCore.QRunnable so the task can be run in a thread pool 
# concurrently with other tasks.
class HunspellImportTask(QtCore.QRunnable):

    ## @param lang `str` short name of the language, e.g. 'en'
    # @param dicfile `str` | `None` full path to the DIC file to import words from
    # (`None` means the default path will be assumed: pycross/assets/dic/<LANGUAGE>.dic)
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
    # @param replacements `dict` character replacement rules in the format:
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
    # @param rows `2-tuple` | `None` the start and end rows (indices) of the words to import;
    # e.g. (20, 100) means start import from row 20 and end import after row 100.
    # If the second element in the tuple is negative (e.g. -1), only the start row will
    # be considered and the import will go on till the last word in the source DIC file.
    # `None` means ALL available words.
    # @param commit_each `int` threshold of insert operations after which the transaction will be committed
    # (default = 1000)
    # @param on_stopcheck `callback` callback function called periodically to check
    # for interrupt condition; takes 3 parameters:
    #   * id `int` unique ID of this task (in the thread pool)
    #   * lang `str` short name of the language, e.g. 'en'
    #   * filepath `str` full path to the source DIC file
    # Must return a Boolean value: `True` to stop the import task, `False` to continue
    # @param id `int` unique ID of this task (in the thread pool)
    def __init__(self, lang, dicfile=None, posrules=None, posrules_strict=False,
                posdelim='/', lcase=True, replacements=None, remove_hyphens=True,
                filter_out=None, rows=None, commit_each=1000, on_stopcheck=None, id=0):
        super().__init__()
        ## `HunspellImportSignals` signals emiited by the import task
        self.signals = HunspellImportSignals()
        ## `str` short name of the language, e.g. 'en'
        self.lang = lang
        ## `str` | `None` full path to the DIC file to import words from
        self.dicfile = dicfile or os.path.join(DICFOLDER, f"{lang}.dic")
        ## `dict` part-of-speech regular expression parsing rules
        self.posrules = posrules
        ## `bool` import only the indicated or all parts of speech
        self.posrules_strict = posrules_strict
        ## `str` delimiter delimiting the word and its part of speech (default = '/')
        self.posdelim = posdelim
        ## `bool` import words in lower case
        self.lcase = lcase
        ## `dict` character replacement rules
        self.replacements = replacements
        ## `bool` remove all hyphens from words
        self.remove_hyphens = remove_hyphens
        ## `dict` regex-based rules to exclude words
        self.filter_out = filter_out
        ## `2-tuple` | `None` the start and end rows (indices) of the words to import
        self.rows = rows
        ##  `int` threshold of DB insert operations after which the changes are written to the DB
        self.commit_each = commit_each
        ## `callback` callback function called periodically to check for interrupt condition
        self.on_stopcheck = on_stopcheck
        ## `int` unique ID of this task (in the thread pool)
        self.id = id

    ## Deletes the existing DB file.
    # @param db `Sqlitedb` a single SQLite database to delete
    def _delete_db(self, db):
        try:
            db.disconnect()
            os.remove(db.dbpath)
        except:
            pass

    ## Retrieves the list of parts of speech present in the DB.
    # @param cur `SQLite cursor object` the DB cursor
    # @returns `list` parts of speech in the short form, e.g. ['N', 'V']
    def _get_pos(self, cur):
        return [res[0] for res in cur.execute(f"select {SQL_TABLES['pos']['fpos']} from {SQL_TABLES['pos']['table']}").fetchall()]

    ## Overridden worker method called when the task is started: does the import job.
    def run(self):

        # interrupt if requested
        if self.on_stopcheck and self.on_stopcheck(self.id, self.lang, self.dicfile):
            return
        # emit OnStart signal
        self.signals.sigStart.emit(self.id, self.lang, self.dicfile)

        # create `Sqlitedb` object
        db = Sqlitedb()
        # quit if cannot create DB
        if not db.setpath(self.lang):
            # emit OnError signal
            self.signals.sigError.emit(self.id, self.lang, self.dicfile, _('Unable to connect to database {}!').format(self.lang))
            return

        stopped = False
        # fetch the DB cursor
        cur = db.conn.cursor()
        # check correctness of parts of speech in HunspellImportTask::posrules
        if self.posrules:
            poses = self._get_pos(cur)
            for pos in self.posrules:
                if not pos in poses:
                    # emit OnError signal
                    self.signals.sigError.emit(self.id, self.lang, self.dicfile, _("Part of speech '{}' is absent from the DB!").format(pos))
                    # delete DB
                    self._delete_db(db)
                    return

        # imported word count
        cnt = 0
        try:
            # open file stream
            with codecs.open(self.dicfile, 'r', encoding=ENCODING, errors='ignore') as dic:
                # adjust iterator to match the start/end rows
                if not self.rows:
                    dic_iterate = dic
                else:
                    if self.rows[1] >= self.rows[0]:
                        dic_iterate = (row for i, row in enumerate(dic) if i in range(self.rows[0], self.rows[1] + 1))
                    else:
                        dic_iterate = (row for i, row in enumerate(dic) if i >= self.rows[0])
                # iterate rows (words)
                for row in dic_iterate:
                    row = row.strip()
                    #print(f"ROW = [{row}]")
                    # check stop request
                    if stopped or \
                            (self.on_stopcheck and \
                             self.on_stopcheck(self.id, self.lang, self.dicfile)):
                        stopped = True
                        break
                    # split the next row to extract the word and part-of-speech
                    w = row.split(self.posdelim)
                    # extract the word (convert to lowercase if specified)
                    word = w[0].lower() if self.lcase else w[0]
                    # extract POS (empty string if none)
                    pos = w[1] if len(w) > 1 else ''
                    # skip non-AZ words
                    #print(f"WORD = [{word}], POS = [{pos}]")
                    if not word.isalpha(): 
                        #print(f'{word}: NOT A-Z!')
                        continue
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

## Main interface to handle downloads and imports of Hunspell dictionaries as
# SQLite databases. Can start download and import tasks both in a synchonous mode
# (start and wait for completion) and asynchronously (in a thread pool).
class HunspellImport:

    ## @param settings `dict` pointer to the app global settings (`utils::guisettings::CWSettings::settings`)
    # @param dbmanager `Sqlitedb` | `None` DB object (`None` to create a new one)
    # @param dicfolder `str` root path of the dictionaries, default = utils::globalvars::DICFOLDER
    def __init__(self, settings, dbmanager=None, dicfolder=DICFOLDER):
        ## `dict` pointer to the app global settings (`utils::guisettings::CWSettings::settings`)
        self.settings = settings
        ## `Sqlitedb` | `None` DB object
        self.db = dbmanager or Sqlitedb()
        ## `str` root path of the dictionaries, default = utils::globalvars::DICFOLDER
        self.dicfolder = dicfolder
        ## `QtCore.QThreadPool` thread pool to run tasks
        self.pool = QtCore.QThreadPool()
        ## `int` timeout for HTTP(S) requests (in milliseconds)
        self.timeout_ = settings['common']['web']['req_timeout'] * 500
        ## `dict` HTTP(S) proxy server settings
        self.proxies_ = {'http': settings['common']['web']['proxy']['http'], 'https': settings['common']['web']['proxy']['https']} if not settings['common']['web']['proxy']['use_system'] else None

    ## Checks if there are tasks running in the pool.
    # @returns `bool` `True` if there are active tasks, `False` if none
    def pool_running(self):
        return bool(self.pool.activeThreadCount())

    ## Gets the number of active threads (tasks) in the pool.
    # @returns `int` number of active tasks
    def pool_threadcount(self):
        return self.pool.activeThreadCount()

    ## Waits for all the tasks in the pool to complete.
    def pool_wait(self):
        if self.pool_running():
            self.pool.waitForDone()

    ## Gets the information about an existing SQLite database: full path and number of words.
    # @param lang `str` short name of the language, e.g. 'en'
    # @returns `dict` info in the format:
    # @code {'entries': number_of_entries, 'path': full_path_to_DB_file} @endcode
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
    # @param stopcheck `callback` callback that returns `True` to stop the operation or
    # `False` to continue (takes no parameters)
    # @returns `list` list of dictionaries representing language-specific dictionary info:
    # <pre>
    #   * 'dic_url': URL of the dictionary file
    #   * 'lang': short language name, e.g. 'en' / 'ru' / 'it'
    #   * 'lang_full': full language name, e.g. 'Russian', 'English (US)'
    #   * 'license': name of applicable license, e.g. 'GPL-3.0' / 'MIT and BSD'
    #   * 'license_url': URL of applicable license file
    # </pre>
    def list_hunspell(self, stopcheck=None):
        readme = f"{HUNSPELL_REPO}/readme.md"
        dics = []
        try:
            res = requests.get(readme, allow_redirects=True, timeout=self.timeout_, proxies=self.proxies_)
            if not res: 
                return []
            if stopcheck and stopcheck(): 
                return []
            res = res.text        
            regex = re.compile(r'(\(dictionaries/[\w]+\))(\s*\|\s*)([\w\s]+)(\s*\|\s*)(\[.*?\])(\(.*?\))', re.I)
        
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
        except:
            return []
        return dics

    ## @brief Retrieves the information for all available Hunspell dictionaries.
    # Does everything what list_hunspell() does, but adds DB information (number of
    # entries and path to DB file) to each dictionary in the list.
    # @param stopcheck `callback` callback that returns `True` to stop the operation or
    # `False` to continue (takes no parameters)
    # @returns `list` list of dictionaries representing language-specific dictionary info:
    # <pre>
    #   * 'dic_url': URL of the dictionary file
    #   * 'lang': short language name, e.g. 'en' / 'ru' / 'it'
    #   * 'lang_full': full language name, e.g. 'Russian', 'English (US)'
    #   * 'license': name of applicable license, e.g. 'GPL-3.0' / 'MIT and BSD'
    #   * 'license_url': URL of applicable license file
    #   * 'entries': number of entries in the existing DB (0 if no DB exists or is empty)
    #   * 'path': full path to the existing DB file (empty string if no DB exists)
    # </pre>
    def list_all_dics(self, stopcheck=None):
        dics = self.list_hunspell(stopcheck)
        for dic in dics:
            info = self.get_installed_info(dic['lang'])
            if not info: info = {'entries': 0, 'path': ''}
            dic.update(info)
            if stopcheck and stopcheck(): return dics
        return dics

    ## Downloads a single Hunspell dictionary (*.dic file) and stores it locally.
    # @param url `str` URL of the DIC file to download (generally, https://raw.githubusercontent.com/wooorm/dictionaries/main/dictionaries/<LANG>/index.dic)
    # @param lang `str` short name of the language, e.g. 'en'
    # @param overwrite `bool` whether to overwrite the existing file (if any)
    # @param on_stopcheck `callback` callback function called periodically to check
    # for interrupt condition; takes 4 parameters:
    #   * id `int` unique ID of this task (in the thread pool)
    #   * url `str` URL of the DIC file to download
    #   * lang `str` short name of the language, e.g. 'en'
    #   * filepath `str` full path to the downloaded (target) file
    # @param on_start `callback` Qt slot (callback) for HunspellDownloadSignals::sigStart
    # @param on_getfilesize `callback` Qt slot (callback) for HunspellDownloadSignals::sigGetFilesize
    # @param on_progress `callback` Qt slot (callback) for HunspellDownloadSignals::sigProgress
    # @param on_complete `callback` Qt slot (callback) for HunspellDownloadSignals::sigComplete
    # @param on_error `callback` Qt slot (callback) for HunspellDownloadSignals::sigError
    # @param wait `bool` `True` to wait for the task to complete; `False` to start
    # the task asynchronously (without waiting for the result)
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

    ## @brief Downloads all the Hunspell dictionaries specified by the user.
    # The download tasks are started asynchronously in the thread pool,
    # each task using HunspellDownloadTask::signals to signalize its status
    # and check for interruption request.
    # @param dics `list` list of dict objects each representing a single Hunspell
    # dictionary, its URL, langugage, etc. See list_hunspell() for dict structure.
    # See other parameters in download_hunspell()
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

    ## @brief Imports a Hunspell-formatted dictionary file into the DB.
    # @param lang `str` short name of the imported dictionary language, e.g. 'en', 'de' etc.
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
    # @param replacements `dict` character replacement rules in the format:
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
    # @param rows `2-tuple` | `None` the start and end rows (indices) of the words to import;
    # e.g. (20, 100) means start import from row 20 and end import after row 100.
    # If the second element in the tuple is negative (e.g. -1), only the start row will
    # be considered and the import will go on till the last word in the source DIC file.
    # `None` means ALL available words.
    # @param commit_each `int` threshold of insert operations after which the transaction will be committed
    # (default = 1000)
    # @param on_checkstop `callback` callback function called periodically to check
    # for interrupt condition; takes 3 parameters:
    #   * id `int` unique ID of this task (in the thread pool)
    #   * lang `str` short name of the language, e.g. 'en'
    #   * filepath `str` full path to the source DIC file
    # Must return a Boolean value: `True` to stop the import task, `False` to continue
    # @param on_start `callback` Qt slot (callback) for HunspellImportSignals::sigStart
    # @param on_word `callback` Qt slot (callback) for HunspellImportSignals::sigWordWritten
    # @param on_commit `callback` Qt slot (callback) for HunspellImportSignals::sigCommit
    # @param on_finish `callback` Qt slot (callback) for HunspellImportSignals::sigComplete
    # @param on_error `callback` Qt slot (callback) for HunspellImportSignals::sigError
    # @param wait `bool` `True` to wait for the task to complete; `False` to start
    # the task asynchronously (without waiting for the result)
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

    ## @brief Imports all Hunspell dictionaries specified by the user.
    # The import tasks are started asynchronously in the thread pool,
    # each task using HunspelImportTask::signals to signalize its status
    # and check for interruption request.
    # @param dics `list` list of dict objects each representing a single Hunspell
    # dictionary, its URL, langugage, etc. See list_hunspell() for dict structure.
    # See other parameters in add_from_hunspell()
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
            self.pool.start(task)