# -*- coding: utf-8 -*-
"""
Created on Tue Oct  1 13:14:46 2019

@author: iskander.shafikov
"""

## ******************************************************************************** ##             

from utils.clibase import *
from crossword import Crossword, CWError
from wordsrc import DBWordsource, TextWordsource, TextfileWordsource
from dbapi import Sqlitedb
import traceback, re

## ******************************************************************************** ## 
                
class CLI(CLIBase):
    
    def __init__(self, splash=True):
        super().__init__()
        self.splash = splash
        self.db = None
        self.cw = None
        
    def __del__(self):
        if self.db: self.db.disconnect()
        
    #----- NON-COMMAND METHODS ------#
    
    def print_splash(self):
        with open('assets/splash', 'r') as f:
            print(COLOR_STRESS + f.read())
            
    def beforeRun(self):        
        super().beforeRun()
        try:
            if getattr(self, 'splash'): self.print_splash()
        except AttributeError:
            pass
        
    def beforeQuit(self):
        super().beforeQuit()
        print(COLOR_STRESS + 'QUITTING APP...')
        
    def grid_from_file(self, gridfile):
        """
        """
        cwgrid = []
        with open(gridfile, 'r', encoding=ENCODING) as file:
            for ln in file:
                s = ln
                if s.endswith('\n'): s = s[:-1]
                if s.endswith('\r'): s = s[:-1]
                if not s: break
                cwgrid.append(s)
            
        return cwgrid
    
    def set_data(self, data=None, dtype='grid'):
        if not self.cw: return
        if not data is None and dtype == 'grid':
            data = self.grid_from_file(data)
        self.cw.data_type = dtype
        self.cw.data = data
        self.cw.init_data()
    
    def set_word_source(self, src='en', maxres=MAX_RESULTS):
        if not self.cw: return
        if isinstance(src, str):
            src = src.lower()
            if src in LANG or src.endswith('.db'):
                if self.db: self.db.disconnect()
                self.db = Sqlitedb()
                if not self.db.setpath(src, fullpath=src.endswith('.db')): 
                    raise CWError(f"DB file '{src}' is unavailable!")
                src = DBWordsource(SQL_TABLES, self.db, max_fetch=maxres)
            else:
                if not os.path.isfile(src):
                    raise CWError(f"Text file '{src}' is unavailable!")
                src = TextfileWordsource(src, enc=ENCODING, max_fetch=maxres)
        elif isinstance(src, list):
            # assume a list of words
            src = TextWordsource(src, max_fetch=maxres)
        else:
            raise CWError("'src' argument must be a string (e.g. 'en', 'ru', or full file path) or a list of words!")
            
        self.cw.wordsource = src
        #print(self.cw.wordsource)
        
    def set_pos(self, pos='N'):
        if not self.cw: return
        if isinstance(pos, str) and ',' in pos:
            pos = [s.strip() for s in pos.split(',')]
        self.cw.pos = pos if (pos and pos != 'ALL') else None
        
    def on_dict_add(self, dicfile, lang, entries, total_entries):
        print(f"Added dictionary '{dicfile}', lang = {lang}, {entries} entries, total entries = {total_entries}")
        
    def on_commit(self, entries, dicfile):
        print(f"Wrote {entries} entires to database {dicfile}")
           
    #----- COMMAND METHODS ------#    
        
    def cmd_makedb(self, langs=None):
        """
        """
        db = Sqlitedb()
        try:
            if isinstance(langs, str):
                langs = [l.strip() for l in langs.split(',')]
            db.add_all_from_hunspell(langs, on_commit=self.on_commit, on_dict_add=self.on_dict_add)
        finally:
            if db: db.disconnect()
        
    def cmd_make(self, data=None, dtype='grid', pos='N', src='en', maxres=MAX_RESULTS, log=''):
        """
        """
        try:
            if not data is None and dtype == 'grid':
                data = self.grid_from_file(data) if isinstance(data, str) and os.path.isfile(data) else eval(data)
    
            if isinstance(src, str):
                src = src.lower()
                if src in LANG or src.endswith('.db'):
                    if self.db: self.db.disconnect()
                    self.db = Sqlitedb()
                    if not self.db.setpath(src, fullpath=src.endswith('.db')): 
                        raise CWError(f"DB file '{src}' is unavailable!")
                    src = DBWordsource(SQL_TABLES, self.db.conn, max_fetch=maxres)
                else:
                    if not os.path.isfile(src):
                        raise CWError(f"Text file '{src}' is unavailable!")
                    src = TextfileWordsource(src, enc=ENCODING, max_fetch=maxres)
            elif isinstance(src, list):
                # assume a list of words
                src = TextWordsource(src, max_fetch=maxres)
            else:
                raise CWError("'src' argument must be a string (e.g. 'en', 'ru', or full file path) or a list of words!")
            
            if isinstance(pos, str) and ',' in pos:
                pos = [s.strip() for s in pos.split(',')]
            
            if self.cw: self.cw.closelog()
            self.cw = Crossword(data=data, data_type=dtype, wordsource=src, wordfilter=None, pos=pos, log=log)
            print(self.cw) 
                
        except CWError:
            traceback.print_exc(limit=None)
            #print(COLOR_ERR + str(err))
            
        except Exception:
            traceback.print_exc(limit=None)
            #print(COLOR_ERR + str(err))
        
    def cmd_generate(self, method='', clear=False, timeout=60.0):
        """
        """
        try:
            if not self.cw:
                raise CWError("Crossword is not initialized! Execute 'm' command to make one first.")
    
            if clear: self.cmd_clear()
            
            if self.cw.generate(method, timeout):
                print(self.cw) 
                print(f"\n{self.cw.words.print_words()}")  
                #print(f"\n{self.cw.words.print_clues()}")
                
        except CWError:
            traceback.print_exc(limit=None)
            #print(COLOR_ERR + str(err))
            
        except Exception:
            traceback.print_exc(limit=None)
            #print(COLOR_ERR + str(err))
            
        finally:
            self.cw.closelog()
            
    def cmd_print(self):
        if not self.cw: 
            print(COLOR_ERR + 'No active crossword!')
            return
        
        print(self.cw)
        print(f"\n{self.cw.words.print_words()}")
        
    def cmd_clear(self):
        """
        Clears current crossword.
        """
        if self.cw: self.cw.clear()
            
    def cmd_edit(self):
        if not self.cw: 
            print(COLOR_ERR + 'No active crossword!')
            return
        
        print(self.cw) 
        regex = re.compile(r'(\(\s*\d+\s*,\s*\d+\s*\))(\s*)(h|v)')
        
        while True:
            print(COLOR_STRESS + '\nSelect editing option:')
            print(COLOR_STRESS + '1) cw parameters')
            print(COLOR_STRESS + '2) words')
            print(COLOR_STRESS + '3) clues')
            
            entered = str(input('Type option number or "w" to quit:\t')).lower()
            
            if not entered:
                print(EMPTY_CMD_MSG)
                continue
            
            if entered == '1':
                # edit cw params
                while True:
                    print(COLOR_STRESS + '\nSelect parameter to edit:')
                    print(COLOR_STRESS + '1) grid data')
                    print(COLOR_STRESS + '2) word sources')
                    print(COLOR_STRESS + '3) log output')
                    print(COLOR_STRESS + '4) part-of-speech filter')
                    
                    entered1 = str(input('Type option number or "w" to go to main menu:\t')).lower()
                    
                    if not entered1:
                        print(EMPTY_CMD_MSG)
                        continue
                    
                    if entered1 == '1':
                        # edit grid data
                        print(COLOR_STRESS + '\nSelect grid data type:')
                        print(COLOR_STRESS + '1) grid (string pattern)')
                        print(COLOR_STRESS + '2) file (e.g. xpf)')
                        print(COLOR_STRESS + f"Current value is: '{self.cw.data_type}'")
                        
                        entered11 = str(input('Type option number above, or RETURN to leave current, or "w" to go to main menu:\t')).lower()
                        
                        if entered11 and entered11 != 'w':
                            if entered11 == '1':
                                # data_type = grid
                                self.cw.data_type = 'grid'
                                entered111 = str(input('\nEnter grid or path to grid file:\n> '))
                                if os.path.isfile(entered111):
                                    self.cw.data = self.grid_from_file(entered111)
                                elif not entered111:
                                    print(COLOR_ERR + 'Wrong grid definition!')
                                    continue
                                else:
                                    grid = [entered111]
                                    while True:
                                        entered111 = str(input('> '))
                                        if not entered111: break
                                        grid.append(entered111)
                                    self.cw.data = grid
                                self.cw.init_data()                                    
                            elif entered11 == '2':
                                # data_type = file
                                self.cw.data_type = 'file'
                                entered111 = str(input('\nEnter file path:\t'))
                                if not os.path.isfile(entered111):
                                    print(COLOR_ERR + 'Unavailable file path!')
                                    continue
                                self.cw.data = entered111
                                self.cw.init_data()                            
                            else:
                                print(COLOR_ERR + 'Wrong command!')
                                continue 
                    
                    elif entered1 == '2':
                        # edit word sources
                        print(COLOR_STRESS + '\nEnter word source, one of:')
                        print(COLOR_STRESS + f"- language-specific database: {' or '.join(repr(k) for k in LANG)}")
                        print(COLOR_STRESS + '- full path to database (*.db) or text file (*.csv, *.txt, etc)')
                        print(COLOR_STRESS + '- comma-separated list of words, e.g. "room,mouse,dog,cat"')
                        print(COLOR_STRESS + 'Press RETURN or "w" to cancel.')
                        src = str(input('> ')).lower()
                        if src == 'w' or not src: continue
                        if ',' in src:
                            src = src.split(',')
                            
                        print(COLOR_STRESS + f"\nEnter max results threshold (current value = {self.cw.wordsource.max_fetch})")
                        print(COLOR_STRESS + f"Enter -1 to use no threshold limit, -2 to use the default value = {MAX_RESULTS}")
                        print(COLOR_STRESS + 'Press RETURN to use default value or "w" to cancel.')
                        max_res = str(input('> ')).lower()
                        if max_res == 'w': continue
                        if not max_res: max_res = MAX_RESULTS
                        else:
                            try:
                                max_res = int(max_res) 
                            except:
                                print(COLOR_ERR + 'Wrong value of "max_res" entered!')
                                continue
                        if max_res == -1:
                            max_res = None
                        elif max_res == -2:
                            max_res = MAX_RESULTS
                            
                        self.set_word_source(src, max_res)
                    
                    elif entered1 == '3':
                        # edit log output
                        print(COLOR_STRESS + '\nEnter log option, one of:')
                        print(COLOR_STRESS + '1) console (stdout)')
                        print(COLOR_STRESS + '2) console error (stderr)')
                        print(COLOR_STRESS + '3) file')
                        print(COLOR_STRESS + '4) none')
                        print(COLOR_STRESS + f"Current value is: '{self.cw._slog}'")
                        entered31 = str(input('Type option number above, or RETURN to leave current, or "w" to go to main menu:\t')).lower()
                        
                        if entered31 and entered31 != 'w':
                            if entered31 == '1':
                                self.cw.setlog('stdout')
                            elif entered31 == '2':
                                self.cw.setlog('stderr')
                            elif entered31 == '3':
                                fpath = str(input('\nEnter file path:\t')).lower()
                                self.cw.setlog(fpath)
                            elif entered31 == '4':
                                self.cw.setlog('')
                            else:
                                print(COLOR_ERR + 'Wrong command!')
                    
                    elif entered1 == '4':
                        # edit part-of-speech filter
                        print(COLOR_STRESS + '\nEnter part(s) of speech to use in search')
                        print(COLOR_STRESS + 'May be a single letter denoting a POS, e.g. "N" (noun) or a comma-separated list, e.g. "N,V" (nouns and verbs)')
                        print(COLOR_STRESS + f"Current value is: '{self.cw.pos}'")
                        print(COLOR_STRESS + 'Press RETURN to leave current, or "w" to go to main menu')
                        pos = input('> ')
                        if pos and pos != 'w':
                            self.set_pos(pos)
                    
                    elif entered1 == 'w':                        
                        break
                    
                    else:
                        print(COLOR_ERR + 'Wrong command!')
                        continue
            
            elif entered == '2':
                # edit words
                while True:
                     print(COLOR_STRESS + '\nEnter word coordinate and direction, e.g. "(1,3)h", "(0,5)v"')
                     print(COLOR_STRESS + 'Coordinates are in the format (column,row)')
                     print(COLOR_STRESS + 'Direction is one character: "h" = "horizontal" (across), "v" = "vertical" (down)')
                     print(COLOR_STRESS + 'Press "w" to stop editing.')
                     
                     sword = str(input('> ')).lower()
                     wd = None
                     
                     if sword == 'w':
                         break
                     
                     else:
                         m = regex.fullmatch(sword)
                         if not m:
                             print(COLOR_ERR + 'Wrong coordinate / direction passed!')
                             continue
                         wd = self.cw.words.find_by_coord_dir(eval(m[1]), m[3])
                         if not wd:
                             print(COLOR_ERR + 'Word not found!')
                             continue
                         
                     print(f"WORD = {self.cw.words.print_word(wd)}")
                         
                     print(COLOR_STRESS + '\nEnter new word string or "!" to clear word (use "_" to make blank character)')
                     print(COLOR_STRESS + 'Press "w" to go to main menu')

                     sword = str(input('> ')).lower()      
                     if sword == 'w':
                         break
                     elif sword == '!':
                         self.cw.clear_word(wd)
                         print(f"CLEARED WORD = {self.cw.words.print_word(wd)}")
                     else:
                         try:
                             self.cw.change_word(wd, sword)
                             print(f"CHANGED WORD = {self.cw.words.print_word(wd)}")
                         except Exception as err:
                             print(COLOR_ERR + str(err))
                             continue
                         
                print(self.cw)
            
            elif entered == '3':
                # edit clues
                print(COLOR_STRESS + '\nEnter clues for each word. Press RETURN to skip at any time, press "w" to quit.')
                for wd in self.cw.words.words:
                    print(f"\n{self.cw.words.print_word(wd)}\n\tCLUE = '{wd.clue}'")
                    clue = str(input('> '))
                    if not clue: continue
                    if clue == 'w': break
                    wd.clue = clue
                    
                print(self.cw.words.print_clues())
            
            elif entered == 'w':
                break
            
            else:
                print(COLOR_ERR + 'Wrong command!')
                continue
            
    def cmd_save(self, filename='cw.xpf', filetype='xpf'):
        if not self.cw: 
            print(COLOR_ERR + 'No active crossword!')
            return
        self.cw.words.to_file(filename, filetype)
            
    ## ------- Experimental / testing --------- ##
    def cmd_x(self, path_in, path_out):
        regex = re.compile('.*M.*')
        with open(path_in, 'r', encoding='utf-8') as fin:
            with open(path_out, 'w', encoding='utf-8') as fout:
                for row in fin:
                    w = row.split('/')
                    if len(w) > 1 and regex.match(w[1]):
                        fout.write(f"{w[0].lower()} N\n")
                       
            
## ******************************************************************************** ##             
    
def main():    
    fire.Fire(CLI, 'run')

## ******************************************************************************** ##    
       
if __name__ == '__main__':
    main()