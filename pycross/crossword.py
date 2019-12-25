# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

from utils import globalvars
import sys, os
import numpy as np
import timeit
from operator import itemgetter
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import json

## ******************************************************************************** ##

FILLER = '*'
FILLER2 = '~'
BLANK = '_'
DEFAULT_GRID = \
"""____*___*____
*_*_______*_*
*_*_*_*_*_*_*
*_**_____****
___**_*_**___
*_*********_*"""
LOG_INDENT = '\t'

## ******************************************************************************** ##

class CWError(Exception):
    pass

class CWTimeoutError(CWError):
    pass

class CWStopCheck(CWError):
    pass

## ******************************************************************************** ##

class MLStripper(HTMLParser):
    """
    Found solution here: https://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
    """
    
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
                
    def handle_data(self, d):
        self.fed.append(d)
        
    def get_data(self):
        return ''.join(self.fed)
    
    def strip(self, text):
        self.feed(text)
        return self.get_data()

## ******************************************************************************** ##
    
class Coords:
    
    def __init__(self, coord_start, coord_end):
        self.start = coord_start
        self.end = coord_end
        self.validate()
        
    def validate(self):
        if not isinstance(self.start, tuple) or not isinstance(self.end, tuple):
            raise CWError('Coords.start and Coords.end must be 2-tuples!')
        if len(self.start) != 2 or len(self.end) != 2:
            raise CWError('Coords.start and Coords.end must be 2-tuples!')
        if self.start[0] == self.end[0]:
            # vertical            
            if self.end[1] <= self.start[1]:
                raise CWError(f'End coordinate {repr(self.end)} must be greater than the start coordinate {repr(self.start)}!')
            self.dir = 'v'
        elif self.start[1] == self.end[1]:
            # horizontal
            if self.end[0] <= self.start[0]:
                raise CWError(f'End coordinate {repr(self.end)} must be greater than the start coordinate {repr(self.start)}!')
            self.dir = 'h'
        else:
            raise CWError('One coordinate must be equal!')
            
    def coord_array(self):
        if self.dir == 'h': 
            l = self.end[0] - self.start[0] + 1
            return [(i + self.start[0], self.start[1]) for i in range(l)]
        else:
            l = self.end[1] - self.start[1] + 1
            return [(self.start[0], i + self.start[1]) for i in range(l)]
        
    def does_cross(self, coord):
        for c in self.coord_array():
            if c == coord: 
                return True
        return False
    
    """
    def __eq__(self, other):
        return self.start == other.start and self.end == other.end and self.dir == other.dir
    """
        
    def __len__(self):
        cooord_index = 1 if self.dir == 'v' else 0
        return self.end[cooord_index] - self.start[cooord_index] + 1
    
    def __repr__(self):
        return f"Coords object :: start = {repr(self.start)}, end = {repr(self.end)}, dir = '{self.dir}'"

## ******************************************************************************** ##

class Word(Coords):
    
    def __init__(self, coord_start, coord_end, num=0, clue='', word=None):
        super().__init__(coord_start, coord_end)
        self.num = num
        self.clue = clue
        self.set_word(word)
        
    def set_word(self, wd):
        if not wd is None and len(wd) != len(self):
            raise CWError('Word length is not correct!')
        self.word = wd
        
    def __hash__(self):
        return hash((self.start, self.dir))
                
    def __repr__(self):
        return f"Word object :: num = {self.num}, start = {repr(self.start)}, end = {repr(self.end)}, dir = '{self.dir}'"
    
## ******************************************************************************** ## 
        
class CWInfo:
    
    def __init__(self, title='', author='', editor='', publisher='', cpyright='', date=''):
        self.title = title
        self.author = author
        self.editor = editor
        self.publisher = publisher
        self.cpyright = cpyright
        self.date = date

    def __str__(self):
        return '\n'.join((f"{key}='{value}'" for key, value in self.__dict__.items()))
    
## ******************************************************************************** ##
        
class Wordgrid:
    
    def __init__(self, data, data_type='grid', info=CWInfo(), 
                 on_reset=None, on_clear=None, on_change=None, 
                 on_clear_word=None, on_putchar=None):   
        """
        Constructor initializes the words and grid from the given grid data.
        """
        self.info = info
        self.on_reset = on_reset
        self.on_clear = on_clear
        self.on_change = on_change
        self.on_clear_word = on_clear_word
        self.on_putchar = on_putchar
        self.old_words = None
        self.initialize(data, data_type)
            
    def initialize(self, data, data_type='grid'):
        if data_type == 'grid':
            self.reset(data)
        elif data_type == 'words':
            self.from_words(data)
        elif data_type == 'file':            
            self.from_file(data)
        else:
            raise CWError(f"Wrong 'data_type' argument: '{data_type}'! Must be 'grid' OR 'words' OR 'file'!")
        
    def validate(self, grid):
        """
        Checks if the grid is appropriate:
            * must be a 'str' or 'list' type
            * must contain only a-z characters, BLANK, or FILLER, or FILLER2
        """
        if isinstance(grid, str):
            grid = grid.split('\n')
            if len(grid) < 2:
                raise CWError('Grid appears incorrect, for in contains less than 2 rows!')
                
        if isinstance(grid, list):
            for row in grid:
                if not all(c.isalpha() or c in (BLANK, FILLER, FILLER2) for c in row):
                    raise CWError(f"Grid contains invalid characters! Must contain only [a-z], '{BLANK}', '{FILLER}' and {FILLER2}.")
            return
        
        raise CWError('Grid must be passed either as a list of strings or a single string of rows delimited by new-line symbols!')                  
        
    def reset(self, grid=None, update_internal_strings=False):
        """
        Reconstructs the internal grid dimensions from the given
        grid pattern ('grid'). The following class members are fully re-initialized:
            * words (list of Word) - the collection of Word objects
            * grid (list of str) - the internal grid pattern OR the existing self.grid if == None
            * width (int) - the horizontal size (in cells)
            * height (int) - the vertical size (in cells)
        'update_internal_strings' tells the function to update each Word object's string representation
        """
        if grid is None and not getattr(self, 'grid', None): 
            raise CWError('Cannot call reset() on a null grid!')
            
        if not grid is None: 
            self.validate(grid)        
            if isinstance(grid, str): grid = grid.split('\n')
        
        # convert grid to 2D matrix
        grid = self.grid if grid is None and (not getattr(self, 'grid', None) is None) else [list(l.lower()) for l in grid]
        
        # validate characters
        for row in grid:
            for c in row:
                self._validate_char(c)
        
        # get number of rows
        lgrid = len(grid)   
        # initialize words list
        self.words = []
        
        # get get horizontal words
        grid_width = 0
        for y, row in enumerate(grid):
            lrow = len(row)
            c_start = None
            for x, char in enumerate(row):
                if char == FILLER or char == FILLER2:
                    if c_start and ((x - c_start[0]) > 1):
                        self.words.append(Word(c_start, (x - 1, y)))
                    c_start = None                   
                else:
                    if not c_start: c_start = (x, y)
            if c_start and ((lrow - c_start[0]) > 1):
                self.words.append(Word(c_start, (lrow - 1, y)))   
            if lrow > grid_width:
                grid_width = lrow
                
        # pad trailing fillers to make matrix even 2D
        for row in grid:
            row += [FILLER2] * (grid_width - len(row))
            
        # get vertical words
        for x in range(grid_width):
            c_start = None
            for y in range(lgrid):
                if grid[y][x] == FILLER or grid[y][x] == FILLER2:
                    if c_start and ((y - c_start[1]) > 1):
                        self.words.append(Word(c_start, (x, y - 1)))
                    c_start = None
                else:
                    if not c_start: c_start = (x, y)
            if c_start and ((lgrid - c_start[1]) > 1):
                self.words.append(Word(c_start, (x, lgrid - 1)))
        
        # set 'num' for each word (cw-type numeration)
        s_words = sorted(self.words, key=lambda w: (w.start[1], w.start[0]))
        n = 0        
        for i, w in enumerate(s_words):
            if i == 0 or w.start != s_words[i-1].start:
                n += 1
            w.num = n                
        
        # sort words using default sorting method
        self.sort()
        self.grid = grid
        self.width = grid_width
        self.height = lgrid  
        if update_internal_strings: self.update_word_strings()
        if self.on_reset: self.on_reset(self, self.grid)
        
    def from_words(self, words, update_internal_strings=False):
        """
        Constructs the internal grid, dimensions and words (with/without clues)
        from the given collection of Word objects ('words'). This is essentially
        the reverse of reset(), which constructs words from a given grid structure.
        """
        if not words or not hasattr(words, '__iter__') or not isinstance(words[0], Coords):
            raise CWError(f'"words" argument must be a non-empty collection of Word / Coords objects!')
            
        # calculate the grid dimensions
        width = max(words, key=lambda w: w.end[0]).end[0] + 1
        height = max(words, key=lambda w: w.end[1]).end[1] + 1
        #print(f"Dimensions = {width} x {height}")
        # make grid filled with FILLER characters
        grid = [[FILLER for c in range(width)] for r in range(height)]
        # list to hold coords of each character in each word in words
        coords = []   
        # accumulate coordinates
        for w in words: coords += w.coord_array()
        # sort coordinates by row, then column
        coords.sort(key=itemgetter(1, 0))
        # make blanks in grid for accumulated coords (to hold word characters)
        for (col, row) in coords:
            grid[row][col] = BLANK
        # squash rows into strings
        grid = [''.join(row) for row in grid]
        # reconstruct grid & words
        self.reset(grid)
        # finally, set words and clues, if any (deactivate on_change temporarily)
        old_callback = self.on_change
        self.on_change = None
        for w in self.words:
            for ww in words:
                if w.start == ww.start and w.dir == ww.dir and ww.word:
                    self.change_word(w, ww.word)
                    w.clue = ww.clue
                    break
        self.on_change = old_callback
        # update Word objects if necessary
        if update_internal_strings: self.update_word_strings()

    def grid_from_file(self, gridfile):
        """
        """
        cwgrid = []
        with open(gridfile, 'r', encoding=globalvars.ENCODING, errors='replace') as file:
            for ln in file:
                s = ln
                if s.endswith('\n'): s = s[:-1]
                if s.endswith('\r'): s = s[:-1]
                if not s: break
                cwgrid.append(s)            
        return cwgrid
        
    def from_file(self, filename, file_format=None):
        if file_format is None:
            file_format = os.path.splitext(filename)[1][1:].lower()

        if file_format == 'xpf':
            self._parse_xpf(filename)

        elif file_format == 'ipuz':
            self._parse_ipuz(filename)
            
        elif file_format == 'json':
            # assume JSON has list of Word objects
            with open(filename, 'r', encoding=globalvars.ENCODING, errors='replace') as infile:
                words = json.load(infile)
                self.from_words(words)

        else:
            # assume simple grid text file
            self.reset(self.grid_from_file(filename))
    
    def to_file(self, filename, file_format=None):
        if file_format is None:
            file_format = os.path.splitext(filename)[1][1:].lower()

        if file_format == 'xpf':
            self._save_xpf(filename)

        elif file_format == 'ipuz':
            self._save_ipuz(filename)

        elif file_format == 'json':
            with open(filename, 'w', encoding=globalvars.ENCODING) as outfile:
                json.dump(self.words, outfile, ensure_ascii=False, indent='\t')

        else:
            # save grid
            with open(filename, 'w', encoding=globalvars.ENCODING) as outfile:
                outfile.write(self.tostr())

    def _parse_ipuz(self, filename):

        def _get_char(el, default=BLANK):
            if isinstance(el, int):
               return BLANK
            elif isinstance(el, str):
                if el == '0': return BLANK
                elif el == '#': return FILLER
                elif el.lower() == 'null': return FILLER2
                else: return el.lower()
            elif isinstance(el, dict):
                return _get_char(el.get('cell', 0))
            return default

        ipuz = None
        with open(filename, 'r', encoding=globalvars.ENCODING, errors='replace') as infile:
            ipuz = json.load(infile)
        ipuz_kind = ''.join(ipuz.get('kind', ''))
        if not ipuz_kind: raise CWError(f"Unabe to parse '{filename}' as IPUZ file!")
        if not 'crossword' in ipuz_kind.lower(): return
        # get info
        self.info.title = ipuz.get('title', '')
        self.info.author = ipuz.get('author', '')
        self.info.editor = ipuz.get('editor', '')
        self.info.cpyright = ipuz.get('copyright', '')
        self.info.publisher = ipuz.get('publisher', '')
        self.info.date = ipuz.get('date', '')
        # get grid
        grid = ipuz.get('solution', None)
        if grid:            
            # first try the 'solutions' data
            grid = [''.join([_get_char(col) for col in row]) for row in grid]
        else:
            # if solutions is absent, try 'puzzle' data
            grid = ipuz.get('puzzle', None)
            # if both 'solutions' and 'puzzle' are absent, raise error
            if not grid: raise CWError(f"Unabe to parse '{filename}' as IPUZ file!")
            grid = [''.join([_get_char(col) for col in row]) for row in grid]
        # generate words & members
        self.reset(grid)
        # add clues
        clues = ipuz.get('clues', None)
        if not clues or not isinstance(clues, dict): return
        for k in clues:
            if not k in ('Across', 'Down'): continue
            for ipuz_w in clues[k]:
                w = self.find_by_num_dir(ipuz_w[0], 'h' if k == 'Across' else 'v')
                if w: w.clue = ipuz_w[1]

    def _save_ipuz(self, filename, ipuz_version='2', ipuz_kind='1'):
        ipuz = {'version': f"http://ipuz.org/v{ipuz_version}", 'kind': [f"http://ipuz.org/crossword#{ipuz_kind}"]}
        if self.info.title: ipuz['title'] = self.info.title
        if self.info.author: ipuz['author'] = self.info.author
        if self.info.editor: ipuz['editor'] = self.info.editor
        if self.info.cpyright: ipuz['copyright'] = self.info.cpyright
        if self.info.publisher: ipuz['publisher'] = self.info.publisher
        if self.info.date: ipuz['date'] = self.info.date
        ipuz['origin'] = f"{globalvars.APP_NAME} {globalvars.APP_VERSION}"
        ipuz['dimensions'] = {'width': self.width, 'height': self.height}
        ipuz['puzzle'] = [['#' if c == FILLER else ('null' if c == FILLER2 else 0) for c in row] for row in self.grid]
        ipuz['solution'] = [['#' if c == FILLER else ('null' if c == FILLER2 else c.upper()) for c in row] for row in self.grid]
        ipuz['clues'] = {'Across': [], 'Down': []}
        self.sort()
        for w in self.words:
            k = 'Across' if w.dir == 'h' else 'Down'
            ipuz['clues'][k].append([w.num, w.clue])

        with open(filename, 'w', encoding=globalvars.ENCODING) as outfile:
            json.dump(ipuz, outfile, ensure_ascii=False, indent='\t')
    
    def _parse_xpf(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        pz = root.find('Puzzle')
        if not pz:
            raise CWError(f"No puzzles in '{filename}'!")
        # get meta info
        title = pz.find('Title')
        self.info.title = title.text or '' if not title is None else ''
        author = pz.find('Author')
        self.info.author = author.text or '' if not author is None else ''
        editor = pz.find('Editor')
        self.info.editor = editor.text or '' if not editor is None else ''
        cpyright = pz.find('Copyright')
        self.info.cpyright = cpyright.text or '' if not cpyright is None else ''
        publisher = pz.find('Publisher')
        self.info.publisher = publisher.text or '' if not publisher is None else ''
        date = pz.find('Date')
        self.info.date = date.text or '' if not date is None else ''
        # make grid
        gr = pz.find('Grid')
        if not gr:
            raise CWError(f"No grid in '{filename}'!")
        grid = []
        for row in gr.iter('Row'):
            grid.append(row.text.lower().replace('.', FILLER).replace('~', FILLER2).replace(' ', BLANK))
        # generate words & members
        self.reset(grid)
        # add clues
        cl = pz.find('Clues')
        if not cl: return
        for clue in cl.iter('Clue'):
            coord = (clue.get('Col', None), clue.get('Row', None))
            if not coord[0] or not coord[1]: continue
            coord = (int(coord[0]) - 1, int(coord[1]) - 1)
            direction = clue.get('Dir', None)
            if not direction: continue
            direction = 'h' if direction == 'Across' else 'v'
            clue_str = self._strip_html(clue.text) 
            w = self.find_by_coord_dir(coord, direction)
            if w: w.clue = clue_str
            
    def _save_xpf(self, filename, xpf_version='1.0'):
        if not self.words: return
        root = ET.Element('Puzzles')
        root.set('Version', xpf_version)
        pz = ET.SubElement(root, 'Puzzle')
        ET.SubElement(pz, 'Title').text = self.info.title if self.info.title else ''
        ET.SubElement(pz, 'Author').text = self.info.author if self.info.author else ''
        ET.SubElement(pz, 'Editor').text = self.info.editor if self.info.editor else ''
        ET.SubElement(pz, 'Copyright').text = self.info.cpyright if self.info.cpyright else ''
        ET.SubElement(pz, 'Publisher').text = self.info.publisher if self.info.publisher else ''
        ET.SubElement(pz, 'Date').text = self.info.date if self.info.date else ''
        sz = ET.SubElement(pz, 'Size')
        ET.SubElement(sz, 'Rows').text = str(self.height)
        ET.SubElement(sz, 'Cols').text = str(self.width)
        gr = ET.SubElement(pz, 'Grid')
        for row in self.grid:
            ET.SubElement(gr, 'Row').text = ''.join(row).replace(BLANK, ' ').replace(FILLER, '.').replace(FILLER2, '~').upper()
        cl = ET.SubElement(pz, 'Clues')
        for w in self.words:
            clue = ET.SubElement(cl, 'Clue')
            clue.set('Row', str(w.start[1] + 1))
            clue.set('Col', str(w.start[0] + 1))
            clue.set('Num', str(w.num))
            clue.set('Dir', 'Across' if w.dir == 'h' else 'Down')
            clue.set('Ans', self.get_word_str(w).replace(BLANK, ' ').upper())
            clue.text = f"![CDATA[{w.clue}]]"
        tree = ET.ElementTree(root)
        tree.write(filename, encoding=globalvars.ENCODING, xml_declaration=True)
            
    def _strip_html(self, text):
        if text.startswith('![CDATA[') and text.endswith(']]'):
            text = text[8:-2]
        stripper = MLStripper()
        text = stripper.strip(text)
        return text
    
    def update_word_strings(self):
        """
        Updates the internal strings for each word in grid.
        """
        for w in self.words:
            w.set_word(self.get_word_str(w))
    
    def _validate_char(self, char):
        if not char.isalpha() and not char in (BLANK, FILLER, FILLER2):
            raise CWError(f'Character "{char}" is invalid!')
    
    def _validate_coord(self, coord):
        """
        Checks if the given coordinate lies within the grid range.
        Raises an error if out of range.
        """
        if coord[0] < 0 or coord[0] >= self.width or coord[1] < 0 or coord[1] >= self.height:
            raise CWError(f"Coordinate {repr(coord)} is out of the grid range (w={self.width}, h={self.height})!")
    
    def is_complete(self):
        """
        Checks if all the words are completed (have no blanks left).
        """
        for r in self.grid:
            if BLANK in r: return False
        return True

    def remove_row(self, row):
        """
        Removes the given row from grid. Use with care! Destroys word structure.
        """
        if row >= 0 and row < self.height:
            del self.grid[row]
            self.reset()

    def remove_column(self, col):
        """
        Removes the given column from grid. Use with care! Destroys word structure.
        """
        if col >= 0 and col < self.width:
            for row in self.grid:
                del row[col]
            self.reset()

    def add_row(self, index=-1, char=BLANK):
        """
        Inserts an empty row after the one given by 'index'.
        If index == -1, appends a row after the last one.
        'char' = fill character (default = BLANK).
        Use with care! Destroys word structure.
        """
        if index < 0 or index >= self.height:
            self.grid.append([char] * self.width)
        else:
            self.grid.insert(index, [char] * self.width)
        self.reset()

    def add_column(self, index=-1, char=BLANK):
        """
        Inserts an empty column after the one given by 'index'.
        If index == -1, appends a column after the last one.
        'char' = fill character (default = BLANK).
        Use with care! Destroys word structure.
        """
        for row in self.grid:
            if index < 0 or index >= self.width:
                row.append(char)
            else:
                row.insert(index, char)
        self.reset()

    def reflect_bottom(self, mirror=True, reverse=True, border=''):
        """
        Duplicates the current grid by reflecting its cells down.
        * If 'mirror' is True (default), reflection will be mirror-like
        (symmetrical against bottom line).
        * If 'reverse' is True (default), reflection will be inverted
        from left to right.
        * If both arguments are False, a simle copy-paste duplication will
        be performed.
        * If 'border' is an empty string (default), no extra row will be put
        between the existing and the new (reflected) cells.
        Otherwise, 'border' is a 2-character pattern for the extra row,
        e.g. '* ' means sequence of FILL and BLANK, '**' means all filled, etc.
        """
        last_row = len(self.grid)

        if border:
            sborder = border * (self.width // len(border))
            if len(sborder) < self.width:
                sborder += border
            sborder = sborder[:self.width]
            sborder = sborder.replace(' ', BLANK).replace('*', FILLER).replace('~', FILLER2)
            self.grid.append(list(sborder))

        to_insert = []
        for i in range(last_row):
            ls = [c if c in (BLANK, FILLER, FILLER2) else BLANK for c in self.grid[i]]
            to_insert.append(list(reversed(ls)) if reverse else ls)
        if mirror: to_insert.reverse()

        self.grid += to_insert
        self.reset()

    def reflect_top(self, mirror=True, reverse=True, border=''):
        """
        Duplicates the current grid by reflecting its cells up.
        See reflect_bottom() for description of arguments.
        """
        first_row = 0
        
        if border:
            sborder = border * (self.width // len(border))
            if len(sborder) < self.width:
                sborder += border
            sborder = sborder[:self.width]
            sborder = sborder.replace(' ', BLANK).replace('*', FILLER).replace('~', FILLER2)
            self.grid.insert(0, list(sborder))
            first_row = 1

        last_row = len(self.grid)
        to_insert = []
        for i in range(first_row, last_row):
            ls = [c if c in (BLANK, FILLER, FILLER2) else BLANK for c in self.grid[i]]
            to_insert.append(list(reversed(ls)) if reverse else ls)
        if mirror: to_insert.reverse()

        self.grid[0:0] = to_insert
        self.reset()

    def reflect_right(self, mirror=True, reverse=True, border=''):
        """
        Duplicates the current grid by reflecting its cells right.
        See reflect_bottom() for description of arguments.
        """
        self.height = len(self.grid)
        last_col = self.width - 1

        if border:
            sborder = border * (self.height // len(border))
            if len(sborder) < self.height:
                sborder += border
            sborder = sborder[:self.height]
            sborder = sborder.replace(' ', BLANK).replace('*', FILLER).replace('~', FILLER2)
            for i in range(self.height):
                self.grid[i].append(sborder[i])

        if not reverse:
            for row in self.grid:
                ls = [c if c in (BLANK, FILLER, FILLER2) else BLANK for c in row[:last_col]]
                if mirror: ls.reverse()
                row += ls
        else:
            for row in reversed(self.grid):
                ls = [c if c in (BLANK, FILLER, FILLER2) else BLANK for c in row[:last_col]]
                if mirror: ls.reverse()
                row += ls

        self.reset()

    def reflect_left(self, mirror=True, reverse=True, border=''):
        """
        Duplicates the current grid by reflecting its cells left.
        See reflect_bottom() for description of arguments.
        """
        self.height = len(self.grid)
        first_col = 0

        if border:
            sborder = border * (self.height // len(border))
            if len(sborder) < self.height:
                sborder += border
            sborder = sborder[:self.height]
            sborder = sborder.replace(' ', BLANK).replace('*', FILLER).replace('~', FILLER2)
            for i in range(self.height):
                self.grid[i].insert(0, sborder[i])
            first_col = 1

        if not reverse:
            for row in self.grid:
                ls = [c if c in (BLANK, FILLER, FILLER2) else BLANK for c in row[first_col:]]
                if mirror: ls.reverse()
                row[0:0] = ls
        else:
            for row in reversed(self.grid):
                ls = [c if c in (BLANK, FILLER, FILLER2) else BLANK for c in row[first_col:]]
                if mirror: ls.reverse()
                row[0:0] = ls

        self.reset()

    def reflect(self, direction='d', mirror=True, reverse=True, border=''):
        """
        Combined method for 'reflect_...' methods above.
        """
        d = direction[-1].lower()
        if d == 'd':
            self.reflect_bottom(mirror, reverse, border)
        elif d == 'u':
            self.reflect_top(mirror, reverse, border)
        elif d == 'r':
            self.reflect_right(mirror, reverse, border)
        elif d == 'l':
            self.reflect_left(mirror, reverse, border)
    
    def intersects_of(self, word, word_coord_tuples=True):
        """
        Finds all words intersecting the given word.
        """
        index1 = 0 if word.dir == 'h' else 1
        index2 = 0 if index1 else 1
        intersects = []
        for w in self.words:
            if w.dir != word.dir and \
               w.start[index1] >= word.start[index1] and w.start[index1] <= word.end[index1] and \
               w.start[index2] <= word.start[index2] and w.end[index2] >= word.end[index2]:
                if word_coord_tuples:
                    intersects.append((w, (w.start[0], word.start[1]) if word.dir == 'h' else (word.start[0], w.start[1])))  
                else:
                    intersects.append(w)
        return intersects
    
    def find_incomplete(self, method='most-complete', exclude=None):
        """
        Retrieves a next incomplete word (fully or partially blank).
        The 'method' argument (str) governs the search algorithm; it can be one of:
            - 'first-incomplete' (default): the first incomplete word will be returned
            - 'most-complete': the first word having the least blanks will be returned
            - 'most-incomplete': the first word having the most blanks will be returned (i.e. fully blank word)
            - 'random': a random incomplete word will be returned
        The 'exclude' argument (callable) allows excluding words from search.
        It accepts a single argument - a Word object, and returns True to exclude and False otherwise.
        """
        word = (None, 0)
        words = []
        for w in self.words:
            if exclude and exclude(w): continue
            blanks = 0
            for coord in w.coord_array():
                if self.grid[coord[1]][coord[0]] == BLANK:
                    if method == 'first-incomplete':                        
                        return w
                    elif method == 'most-complete' or method == 'most-incomplete':
                        blanks += 1
                    elif method == 'random':
                        words.append(w)
                        break
            if blanks and (word[0] is None or 
                (method == 'most-complete' and blanks < word[1]) or 
                (method == 'most-incomplete' and blanks > word[1])):
                word = (w, blanks)
                
        if method == 'most-complete' or method == 'most-incomplete':
            return word[0]
        elif method == 'random' and words:
            np.random.seed()
            return np.random.choice(words)
                
        return None
    
    def count_incomplete(self):
        c = 0
        for w in self.words:
            if not self.is_word_complete(w):
                c += 1
        return c
    
    def get_word_str(self, w):
        if not w in self.words: 
            raise CWError(f"Word '{str(w)}' is absent from grid!")
        return ''.join(self.grid[coord[1]][coord[0]] for coord in w.coord_array())
    
    def is_word_complete(self, w):
        if not w in self.words: 
            raise CWError(f"Word '{str(w)}' is absent from grid!")
        for coord in w.coord_array():
            if self.grid[coord[1]][coord[0]] == BLANK:
                return False
        return True
    
    def is_word_blank(self, w):
        return self.get_word_str(w) == BLANK * len(w)
    
    def find(self, word):
        for w in self.words:
            if w == word:
                return w
        return None
    
    def find_by_coord(self, coord, start_coord=True):
        found = {'h': None, 'v': None}
        for w in self.words:
            if start_coord:
                if w.start == coord:
                    found[w.dir] = w
            elif w.does_cross(coord):
                found[w.dir] = w
        return found
    
    def find_by_coord_dir(self, coord, direction):
        for w in self.words:
            if w.start == coord and w.dir == direction:
                return w
        return None
    
    def find_by_str(self, str_word):
        for w in self.words:
            if self.get_word_str(w) == str_word:
                return w
        return None
    
    def find_by_num_dir(self, num, direction):
        #self.sort()
        for w in self.words:
            if w.num == num and w.dir == direction: return w
        return None
    
    def find_by_clue(self, clue):
        for w in self.words:
            if w.clue == clue: return w
        return None
    
    def get_char(self, coord):
        self._validate_coord(coord)
        return self.grid[coord[1]][coord[0]]
        
    def put_char(self, coord, char):
        old_char = self.get_char(coord)
        new_char = char.lower()
        self._validate_char(new_char)
        self.grid[coord[1]][coord[0]] = new_char
        if self.on_putchar: self.on_putchar(self, coord, old_char, new_char)

    def clear(self):
        """
        Clears all the words in the collection.
        """
        for y in range(self.height):
            for x in range(self.width):
                if not self.grid[y][x] in (FILLER, FILLER2):
                    self.grid[y][x] = BLANK
        if self.on_clear: self.on_clear(self)
            
    def change_word(self, word, new_word: str):        
        """
        Replaces the given word (word) with another string (new_word).
        """
        if not word in self.words: 
            raise CWError(f"Word '{str(word)}' is absent from grid!")
        if len(new_word) != len(word):
            raise CWError("Lengths of words do not match!")
        if self.on_change: w_old = self.get_word_str(word)
        for i, coord in enumerate(word.coord_array()):
            self.put_char(coord, new_word[i])
        #self.update_word_strings()
        if self.on_change: self.on_change(self, word, w_old)
            
    def clear_word(self, word, force_clear=False):
        if self.is_word_blank(word): return
        if self.on_clear_word: w_old = self.get_word_str(word)
        coord_array = word.coord_array()
        if not force_clear:
            intersects = self.intersects_of(word)
            for cross in intersects:
                if cross[1] in coord_array and self.is_word_complete(cross[0]):
                    coord_array.remove(cross[1])
        for coord in coord_array:
            self.put_char(coord, BLANK)    
        #self.update_word_strings()
        if self.on_clear_word: self.on_clear_word(self, word, w_old)
            
    def sort(self):
        """
        Sorts the words collection (list) by the word coordinates in the 
        assending order: first on rows, then on columns.
        """
        if getattr(self, 'words', None):
            self.words.sort(key=lambda word: (word.dir, word.num))
    
    def print_word(self, w):
        if not w in self.words:
            raise CWError(f"Word '{str(w)}' is absent from grid!")
        return f"{repr(w.start)} {w.dir} '{self.get_word_str(w)}'"

    def print_words(self):
        #self.sort()
        s = f"Num{LOG_INDENT}Coord{LOG_INDENT * 2}Value\n-------------------------------------------\n"
        s += 'ACROSS:\n-------------------------------------------\n'
        s += '\n'.join(f"[{w.num}]{LOG_INDENT}{repr(w.start)}{LOG_INDENT * 2}'{self.get_word_str(w)}'" for w in self.words if w.dir == 'h')   
        s += '\n-------------------------------------------\nDOWN:\n-------------------------------------------\n'
        s += '\n'.join(f"[{w.num}]{LOG_INDENT}{repr(w.start)}{LOG_INDENT * 2}'{self.get_word_str(w)}'" for w in self.words if w.dir == 'v') 
        return s
           
    def print_clues(self):
        return '\n'.join(f"[{w.num}]{LOG_INDENT}{w.dir}{LOG_INDENT * 2}{w.clue}" for w in self.words)
    
    def word_list(self, strings=True):
        return [self.get_word_str(w) if strings else w for w in self.words]
    
    def tostr(self):
        return '\n'.join([''.join(row) for row in self.grid]) if self.grid else ''

    def _cell_count(self, condition=None):
        """
        Return number of blocked cells (FILLER, FILLER2).
        """
        c = 0
        for y in range(self.height):
            for x in range(self.width):
                if (condition is None) or (condition(y, x) == True):
                    c += 1
        return c

    def _word_count(self, condition=None):
        c = 0
        for w in self.words:
            if (condition is None) or (condition(w) == True):
                c += 1
        return c
    
    def _word_lengths(self):
        """
        Return an array of word lengths.
        """
        return [len(w) for w in self.words]

    def update_stats(self):
        """
        Updates self.stats dict with current handy statistics.
        """
        self.stats = {}
        self.stats['grid_width'] = self.width
        self.stats['grid_height'] = self.height
        self.stats['cell_count'] = self.height * self.width
        self.stats['filler_cell_count'] = self._cell_count(lambda r, c: self.grid[r][c] in (FILLER, FILLER2))
        self.stats['word_count'] = len(self.words)
        self.stats['complete_word_count'] = self._word_count(self.is_word_complete)
        self.stats['blank_word_count'] = self._word_count(self.is_word_blank)
        self.stats['across_word_count'] = self._word_count(lambda w: w.dir == 'h')
        self.stats['down_word_count'] = self.stats['word_count'] - self.stats['across_word_count']
        wls = self._word_lengths()
        self.stats['word_lengths'] = wls
        self.stats['mean_word_length'] = np.mean(wls)
        self.stats['min_word_length'] = min(wls)
        self.stats['max_word_length'] = max(wls)
        self.stats['withclues_word_count'] = self._word_count(lambda w: bool(w.clue))       

    def save(self):
        """
        Saves all words to self.old_words to be able to restore later.
        """        
        self.update_word_strings()
        self.old_words = self.words[:]

    def restore(self):
        """
        Restores words from self.old_words.
        """
        if not self.old_words is None:
            self.from_words(self.old_words)
    
    def __contains__(self, word):
        """
        The 'in' operator overload: checks if words contain a given word.
        """  
        if isinstance(word, str):            
            word = word.lower() 
        elif not isinstance(word, Word):
            raise CWError('Word must be a Word object!') 
        for w in self.words:
            if (isinstance(word, Word) and w == word) or (isinstance(word, str) and self.get_word_str(w) == word):
                return True            
        return False
    
    def __bool__(self):
        """
        Convenience for is_complete().
        """
        return self.is_complete()
    
    def __len__(self):
        return len(self.words)
    
    def __str__(self):
        """
        The 'str' convertion overload: represents a pretty output of the grid.
        """        
        # print horizontal coordinates
        s = ' ' * 5 + ''.join([str(c).rjust(4, ' ') for c in range(self.width)])
        # print top border         
        s += '\n' + ' ' * 5 + ' ___' * self.width
        # print rows
        for n, row in enumerate(self.grid):
            # vertical coord
            s += '\n' + str(n).rjust(3, ' ') + ' '
            # row chars
            s += ' | ' + ' | '.join(row) + ' |'
            # horizontal line
            s += '\n' + ' ' * 5 + ' ---' * self.width
        return s
            
        
## ******************************************************************************** ##

class Crossword:
    
    def __init__(self, data=None, data_type='grid', wordsource=None, wordfilter=None, 
                 pos='N', log='stdout', bufferedlog=False, **kwargs):
        """
        Initializes Crossword members.
        ARGS:
            * grid (str | list): CW grid
            * wordsource (Wordsource): source of words to use in generation (see wordsrc.py)
            * wordfilter (callable): word filtering function used in suggest() -- may be None if no filtering is required
            * pos (str | list | tuple): word part-of-speech filter: 
                can be a list/tuple (e.g. ['N', 'V']), a single str, e.g. 'N';
                the value of 'ALL' or None means no part-of-speech filter 
            * log (str): stream or file path to output debugging info (log messages); may be one of:
                'stdout' (default): current console stream
                'stderr': error console stream
                file path: path to output (text) file
                '' or None: no logging will be made
            * bufferedlog (bool): whether the log should be buffered (written on disk only on destruction)
                or not buffered (default), when log messages will be written immediately
            * kwargs: additional args passed to Wordgrid constructor, like:
                info, on_reset, on_clear, on_change, on_clear_word, on_putchar etc. 
        """
        self.data = DEFAULT_GRID if (data is None and data_type == 'grid') else data
        self.data_type = data_type
        # set of used words (to rule out duplicate words in CW)
        self.used = set()
        # Wordgrid
        self.init_data(**kwargs)
        self.wordsource = wordsource
        self.wordfilter = wordfilter
        self.pos = pos if (pos and pos != 'ALL') else None
        self.bufferedlog = bufferedlog        
        # initialize log stream (if set)
        self.setlog(log)
        
    def __del__(self):
        """
        Destructor flushes and closes log file (if present).
        """
        self.closelog()
        
    def init_data(self, **kwargs):
        self.words = Wordgrid(data=self.data, data_type=self.data_type, **kwargs)
        self.reset_used()
        self.time_start = timeit.default_timer()
            
    def setlog(self, log=''):
        """
        Initializes self.log to point to the relevant output stream as given by 'log' arg:
            'stdout' (default): current console stream
            'stderr': error console stream
            file path: path to output (text) file
            '' or None: no logging will be made
        """
        self._slog = log
        self.closelog()
        if log == 'stdout':
            self.log = sys.stdout
        elif log == 'stderr':
            self.log = sys.stderr
        elif log == '' or log is None:
            self.log = None
        else:
            self.log = open(log, 'w', encoding=globalvars.ENCODING, buffering=-1 if self.bufferedlog else 1)        
            
    def _log(self, what, end='\n'):
        """
        Prints debug/log message ('what') to self.log with optional line-ending char ('end').
        """
        try:
            if self.log: print(what, file=self.log, end=end)
        except:
            self.setlog(self._slog)
            if self.log: print(what, file=self.log, end=end)
            
    def change_word(self, word, new_word):
        if not hasattr(self, 'words'): return
        self.used.discard(self.words.get_word_str(word))
        crosses = self.words.intersects_of(word, False)
        for w in crosses:
            self.used.discard(self.words.get_word_str(w))
        self.words.change_word(word, new_word)
        self.used.add(self.words.get_word_str(word))
        
    def clear_word(self, word, force_clear=False):
        if not hasattr(self, 'words'): return
        self.used.discard(self.words.get_word_str(word))
        crosses = self.words.intersects_of(word, False)
        for w in crosses:
            self.used.discard(self.words.get_word_str(w))
        self.words.clear_word(word, force_clear)
        
    def clear(self):
        """
        """
        # clear USED list
        self.used.clear()
        # clear cw grid
        self.words.clear()

    def print_used(self):
        """
        Prints all words currently contained in USED list.
        """
        for wstr in self.used:
            print(wstr)
            
    def closelog(self):
        """
        Flushes and closes self.log (stream) if it points to a file.
        """
        if getattr(self, 'log', None) and self.log != sys.stdout and self.log != sys.stderr:
            self.log.close()
            
    def add_completed(self):
        """
        Updates the USED list adding the completed (pre-set) words.
        """
        for w in self.words.words:
            if self.words.is_word_complete(w):
                self.used.add(self.words.get_word_str(w))

    def reset_used(self):
        self.used.clear()
        self.add_completed()
        #self.print_used()
        
    def suggest(self, word):
        """
        Fetches suggestions for the given word from the datasets,
        honoring the corresponding rules / filters and excluding items
        from the USED list.
        """
        # define filtering function 
        def filt(sug):
            # check if word is not in USED list
            not_in_used = not sug in self.used
            # combine that with custom self.wordfilter function, if set
            return (not_in_used and self.wordfilter(sug)) if self.wordfilter else not_in_used
        
        # get suggestions (list) from word source
        return self.wordsource.fetch(word, BLANK, self.pos, filt)
    
    def make_path(self, start_word=None, path=[], recurse=0, chain_paths=False, word_filter=None):
        """
        Function that creates a sequential generation path, 
        i.e. list of words to fill forming a connected graph (all words in path
        are connected through intersections).
        Algorithm starts from first non-complete word (with one or more blanks),
        then recursively adds each intersecring word using DFS (depth-first search).
        The resulting path contains all the words in the CW if chain_paths == True,
        or a single connected graph (list) of words if chain_paths == False.
        ARGS:
            * start_word (Word): the initial word from which generation will start;
              if None, the first incomplete word will be taken
            * path (list): pointer to the list of words forming the path (will be 
              updated by the function)
            * recurse (int): the current recursion depth (position on stack);
              this arg must be zero when starting path generation; each recursive call
              will increment it and each return will decrement it
            * chain_paths (bool): whether to merge all word graphs together into one path (==True),
              or make one connected path starting from start_word (==False).
              In essence, setting this arg to False (default) may be useful when
              generating CW block-wise, where each graph (block of words)
              is not connected with the others by intersections. In this case,
              concurrent generation might be used.
            * word_filter (callable): filter function to exclude words from search tree
        """
        def filter_out(w):
            return (w in path) or (self.words.get_word_str(w) in self.used) or (word_filter(w) if word_filter else False)
        
        # if start_word is None or path is empty, find the first incomplete word in CW
        # passing path and exclude lists to the search function to skip already added words
        if (start_word is None) or not path:
            start_word = self.words.find_incomplete(method='most-complete', exclude=filter_out)
            
        # if not found, quit function (there are no more incomplete words in CW)
        if start_word is None or filter_out(start_word): 
            return
        
        # save current recursion depth
        rec = recurse     
        # add start_word to path
        path.append(start_word)
            
        # find intersecting words (pass False to intersects_of() to return just a list of words)
        crosses = self.words.intersects_of(start_word, False)
        # for each intersect
        for w in crosses:
            # if next intersect has blanks
            if not self.words.get_word_str(w) in self.used:
                # increment recursion depth
                rec += 1
                # recursively call make_path() with current intersect as start_word
                self.make_path(w, path, rec, chain_paths, word_filter)
                # decrement recursion depth
                rec -= 1
                
        # if on zero recursion depth and chain_paths == True, add a next path to path
        if chain_paths and rec == 0 and len(path) < (len(self.words) - len(self.used)):
            self.make_path(None, path, rec, chain_paths, word_filter)
            
    def generate_iter(self, timeout=None, stopcheck=None):
        """
        Generates crossword using the iterative algorithm.
        RETURNS:
            True on success (all words in CW are filled) and False otherwise
            
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        !!! IMPORTANT NOTICE !!!
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        Currently the iterative algo does a good job ONLY for fully blank word grids.
        For partically filled grids, it will generate INCORRECT words, since
        the traversal path is generated STATICALLY only once and is not
        amended during word generation. The path exludes all words in USED list,
        so the algo will fit words without checking how they intersect with existing
        (used) words in the grid. While this caveat will be dealt with later,
        prefer the Recursive algo for word grids with some words filled.
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        """ 
        
        # if CW complete, return True
        if self.words: 
            self._log(f"\n\tCompleted CW!")
            return True
        
        self._log('Creating word paths...')
        
        # list to hold word paths (where each path is again a list)
        paths = []
        # list to hold ALL words to be excluded from path generation
        exclude = []
        # exclude must ultimately contain all words not found in USED list, so...
        fillable_count = len(self.words) - len(self.used)
        
        # generate paths until 'exclude' holds ALL incomplete words in CW:
        while len(exclude) < fillable_count:
            # generate a next path
            path = []
            self.make_path(start_word=None, path=path, word_filter=lambda w: w in exclude)
            # merge it into exclude (to pass into following generation cycles)
            exclude += path
            # add path to paths, converting each element into a dict with 2 elements:
            # 'w': the word in path; and 'sug': suggestions from word source
            paths.append([{'w': w, 'sug': None} for w in path])
            # check timeout
            if self.timeout_happened(timeout): raise CWTimeoutError()
            
        #print('\n'.join(str(w) for w in exclude))
        
        self._log(f"Created {len(paths)} paths")
        
        # this list will contain Boolean generation results for each path (block of words)
        results = []
        
        # loop for each path in paths (if CW is fully connected, there will be just one loop cycle)
        for p in paths:
            # generation result
            res = True
            # store path length
            lpath = len(p)
            i = 0
            # step through path (until 'i' reaches its end index)
            # (while is preferred over for here since we'll be changing the 'i' value dynamically)
            while i < lpath:
                
                # check timeout
                if self.timeout_happened(timeout): raise CWTimeoutError()
                # check for stopping criteria
                if stopcheck and stopcheck(): raise CWStopCheck()
                
                if self.log: 
                    self._log(f"\n{str(self.words)}\n")                
                    self._log(f"\nNext word = [{self.words.print_word(p[i]['w'])}]")
                    
                # get string representation of next word in path
                s_word = self.words.get_word_str(p[i]['w'])
                
                # skip word if it's already in USED list
                if s_word in self.used: 
                    self._log(f"Skipping [{s_word}] (found in USED)...")
                    i += 1
                    continue
                
                # get new suggestions from word source if 'sug' is None
                if p[i]['sug'] is None:                    
                    p[i]['sug'] = self.suggest(s_word) 
                    self._log(f"Fetched {len(p[i]['sug'])} suggestions for [{s_word}]")
                    
                # check timeout
                if self.timeout_happened(timeout): raise CWTimeoutError()
                # check for stopping criteria
                if stopcheck and stopcheck(): raise CWStopCheck()
                    
                # if suggestions returned an empty list (means we can't go on with generation)
                if len(p[i]['sug']) == 0:
                    
                    self._log(f"No suggestions for [{s_word}]!")
                    # reset 'sug' list to None (to possibly re-generate on next step)
                    p[i]['sug'] = None
                    self._log(f"Clearing [{s_word}]...", end='')
                    # clear word forcibly, i.e. set ALL characters to BLANK
                    # (this word is unusable as it is, so we must clear it thoroughly)
                    # at the same time, discard word and its intersects from USED list
                    self.clear_word(p[i]['w'], True)
                    
                    # now we must look if we're already some steps forward through the path
                    # or are at the first word, to see if we must go back and use some
                    # other suggestions for previous words, and then re-generate the current one
                    
                    # if we CAN go back
                    if i > 0:
                        
                        # determine all intersects of the current (failed) word --
                        # we have to clear these intersects (aka 'parents'), or they will reproduce the
                        # failed suggestion over and over again...
                        crosses = self.words.intersects_of(p[i]['w'], False)
                        # if intersects are found
                        if crosses:
                            j = -1
                            # loop through current path again to see which words are intersecting this one
                            for k, wd in enumerate(p):
                                # check timeout
                                if self.timeout_happened(timeout): raise CWTimeoutError()
                                # check for stopping criteria
                                if stopcheck and stopcheck(): raise CWStopCheck()
                                # don't search further than current (failed) word, since we haven't been there yet
                                if k == i: break
                                # if next word is an intersect...
                                if wd['w'] in crosses:
                                    # store FIRST intersect's index -- we'll revert path to it later
                                    if j < 0: j = k
                                    # drop word (intersect) from USED
                                    self.used.discard(self.words.get_word_str(wd['w']))
                                    self._log(f"Clearing [{self.words.print_word(wd['w'])}]...", end='')
                                    # clear it (SOFTLY!)
                                    self.words.clear_word(wd['w'], False)  
                                    self._log(f" --> [{self.words.get_word_str(wd['w'])}]")
                                    # ...and reset its suggestions to None (need to re-generate later)
                                    wd['sug'] = None    
                            # reset path index to first intersect in path or one step back if no intersects were found in path
                            i = j if j >= 0 else i - 1
                            
                        # if no intersects are found, reset path index to one step back
                        else:
                            i -= 1
                      
                        # go back to [i]-th path element (word) -- 
                        # it will have been cleared by now, so we'll re-generate it and step forward as usual
                        continue
                    
                    # if we CANNOT go back (we're already or still at first word...)
                    else:
                        # set res to False, since we've failed to generate the current path
                        self._log('Start node reached; unable to generate for path!')
                        res = False
                        # break from current path, go to next one (if any)
                        break
                
                # otherwise, if suggestions are not empty
                else:
                    # remove last suggestion from list and use it for current word
                    # (removing is necessary to be able to step back through or break from path
                    # when all the suggestions are exhausted)
                    sug_word = self.wordsource.pop_word(p[i]['sug'])
                    self._log(f"Trying '{sug_word}' for [{self.words.get_word_str(p[i]['w'])}]...")
                    # write suggestion to current word (store in word grid)
                    # add new word to USED list (to mark as 'used' and 'visited')
                    self.words.change_word(p[i]['w'], sug_word)
                    # increment path index to step forward to next word in path
                    i += 1
                    
            # add generation result for current path to results list
            results.append(res)
            self._log(f"\n\tCompleted path with result = {res}")
            
        self._log(f"\n\tCompleted CW!")
        # return True if all paths have been generated successfully and False otherwise
        return all(results)
        
    def generate_recurse(self, start_word=None, recurse_level=0, timeout=None, stopcheck=None):
        """
        Generates crossword using the recursice algorithm.
        ARGS:
            * start_word (Word): the initial word from which generation will start;
              if None, the first incomplete word will be taken
            * recurse_level (int): the current recursion depth (position on stack);
              this arg must be zero when starting generation; each recursive call
              will increment it and each return will decrement it
        RETURNS:
            True on success (all words in CW are filled) and False otherwise
        """  
        # check timeout
        if self.timeout_happened(timeout): raise CWTimeoutError()
        # check for stopping criteria
        if stopcheck and stopcheck(): raise CWStopCheck()
                
        # words must be a valid non-empty container
        if getattr(self, 'words', None) is None:
            raise CWError('Words collection is not initialized!') 
                    
        rec_level = recurse_level
        
        # find first incomplete word if start_word == None
        if start_word is None:
            start_word = self.words.find_incomplete(exclude=lambda w: self.words.get_word_str(w) in self.used)
            if start_word is None: return True
            
        # if CW is fully completed, clear USED and return True
        #if len(self.words) == len(self.used): return True
        
        s_word = self.words.get_word_str(start_word)
                       
        # return True (success of generation cycle) if start_word is found in the USED list
        if s_word in self.used: return True
                       
        self._log(f"{LOG_INDENT * rec_level}New start word is: {self.words.print_word(start_word)}")
            
        # fetch list of suggested words for start_word
        suggested = self.suggest(s_word)
        # if nothing could be fetched return False
        if not suggested:
            self._log(f"{LOG_INDENT * rec_level}Unable to generate CW for word '{s_word}'!")
            return False
        
        self._log(f"{LOG_INDENT * rec_level}Fetched {len(suggested)} suggestions")
        
        # success flag
        ok = True
        
        # copy current word
        old_start_word = s_word
        
        # iterate over suggested words        
        for sugg_word in suggested:
            
            # check timeout
            if self.timeout_happened(timeout): raise CWTimeoutError()
            # check for stopping criteria
            if stopcheck and stopcheck(): raise CWStopCheck()
            
            self._log(f"{LOG_INDENT * rec_level}Trying '{sugg_word}' for '{s_word}'...")
            # replace start_word with next suggestion
            self.words.change_word(start_word, sugg_word)
            # add it to USED list (for next suggest() and generate() calls)
            self.used.add(sugg_word)  
            
            self._log(f"\n{str(self.words)}\n")
            
            # find intersecting words (go for DFS algorithm), don't retrieve coordinates (just words)
            crosses = self.words.intersects_of(start_word, False)
            # if there are no intersects, return True (done current cycle)
            if not crosses: 
                self._log(f"{LOG_INDENT * rec_level}No crosses for '{s_word}'")
                return True
            
            self._log(f"{LOG_INDENT * rec_level}Found {len(crosses)} crosses for '{s_word}': {repr([self.words.get_word_str(el) for el in crosses])}")
            
            # iterate over the intersecting words
            
            for cross in crosses:
                
                # check timeout
                if self.timeout_happened(timeout): raise CWTimeoutError()
                # check for stopping criteria
                if stopcheck and stopcheck(): raise CWStopCheck()

                # skip already used words
                if self.words.get_word_str(cross) in self.used:
                    self._log(f"{LOG_INDENT * rec_level}Skipping cross '{self.words.get_word_str(cross)}'...")
                    ok = True
                    continue
                                
                # increment recurse level
                rec_level += 1
                # attempt to generate from current intersect
                res = self.generate_recurse(cross, rec_level, timeout, stopcheck)
                # decrement recurse level
                rec_level -= 1
                                    
                if res: 
                    self._log(f"{LOG_INDENT * rec_level}Generated for cross '{self.words.get_word_str(cross)}'")
                    # set OK to True on success (go to next intersect)
                    ok = True
                    # return True if CW is complete
                    if len(self.words) == len(self.used): return True
                    
                else:
                    # if failed to generate, restore current word to previous (unfilled)
                    self._log(f"{LOG_INDENT * rec_level}Failed to generate for cross '{self.words.get_word_str(cross)}', restoring grid...")
                    # discard the current (failed) intersect from USED
                    self.used.discard(self.words.get_word_str(cross))
                    # restore the old word (the one before diving into recursive generation)
                    self.words.change_word(start_word, old_start_word)
                    # reset OK to False
                    ok = False
                    # break from intersects loop, go to next suggestion for start_word...
                    break
                
            # if we've succeeded before (generating from all intersects recursively),
            # we can break from suggestions loop, since we've in fact completed the 
            # current connected graph (of intersecting words)
            if ok: break
            # otherwise, we're gonna try the next suggested word, so we'll discard the current (failed) one from USED:
            self.used.discard(sugg_word)
        
        # if we're on zero recursion level, find next incomplete word 
        # and generate from there (solve new connected graph); otherwise, return True (step up in recursion stack)
        if ok: 
            return True if recurse_level > 0 else self.generate_recurse(None, 0, timeout, stopcheck)
        
        # otherwise everything is sad...
        self._log(f"{LOG_INDENT * rec_level}Unable to generate CW for word '{str(start_word)}'!")
        return False
    
    def timeout_happened(self, timeout=None):
        return ((timeit.default_timer() - self.time_start) >= timeout) if not timeout is None else False
    
    def generate(self, method=None, timeout=60.0, stopcheck=None, 
                 onfinish=None, ontimeout=None, onstop=None, onerror=None, onvalidate=None):
        """
        Core member function in Crossword: generates the CW using the given method.
        ARGS:
            * method (str): generation method, one of:
                ** 'iter': use the iterative algorithm
                ** 'recurse': use the recursive algorithm
                ** None or '' (default): use recursive algo if cw is fully blank and iter othwerwise
            * timeout (float): terminate generation after the lapse of this many seconds;
                if None, no timeout is set
            * stopcheck (callable): called by generation methods to check if termination is required
            * onfinish (callable): called at completion; callback prototype is:
                onfinish(elapsed: float) -> None, where
                    elapsed [float]: seconds elapsed during generation
            * ontimeout (callable): called at timeout error; callback prototype is:
                ontimeout(timeout: float) -> None, where
                    timeout [float]: timeout seconds
            * onstop (callable): called if the generation was interrupted via stopcheck; prototype is:
                onstop() -> None
            * onerror (callable): called on uncaught exception; prototype is:
                onerror(err: Exception) -> None
            * onvalidate (callable): called on validating cw words; prototype is:
                onvalidate(bad_words: [] or None) -> None, where
                    bad_words: list of unmatched words or None if successful
        RETURNS:
            True on successful generation and False on failure.
        """
        # check source
        if not self.wordsource:
            self._log(f"No valid word source for crossword generation!")
            if onfinish: onfinish(0)
            return False
        
        # mark start time to clock execution
        self.time_start = timeit.default_timer()
        # reset USED list
        self.reset_used()
        self._log(f"{str(self.words)}\n\n")
        # generate CW using the specified method and store the result
        res = False
        try:
            if method == 'iter':
                self._log("USING ITERATIVE ALGORITHM...")
                res = self.generate_iter(timeout=timeout, stopcheck=stopcheck) 
            elif method == 'recurse':
                self._log("USING RECURSIVE ALGORITHM...")
                res = self.generate_recurse(timeout=timeout, stopcheck=stopcheck)
            elif not method:
                self._log("AUTO SELECTING ALGORITHM...")
                if self.words.count_incomplete() < len(self.words):
                    # cw has some completed words, use recursive ago
                    self._log("USING RECURSIVE ALGORITHM...")
                    res = self.generate_recurse(timeout=timeout, stopcheck=stopcheck)
                else:
                    # cw is fully blank, use iterative algo
                    self._log("USING ITERATIVE ALGORITHM...")
                    res = self.generate_iter(timeout=timeout, stopcheck=stopcheck)
            else:
                raise CWError(f"'method' argument ({repr(method)}) is not valid! Must be one of: 'iter', 'recurse', or None / empty string.")
        
        except CWTimeoutError:
            self._log(f"TIMED OUT AT {timeout} SEC!")
            if ontimeout: ontimeout(timeout)
            
        except CWStopCheck:
            self._log(f"STOPPED!")
            if onstop: onstop()
            
        except (CWError, Exception) as err:
            if onerror: onerror(err)
            
        # calculate elapsed time
        elapsed = timeit.default_timer() - self.time_start
            
        # validate completed words against word source
        if res: 
            bad_words = self.validate()
            if onvalidate: onvalidate(bad_words) 

        if self.log: 
            self._log(f"\n\n{str(self.words)}")
            self._log(f"\n{self.words.print_words()}")
        
        # output results
        self._log(f"GENERATION COMPLETED IN {elapsed:.1f} SEC.")
        if onfinish: onfinish(elapsed)
        return res
    
    def validate(self):
        """
        Validates all CW words against the word list (checks they are all present).
        """
        # call word source's check_bad() function on all words in CW
        lst_bad = list(filter(lambda w: not self.wordsource.check(w, self.pos, self.wordfilter), self.words.word_list()))
        # if lst_bad is not empty, it will contain words not found in the word source
        if lst_bad:
            self._log(f"No database results for {repr(lst_bad)}!")
            return lst_bad
        else:
            self._log('CHECK OK')
            return None
    
    def __str__(self):
        """
        String converter operator overload. 
        Outputs Crossword object as a crossword grid.
        """
        return str(self.words)

    @staticmethod
    def basic_grid(cols, rows, base_pattern=1):
        """
        cols [int]: number of columns, >= 2
        rows [int]: number of rows, >= 2
        base_pattern [int]: basic 2x2 pattern, one of:
            1 =     [*][_]
                    [_][_]
            2 =     [_][*]
                    [_][_]
            3 =     [_][_]
                    [*][_]
            4 =     [_][_]
                    [_][*]                                                         
        """
        if cols < 2: cols = 2
        if rows < 2: rows = 2
        pair1 = ''; pair2 = ''
        if base_pattern < 1 or base_pattern > 4:
            base_pattern = 1
        if base_pattern == 1:
            pair1 = FILLER + BLANK
            pair2 = BLANK + BLANK
        elif base_pattern == 2:
            pair1 = BLANK + FILLER
            pair2 = BLANK + BLANK
        elif base_pattern == 3:
            pair1 = BLANK + BLANK
            pair2 = FILLER + BLANK
        elif base_pattern == 4:
            pair1 = BLANK + BLANK
            pair2 = BLANK + FILLER
        grid = []
        for i in range(rows):
            pair = pair1 if (i == 0 or i % 2 == 0) else pair2
            s = pair * (cols // 2)
            if len(s) < cols: s += pair[0]
            grid.append(s)
        return '\n'.join(grid)