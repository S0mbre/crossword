# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package pycross.crossword
# Implementation of crossword-related objects: words, crossword grid and crossword generator.
# The classes implemented here are independent of GUI and can be used in a console environment
# or accessed by plugins.
from utils.globalvars import *
from utils.utils import *

import sys, os, json, datetime, numpy as np, timeit, xml.etree.ElementTree as ET
from operator import itemgetter
from html.parser import HTMLParser

# ******************************************************************************** #

## the placeholder used for filled (blocked / stopped) cells inside the cw grid
# (those that are usually shown as black cells in print)
FILLER = '*'
## the placeholder used for surrounding cells around the cw grid
# (used chiefly when the grid is of non-rectangular form)
FILLER2 = '~'
## the placeholder used for blank cells
BLANK = '_'
## a default cw grid structure - used by Crossword constructor as default grid initializer
DEFAULT_GRID = \
"""____*___*____
*_*_______*_*
*_*_*_*_*_*_*
*_**_____****
___**_*_**___
*_*********_*"""
## indentation character(s) in log messages
LOG_INDENT = '\t'

# ******************************************************************************** #

## General-purpose crossword exceptions.
class CWError(Exception):
    pass

## Generation timeout exception.
class CWTimeoutError(CWError):
    pass

## Generation interrupt exception.
class CWStopCheck(CWError):
    pass

# ******************************************************************************** #

## Utility class that converts HTML text to plain text.
# Found solution here: https://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
class MLStripper(HTMLParser):
    
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

# ******************************************************************************** #

## @brief This is a base class for word objects, basically consisting of a pair of (x, y) coordinates:
# the start coordinate given by Coords::start and the end coordinate given by Coords::end.
# All coordinates are given as 2-tuples (x, y): x = row, y = column (0-based)
class Coords:
    
    ## The Coords constructor: initializes and validates Coords::start and Coords::end.
    # @param coord_start `2-tuple` the start coordinate (x, y)
    # @param coord_end `2-tuple` the end coordinate (x, y)
    def __init__(self, coord_start, coord_end):
        ## `2-tuple` the start coordinate (x, y)
        self.start = coord_start
        ## `2-tuple` the end coordinate (x, y)
        self.end = coord_end
        self.validate()
        
    ## Validates the start and end coordinates passed to __init__().
    # @exception crossword::CWError at least one coordinate is incorrect (relevant to the other)
    def validate(self):
        if not isinstance(self.start, tuple) or not isinstance(self.end, tuple):
            raise CWError(_('Coords.start and Coords.end must be 2-tuples!'))
        if len(self.start) != 2 or len(self.end) != 2:
            raise CWError(_('Coords.start and Coords.end must be 2-tuples!'))
        if self.start[0] == self.end[0]:
            # vertical            
            if self.end[1] <= self.start[1]:
                raise CWError(_('End coordinate {} must be greater than the start coordinate {}!').format(repr(self.end), repr(self.start)))
            ## `str` direction of the start-to-end vector: 'h' = 'horizontal', 'v' = 'vertical'
            self.dir = 'v'
        elif self.start[1] == self.end[1]:
            # horizontal
            if self.end[0] <= self.start[0]:
                raise CWError(_('End coordinate {} must be greater than the start coordinate {}!').format(repr(self.end), repr(self.start)))
            self.dir = 'h'
        else:
            raise CWError(_('One coordinate must be equal!'))

    ## Outputs a list of (x,y) coordinates (`2-tuples`) between Coords::start and Coords::end.
    # @returns `list` a list of coordinate `2-tuples` beginning with Coords::start and ending with Coords::end
    def coord_array(self):
        if self.dir == 'h': 
            l = self.end[0] - self.start[0] + 1
            return [(i + self.start[0], self.start[1]) for i in range(l)]
        else:
            l = self.end[1] - self.start[1] + 1
            return [(self.start[0], i + self.start[1]) for i in range(l)]
        
    ## Checks if a coordinate lies anywhere between Coords::start and Coords::end.
    # @param coord [tuple] the coordinate to check
    # @returns `bool` `True` if coord crosses (lies between Coords::start and Coords::end), `False` otherwise
    def does_cross(self, coord):
        for c in self.coord_array():
            if c == coord: 
                return True
        return False

    ## Python `len()` overload: the distance between Coords::start and Coords::end.
    def __len__(self):
        cooord_index = 1 if self.dir == 'v' else 0
        return self.end[cooord_index] - self.start[cooord_index] + 1
    
    ## Python `repr()` overload: human-readable representation of Coords.
    def __repr__(self):
        return _("Coords object :: start = {}, end = {}, dir = '{}'").format(repr(self.start), repr(self.end), self.dir)

# ******************************************************************************** #

## @brief Implementation of a single word in a hypothetical crossword.
# The class adds to Coords the word number (as found in a crossword), word string, and clue text.
class Word(Coords):
    
    ## Initializes and validates data.
    # @param coord_start `2-tuple` the start coordinate (x, y)
    # @param coord_end `2-tuple` the end coordinate (x, y)
    # @param num `int` word number (in a hypothetical cw grid)
    # @param clue `str` word clue text, e.g. "NBA superstar Jordan's first name"
    # @param word `str` word text, e.g. "FATHER"
    def __init__(self, coord_start, coord_end, num=0, clue='', word=None):
        super().__init__(coord_start, coord_end)
        ## `int` word number (in a hypothetical cw grid)
        self.num = num
        ## `str` word clue text
        self.clue = clue
        self.set_word(word)
        
    ## Sets the internal word string (text).
    # @param wd `str` the word text
    # @exception crossword::CWError passed word has incorrect length (not corresponding to Coords::__len__())
    def set_word(self, wd):
        if not wd is None and len(wd) != len(self):
            raise CWError(_('Word length is not correct!'))
        ## `str` word text
        self.word = wd
        
    ## Python `hash()` overload: to make Word objects comparable / searchable in collections.
    def __hash__(self):
        return hash((self.start, self.dir))
                
    ## Python `repr()` overload: human-readable representation of Word object.
    def __repr__(self):
        return _("Word object :: num = {}, start = {}, end = {}, dir = '{}'").format(self.num, repr(self.start), repr(self.end), self.dir)
    
# ******************************************************************************** # 

## @brief A simple structure to hold crossword meta information, such as title, author, etc.        
class CWInfo:
    
    def __init__(self, title='', author='', editor='', publisher='', cpyright='', date=None):
        ## `str` title
        self.title = title
        ## `str` author name
        self.author = author
        ## `str` editor name
        self.editor = editor
        ## `str` publisher name
        self.publisher = publisher
        ## `str` copyright info
        self.cpyright = cpyright
        ## `datetime` creation date
        self.date = date

    ## Python `str()` overload for handy console output
    def __str__(self):
        return '\n'.join((f"{key}='{value}'" for key, value in self.__dict__.items()))
    
# ******************************************************************************** #

## @brief Core crossword implementation - a grid of characters + internal Word objects.
# This class provides most of the methods required to operate with crosswords on
# the low level, such as adding/deleting words, file I/O, replacing characters,
# checking word completeness, counting grid stats and so on.
# Low-level methods work on the internal character grid, i.e. with individual characters.
# Higher-level methods work with Word objects (i.e. words). The class implements a 2-way
# correspondence between characters and words.
class Wordgrid:
    
    ## Constructor initializes the words and grid from the given grid data.
    # @param data `list` | `str` the input data to initialize the grid from; can be any of:
    #   * `list` list of grid rows, each row being itself either a concatenated string, 
    #            e.g. '_*_*_*', or a list of characters, e.g. ['_', '*', '_', '*']
    #   * `list` list of Word objects
    #   * `str` a single newline-delimited string representing the whole grid, see crossword::DEFAULT_GRID
    #   * `str` full path to an XPF or IPUZ crossword file, or a simple text file containing the cw grid
    # @param data_type `str` hint used by the program to process the 'data' argument, can be any of:
    #   * 'grid' = data is a list or str-type grid
    #   * 'words' = data is a list of Word objects
    #   * 'file' = data is a file path
    # @param info `CWInfo` crossword meta information, default = CWInfo default constructor
    # @param on_reset `callable` callback function triggered when the grid is reset via reset().
    # Callback parameters are:
    #   * `Wordgrid` pointer to the calling class instance
    #   * `list` pointer to Wordgrid::grid
    # @param on_clear `callable` callback function triggered when the grid is cleared via clear()
    # Callback parameters are:
    #   * `Wordgrid` pointer to the calling class instance
    # @param on_change `callable` callback function triggered when a word is changed via change_word()
    # Callback parameters are:
    #   * `Wordgrid` pointer to the calling class instance
    #   * `Word` Word object being changed
    #   * `str` word's text before the change
    # @param on_clear_word `callable` callback function triggered when a word is cleared via clear_word()
    # Callback parameters are:
    #   * `Wordgrid` pointer to the calling class instance
    #   * `Word` Word object being cleared
    #   * `str` word's text before clearing
    # @param on_putchar `callable` callback function triggered when a charater is set in the grid via put_char()
    # Callback parameters are:
    #   * `Wordgrid` pointer to the calling class instance
    #   * `Coord` | `2-tuple` coordinate of the character
    #   * `str` character's previous value
    #   * `str` character's new value
    # @exception crossword::CWError wrong 'data_type' value
    def __init__(self, data, data_type='grid', info=CWInfo(), 
                 on_reset=None, on_clear=None, on_change=None, 
                 on_clear_word=None, on_putchar=None):
        ## `CWInfo` crossword meta info, such as title, author, etc.
        self.info = info
        ## callback function triggered when the grid is reset via reset()
        self.on_reset = on_reset
        ## callback function triggered when the grid is cleared via clear()
        self.on_clear = on_clear
        ## callback function triggered when a word is changed via change_word()
        self.on_change = on_change
        ## callback function triggered when a word is cleared via clear_word()
        self.on_clear_word = on_clear_word
        ## callback function triggered when a charater is set in the grid via put_char()
        self.on_putchar = on_putchar
        ## backup of Wordgrid::words used in save() and restore()
        self.old_words = None
        self.initialize(data, data_type)
            
    ## Initializes the internal char grid and words collection from given data.
    # @see See arguments and description in __init__()
    # @exception crossword::CWError wrong 'data_type' value
    def initialize(self, data, data_type='grid'):
        if data_type == 'grid':
            self.reset(data)
        elif data_type == 'words':
            self.from_words(data)
        elif data_type == 'file':            
            self.from_file(data)
        else:
            raise CWError(_("Wrong 'data_type' argument: '{}'! Must be 'grid' OR 'words' OR 'file'!").format(data_type))
        
    ## @brief Checks if the grid is appropriate.
    # The grid must:
    #   * be of a `str` or `list` type
    #   * contain only [a-z] characters, crossword::BLANK, or crossword::FILLER, or crossword::FILLER2
    # @param grid `list` | `str` crossword grid: either a newline-delimited single string 
    # or a 2-dimension list of individual characters (of type `str`)
    # @exception crossword::CWError incorrectly formatted grid
    def validate(self, grid):
        if isinstance(grid, str):
            grid = grid.split('\n')
            if len(grid) < 2:
                raise CWError(_('Grid appears incorrect, for in contains less than 2 rows!'))
                
        if isinstance(grid, list):
            for row in grid:
                if not all(c.isalpha() or c in (BLANK, FILLER, FILLER2) for c in row):
                    raise CWError(_("Grid contains invalid characters! Must contain only [a-z], '{}', '{}' and '{}'.").format(BLANK, FILLER, FILLER2))
            return
        
        raise CWError(_('Grid must be passed either as a list of strings or a single string of rows delimited by new-line symbols!'))                  
        
    ## @brief Reconstructs the internal grid from the given grid data.
    # The following class members are fully re-initialized:
    #   * Wordgrid::words - the collection of Word objects
    #   * Wordgrid::grid - the internal grid pattern OR the existing self.grid if == `None`
    #   * Wordgrid::width - the horizontal size (in cells)
    #   * Wordgrid::height - the vertical size (in cells)
    # @param grid `list` | `str` crossword grid -- see 'data' argument in __init__()
    # If `None`, Wordgrid::grid will be used, if initialized (otherwise, an exception will be raised)
    # @param update_internal_strings `bool` tells the function to update each 
    # Word object's string representation
    # @exception crossword::CWError empty / null 'grid' argument and Wordgrid::grid not initialized 
    def reset(self, grid=None, update_internal_strings=False):
        if grid is None and not getattr(self, 'grid', None): 
            raise CWError(_('Cannot call reset() on a null grid!'))
            
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
        ## internal words list (`list` of Word objects)
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
        ## internal 2-dimensional character grid, e.g.
        # <pre> [['f', 'a', 't', 'h', 'e', 'r', '*', '_', 'o', 'm'], [...]] </pre>
        self.grid = grid
        ## number of columns in grid
        self.width = grid_width
        ## number of rows in grid
        self.height = lgrid  
        if update_internal_strings: self.update_word_strings()
        if self.on_reset: self.on_reset(self, self.grid)
        
    ## @brief Constructs the internal grid, dimensions and words 
    # from the given collection of Word objects.
    # 
    # This is essentially the reverse of reset(), 
    # which constructs words from a given grid structure.
    # @param words `iterable` collection of source Word objects used to populate the grid
    # @param update_internal_strings `bool` tells the function to update each 
    # Word object's string representation
    # @exception crossword::CWError None 'words' argument is not initialized or inappropriate
    def from_words(self, words, update_internal_strings=False):
        if not words or not is_iterable(words) or not isinstance(words[0], Coords):
            raise CWError(_(f'"words" argument must be a non-empty collection of Word / Coords objects!'))
            
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

    ## Util function that reads a text file into a list of strings suitable as internal grid data.
    # @param gridfile `str` path to the source text file
    # @returns `list` of `str` grid rows as a list of concatenated strings
    def grid_from_file(self, gridfile):
        cwgrid = []
        with open(gridfile, 'r', encoding=ENCODING, errors='replace') as file:
            for ln in file:
                s = ln
                if s.endswith('\n'): s = s[:-1]
                if s.endswith('\r'): s = s[:-1]
                if not s: break
                cwgrid.append(s)            
        return cwgrid
        
    ## Initializes grid data from a crossword file, text file, or JSON-formatter Word collection dump.
    # @param filename `str` path to the source file
    # The file type can be any of:
    #   * XPF = see https://www.xwordinfo.com/XPF/
    #   * IPUZ = see http://www.ipuz.org/ 
    #   * JSON = a JSON dump of a list of Word objects 
    #   * other (text) = a simple text file containing raw grid data
    # @param file_format `str` hint to tell the program the file format (must be 'xpf', 'ipuz', 'json' or `None`).
    # If `None`, the file type will be guessed from the file extension.
    def from_file(self, filename, file_format=None):
        if file_format is None:
            file_format = os.path.splitext(filename)[1][1:].lower()

        if file_format == 'xpf':
            self._parse_xpf(filename)

        elif file_format == 'ipuz':
            self._parse_ipuz(filename)
            
        elif file_format == 'json':
            # assume JSON has list of Word objects
            with open(filename, 'r', encoding=ENCODING, errors='replace') as infile:
                words = json.load(infile)
                self.from_words(words)

        else:
            # assume simple grid text file
            self.reset(self.grid_from_file(filename))
    
    ## Exports the crossword grid to a file.
    # @see Description of arguments in from_file()
    def to_file(self, filename, file_format=None):
        if file_format is None:
            file_format = os.path.splitext(filename)[1][1:].lower()

        if file_format == 'xpf':
            self._save_xpf(filename)

        elif file_format == 'ipuz':
            self._save_ipuz(filename)

        elif file_format == 'json':
            with open(filename, 'w', encoding=ENCODING) as outfile:
                json.dump(self.words, outfile, ensure_ascii=False, indent='\t')

        else:
            # save grid
            with open(filename, 'w', encoding=ENCODING) as outfile:
                outfile.write(self.tostr())

    ## @brief Util function to parse IPUZ files.
    # Resets Wordgrid::grid and Wordgrid::info from the file data.
    # @param filename `str` path to the source file (*.ipuz)
    # @see http://www.ipuz.org/ 
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
        with open(filename, 'r', encoding=ENCODING, errors='replace') as infile:
            ipuz = json.load(infile)
        ipuz_kind = ''.join(ipuz.get('kind', ''))
        if not ipuz_kind: raise CWError(_("Unable to parse '{}' as IPUZ file!").format(filename))
        if not 'crossword' in ipuz_kind.lower(): return
        # get info
        self.info.title = ipuz.get('title', '')
        self.info.author = ipuz.get('author', '')
        self.info.editor = ipuz.get('editor', '')
        self.info.cpyright = ipuz.get('copyright', '')
        self.info.publisher = ipuz.get('publisher', '')
        date_str = ipuz.get('date', '')
        self.info.date = str_to_datetime(date_str, '%m/%d/%Y') if date_str else None
        # get grid
        grid = ipuz.get('solution', None)
        if grid:            
            # first try the 'solutions' data
            grid = [''.join([_get_char(col) for col in row]) for row in grid]
        else:
            # if solutions is absent, try 'puzzle' data
            grid = ipuz.get('puzzle', None)
            # if both 'solutions' and 'puzzle' are absent, raise error
            if not grid: raise CWError(_("Unable to parse '{}' as IPUZ file!").format(filename))
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

    ## @brief Util function to save the grid and info to an IPUZ file.
    # Exports data from Wordgrid::grid and Wordgrid::info to the file.
    # Since IPUZ files are JSON-formatted, json.dump() is used for exporting.
    # @param filename `str` path to the source file (*.ipuz)
    # @param ipuz_version `str` IPUZ API version (=2)
    # @param ipuz_kind `str` IPUZ puzzle kind (=crossword)
    # @see http://www.ipuz.org/ 
    def _save_ipuz(self, filename, ipuz_version='2', ipuz_kind='1'):
        ipuz = {'version': f"http://ipuz.org/v{ipuz_version}", 'kind': [f"http://ipuz.org/crossword#{ipuz_kind}"]}
        if self.info.title: ipuz['title'] = self.info.title
        if self.info.author: ipuz['author'] = self.info.author
        if self.info.editor: ipuz['editor'] = self.info.editor
        if self.info.cpyright: ipuz['copyright'] = self.info.cpyright
        if self.info.publisher: ipuz['publisher'] = self.info.publisher
        if self.info.date: ipuz['date'] = datetime_to_str(self.info.date, '%m/%d/%Y')
        ipuz['origin'] = f"{APP_NAME} {APP_VERSION}"
        ipuz['dimensions'] = {'width': self.width, 'height': self.height}
        ipuz['puzzle'] = [['#' if c == FILLER else ('null' if c == FILLER2 else 0) for c in row] for row in self.grid]
        ipuz['solution'] = [['#' if c == FILLER else ('null' if c == FILLER2 else c.upper()) for c in row] for row in self.grid]
        ipuz['clues'] = {'Across': [], 'Down': []}
        self.sort()
        for w in self.words:
            k = 'Across' if w.dir == 'h' else 'Down'
            ipuz['clues'][k].append([w.num, w.clue])

        with open(filename, 'w', encoding=ENCODING) as outfile:
            json.dump(ipuz, outfile, ensure_ascii=False, indent='\t')
    
    ## @brief Util function to parse XPF files.
    # Resets Wordgrid::grid and Wordgrid::info from the file data.
    # @param filename `str` path to the source file (*.xpf)
    # @see https://www.xwordinfo.com/XPF/
    def _parse_xpf(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        pz = root.find('Puzzle')
        if not pz:
            raise CWError(_("No puzzles in '{}'!").format(filename))
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
        self.info.date = str_to_datetime(date.text, '%m/%d/%Y') if date else None
        # make grid
        gr = pz.find('Grid')
        if not gr:
            raise CWError(_("No grid in '{}'!").format(filename))
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
            
    ## @brief Util function to save the grid and info to an XPF file.
    # Exports data from Wordgrid::grid and Wordgrid::info to the file.
    # Since XPF files are XML-formatted, ElementTree (DOM) is used for exporting.
    # @param filename `str` path to the source file (*.xpf)
    # @param xpf_version `str` XPF API version (=1.0)
    # @see https://www.xwordinfo.com/XPF/
    def _save_xpf(self, filename, xpf_version='1.0'):
        if not self.words: return
        root = ET.Element('Puzzles')
        root.set('Version', xpf_version)
        pz = ET.SubElement(root, 'Puzzle')
        if self.info.title:
            ET.SubElement(pz, 'Title').text = self.info.title
        if self.info.author:
            ET.SubElement(pz, 'Author').text = self.info.author
        if self.info.editor:
            ET.SubElement(pz, 'Editor').text = self.info.editor
        if self.info.cpyright:
            ET.SubElement(pz, 'Copyright').text = self.info.cpyright
        if self.info.publisher:
            ET.SubElement(pz, 'Publisher').text = self.info.publisher 
        if self.info.date:
            ET.SubElement(pz, 'Date').text = datetime_to_str(self.info.date, '%m/%d/%Y')
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
        tree.write(filename, encoding=ENCODING, xml_declaration=True)
            
    ## Util function: converts HTML to plain text.
    # @param text `str` HTML-formatted text
    # @returns `str` plain text
    def _strip_html(self, text):
        if text.startswith('![CDATA[') and text.endswith(']]'):
            text = text[8:-2]
        stripper = MLStripper()
        text = stripper.strip(text)
        return text
    
    ## Updates the internal strings for each word in grid.
    def update_word_strings(self):
        for w in self.words:
            w.set_word(self.get_word_str(w))
    
    ## @brief Validates characters to use in the crossword grid.
    # Only [a-z] (in any language, not ony ASCII!), crossword::BLANK, 
    # crossword::FILLER, and crossword::FILLER2 characters are allowed.
    # @param char `str` character to validate
    # @exception crossword::CWError invalid character
    def _validate_char(self, char):
        if not char.isalpha() and not char in (BLANK, FILLER, FILLER2):
            raise CWError(_('Character "{}" is invalid!').format(char))
    
    ## Checks if the given coordinate lies within the grid dimensions.
    # @param coord `2-tuple` coordinate to validate
    # @exception crossword::CWError coordinate out of range
    def _validate_coord(self, coord):
        if coord[0] < 0 or coord[0] >= self.width or coord[1] < 0 or coord[1] >= self.height:
            raise CWError(_("Coordinate {} is out of the grid range (w={}, h={})!").format(repr(coord), self.width, self.height))
    
    ## Checks if all the words are completed (have no blanks left).
    # @returns `bool` `True` if grid contains no blanks, `False` otherwise
    def is_complete(self):
        for r in self.grid:
            if BLANK in r: return False
        return True

    ## @brief Removes the given row from grid. 
    # @warning Use with care! Destroys word structure.
    # @param row `int` index of row to delete
    def remove_row(self, row):
        if row >= 0 and row < self.height:
            del self.grid[row]
            self.reset()

    ## @brief Removes the given column from grid. 
    # @warning Use with care! Destroys word structure.
    # @param col `int` index of column to delete
    def remove_column(self, col):
        if col >= 0 and col < self.width:
            for row in self.grid:
                del row[col]
            self.reset()

    ## @brief Inserts a new row after the one given by `index`.
    # If `index == -1`, appends a row after the last one.    
    # @warning Use with care! Destroys word structure.
    # @param index `int` index of row after which a new one will be inserted
    # @param char `str` fill character for new row (default = crossword::BLANK)
    def add_row(self, index=-1, char=BLANK):
        if index < 0 or index >= self.height:
            self.grid.append([char] * self.width)
        else:
            self.grid.insert(index, [char] * self.width)
        self.reset()

    ## @brief Inserts a new column after the one given by 'index'.
    # If `index == -1`, appends a column after the last one.    
    # @warning Use with care! Destroys word structure.
    # @param index `int` index of column after which a new one will be inserted
    # @param char `str` fill character for new column (default = crossword::BLANK)
    def add_column(self, index=-1, char=BLANK):
        for row in self.grid:
            if index < 0 or index >= self.width:
                row.append(char)
            else:
                row.insert(index, char)
        self.reset()

    ## Duplicates the current grid by reflecting its cells downwards.
    # @see reflect() for description of arguments.
    def reflect_bottom(self, mirror=True, reverse=True, border=''):
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

    ## Duplicates the current grid by reflecting its cells upwards.
    # @see reflect() for description of arguments.
    def reflect_top(self, mirror=True, reverse=True, border=''):
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

    ## Duplicates the current grid by reflecting its cells to the right.
    # @see reflect() for description of arguments.
    def reflect_right(self, mirror=True, reverse=True, border=''):
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

    ## Duplicates the current grid by reflecting its cells to the left.
    # @see reflect() for description of arguments.
    def reflect_left(self, mirror=True, reverse=True, border=''):
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

    ## @brief Duplicates the current grid by reflecting its cells in a given direction.
    # @param direction `str` the direction to duplicate / reflect the current grid:
    #   * 'd[own]'  = downwards
    #   * 'u[p]'    = upwards
    #   * 'r[ight]' = to the right
    #   * 'l[eft]'  = to the left
    # @param mirror `bool` if `True` (default), reflection will be mirror-like
    # (symmetrical against bottom line).
    # @param reverse `bool` if `True` (default), reflection will be inverted
    # from left to right.
    # @param border `str` fill pattern for a border (row or column)
    # between the existing and reflected blocks of cells.
    # 
    # If both `mirror` and `reflect` are `False`, a simle copy-paste duplication will
    # be performed.
    # If `border` is an empty string (default), no extra row will be put
    # between the existing and the new (reflected) cells.
    # Otherwise, `border` is a 2-character pattern for the extra row,
    # e.g. '* ' means sequence of crossword::FILLER and crossword::BLANK, '**' means all filled, etc.
    def reflect(self, direction='d', mirror=True, reverse=True, border=''):
        d = direction[-1].lower()
        if d == 'd':
            self.reflect_bottom(mirror, reverse, border)
        elif d == 'u':
            self.reflect_top(mirror, reverse, border)
        elif d == 'r':
            self.reflect_right(mirror, reverse, border)
        elif d == 'l':
            self.reflect_left(mirror, reverse, border)
    
    ## Finds all words intersecting the given word.
    # @param word `Word` the given Word object for which intersects are to be searched
    # @param word_coord_tuples `bool` if `True`, the results will include both the
    # intersecting words and the intersect coordinates (as list of 2-tuples);
    # otherwise, only the list of intersecting Word objects is returned
    # @returns `list` list of Word objects or (Word, coord) tuples depending on `word_coord_tuples`
    def intersects_of(self, word, word_coord_tuples=True):
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
    
    ## @brief Retrieves a next incomplete word (fully or partially blank).
    # @param method `str` governs the search algorithm; it can be one of:
    #   * 'first-incomplete' (default): the first incomplete word will be returned
    #   * 'most-complete': the first word having the least blanks will be returned
    #   * 'most-incomplete': the first word having the most blanks will be returned (i.e. fully blank word)
    #   * 'random': a random incomplete word will be returned
    # @param exclude `callable` allows excluding words from search.
    # It accepts a single argument - a Word object, and returns `True` to exclude it and `False` otherwise
    # @returns `Word` | `None` a next incomplete Word object in the grid, or None if no such words are found
    def find_incomplete(self, method='most-complete', exclude=None):
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
    
    ## Counts incomplete words (those containing at least one crossword::BLANK).
    # @returns `int` number of incomplete words
    def count_incomplete(self):
        c = 0
        for w in self.words:
            if not self.is_word_complete(w):
                c += 1
        return c
    
    ## @brief Gets the text of a Word object in the grid.
    # Since the internal structure of Wordgrid is a matrix of characters 
    # rather than an array of words, word strings (text representations)
    # are not available at runtime and must be requested with this method.
    # @param w `Word` the Word object to get the text for
    # @returns `str` the text representation of the word (e.g. "father")
    # @see update_word_strings()
    def get_word_str(self, w):
        if not w in self.words: 
            raise CWError(_("Word '{}' is absent from grid!").format(str(w)))
        return ''.join(self.grid[coord[1]][coord[0]] for coord in w.coord_array())
    
    ## Checks if a word is complete (has no blanks).
    # @param w `Word` the Word object
    # @returns `bool` `True` if the word has no crossword::BLANK characters, `False` otherwise
    # @see is_word_blank() - the reverse method
    def is_word_complete(self, w):
        if not w in self.words: 
            raise CWError(_("Word '{}' is absent from grid!").format(str(w)))
        for coord in w.coord_array():
            if self.grid[coord[1]][coord[0]] == BLANK:
                return False
        return True
    
    ## Checks if a word is blank (consists entirely of crossword::BLANK characters).
    # @param w `Word` the Word object
    # @returns `bool` `True` if the word has no characters other than crossword::BLANK, `False` otherwise
    # @see is_word_complete() - the reverse method
    def is_word_blank(self, w):
        return self.get_word_str(w) == BLANK * len(w)
    
    ## Finds a Word object in the Wordgrid::words collection.
    # @param word `Word` the Word object to look for
    # @returns `Word` | `None` the found Word object or None if not found
    def find(self, word):
        for w in self.words:
            if w == word:
                return w
        return None
    
    ## @brief Retrieves words intersecting the given coordinate.
    # The method retrieves at most 2 words (across and down) for a given coordinate in the grid.
    # @param coord `2-tuple` the (x, y) coordinate in the grid to find words for
    # @param start_coord `bool` if `True` (default), only those words that start in that
    # coordinate will be returned; otherwise, all intersecting words are returned
    # @returns `dict` a dict of found words in the format:
    # @code
    #   {'h': Word|None, 'v': Word|None}
    # @endcode
    # where:\n 
    #   * 'h' = Word object intersecting the coordinate in the Across (horizontal) direction
    #   (`None` if not found)
    #   * 'v' = Word object intersecting the coordinate in the Down (vertical) direction
    #   (`None` if not found)
    def find_by_coord(self, coord, start_coord=True):
        found = {'h': None, 'v': None}
        for w in self.words:
            if start_coord:
                if w.start == coord:
                    found[w.dir] = w
            elif w.does_cross(coord):
                found[w.dir] = w
        return found
    
    ## Gets a word by its start coordinate and direction.
    # @param coord `2-tuple` the start coordinate of the word looked for
    # @param direction `str` the word's direction: 'h' = 'horizonal' or 'v' = 'vertical'
    # @returns `Word` | `None` the found Word object or `None` if not found
    def find_by_coord_dir(self, coord, direction):
        for w in self.words:
            if w.start == coord and w.dir == direction:
                return w
        return None
    
    ## @brief Gets a word by its text representation.
    # @warning The search will return the FIRST word corresponding 
    # to the given text. If the crossword contains more than one such word
    # (which it shouldn't, of course!) - all these other matches will be ignored!
    # @param str_word `str` the text to search for, e.g. "father"
    # @returns `Word` | `None` the found Word object or `None` if not found
    def find_by_str(self, str_word):
        for w in self.words:
            if self.get_word_str(w) == str_word:
                return w
        return None
    
    ## Gets a word by its sequential number and direction.
    # @param num `int` the word's sequential number as stored in Word::num
    # @param direction `str` the word's direction: 'h' = 'horizonal' or 'v' = 'vertical'
    # @returns `Word` | `None` the found Word object or `None` if not found
    def find_by_num_dir(self, num, direction):
        #self.sort()
        for w in self.words:
            if w.num == num and w.dir == direction: return w
        return None
    
    ## @brief Gets a word by its clue text.
    # @warning The search will return the FIRST word corresponding 
    # to the given clue. If the crossword contains more than one such clues
    # (which it shouldn't, of course!) - all these other matches will be ignored!
    # @param clue `str` the clue text to search for, e.g. "US largest state"
    # @returns `Word` | `None` the found Word object or `None` if not found
    def find_by_clue(self, clue):
        for w in self.words:
            if w.clue == clue: return w
        return None
    
    ## Gets the text character stored in the given grid coordinate.
    # @param coord `2-tuple` the grid coordinate
    # @returns `str` the single character contained in that coordinate
    # @exception crossword::CWError coordinate out of range
    def get_char(self, coord):
        self._validate_coord(coord)
        return self.grid[coord[1]][coord[0]]
        
    ## @brief Puts a character into a given coordinate (replacing the existing one).
    # The Wordgrid::on_putchar callback is called after putting the character.
    # @param coord `2-tuple` the grid coordinate to write to
    # @param char `str` the character to put
    # @exception crossword::CWError invalid character
    def put_char(self, coord, char):
        old_char = self.get_char(coord)
        new_char = char.lower()
        self._validate_char(new_char)
        self.grid[coord[1]][coord[0]] = new_char
        if self.on_putchar: self.on_putchar(self, coord, old_char, new_char)

    ## @brief Clears all the words in the collection.
    # This method effectively puts crossword::BLANK into all non-blocked cells
    # of the grid. The internal text representations of each Word object
    # are not updated - call update_word_strings() after this operation if required.
    # The Wordgrid::on_clear callback is called after clearing.
    def clear(self):
        for y in range(self.height):
            for x in range(self.width):
                if not self.grid[y][x] in (FILLER, FILLER2):
                    self.grid[y][x] = BLANK
        if self.on_clear: self.on_clear(self)
            
    ## @brief Replaces the text representation of a given word.
    # The Wordgrid::on_change callback is called after the replacement.
    # @param word `Word` the Word object to replace the text for
    # @param new_word `str` the new text for the word, e.g. "father"
    # @exception crossword::CWError word not found in grid or new text has incorrect length 
    # (different from the given word's length)
    def change_word(self, word, new_word: str):        
        if not word in self.words: 
            raise CWError(_("Word '{}' is absent from grid!").format(str(word)))
        if len(new_word) != len(word):
            raise CWError("Lengths of words do not match!")
        if self.on_change: w_old = self.get_word_str(word)
        for i, coord in enumerate(word.coord_array()):
            self.put_char(coord, new_word[i])
        #self.update_word_strings()
        if self.on_change: self.on_change(self, word, w_old)
            
    ## @brief Clears the given word making its characters blank.
    # @param word `Word` the Word object to clear
    # @param force_clear `bool` if `True`, ALL the characters in the word
    # will be replaced by crossword::BLANK, regardless of intersecting words, if any.
    # Otherwise (if False, which is the default), only the free characters 
    # will be cleared (that is, those not intersecting with other words).
    # The Wordgrid::on_clear_word callback is called after clearing.
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
            
    ## @brief Sorts the words collection by the word coordinates.
    # The sorting is performed in the assending order: 
    # first on rows, then on columns. This corresponds to the typical
    # crossword word numeration.
    def sort(self):
        if getattr(self, 'words', None):
            self.words.sort(key=lambda word: (word.dir, word.num))
    
    ## Gets a human-readable representation of a word.
    # @param w `Word` the Word object
    # @returns `str` a string formatted like so: '(coord_x, coord_y) dir word_text'
    # @exception crossword::CWError word is not found in grid
    def print_word(self, w):
        if not w in self.words:
            raise CWError(_("Word '{}' is absent from grid!").format(str(w)))
        return f"{repr(w.start)} {w.dir} '{self.get_word_str(w)}'"

    ## Serializes (converts) the grid into a single human-readable string.
    # @returns `str` the text representation of the crossword grid in a tabular format, e.g.
    # <pre>
    #   Num       Coord       Value
    #   ----------------------------
    #   ACROSS:
    #   ----------------------------
    #   1         (0, 0)      father
    #   5         (0, 10)     quit
    #   9         (0, 15)     storm
    #   ----------------------------
    #   DOWN:
    #   ----------------------------
    #   ...
    # </pre>
    def print_words(self):
        #self.sort()
        s = _("Num{}Coord{}Value\n-------------------------------------------\n").format(LOG_INDENT, (LOG_INDENT * 2))
        s += _('ACROSS:\n-------------------------------------------\n')
        s += '\n'.join(f"[{w.num}]{LOG_INDENT}{repr(w.start)}{LOG_INDENT * 2}'{self.get_word_str(w)}'" for w in self.words if w.dir == 'h')   
        s += _('\n-------------------------------------------\nDOWN:\n-------------------------------------------\n')
        s += '\n'.join(f"[{w.num}]{LOG_INDENT}{repr(w.start)}{LOG_INDENT * 2}'{self.get_word_str(w)}'" for w in self.words if w.dir == 'v') 
        return s
           
    ## Serializes (converts) all clues into a single human-readable string.
    # @returns `str` the text representation of the clues in the format:
    # <pre>
    #   [word_number]   word_direction      clue text
    #   [word_number]   word_direction      clue text
    #   ...
    # </pre>
    def print_clues(self):
        return '\n'.join(f"[{w.num}]{LOG_INDENT}{w.dir}{LOG_INDENT * 2}{w.clue}" for w in self.words)
    
    ## Returns the collection (`list`) of all words in grid.
    # @param strings `bool` if `True` (default) the words' texts are returned, otherwise the Word objects
    # @returns `list` list of `str` or `Word` objects
    def word_list(self, strings=True):
        return [self.get_word_str(w) if strings else w for w in self.words]
    
    ## Concatenates Wordgrid::grid into a single newline-delimited string.
    # @returns `str` the concatenated grid string, e.g.
    # <pre>
    #   father*__it*__
    #   _*_*_*act_v_ty
    #   ...
    # </pre>
    def tostr(self):
        return '\n'.join([''.join(row) for row in self.grid]) if self.grid else ''

    ## Counts grid cells that satisfy a given condition.
    # @param condition `callable` callback function - the condition to satisfy. 
    # The callback's arguments are (in the sequential order):
    #   * `int` grid row index
    #   * `int` grid column index
    # The callback returns `True` if the condition for the given (y, x) coordinate 
    # is satisfied and `False` otherwise. If 'condition' is `None`, all cells will be counted.
    # @returns `int` number of cells that meet the given condition
    def _cell_count(self, condition=None):
        c = 0
        for y in range(self.height):
            for x in range(self.width):
                if (condition is None) or (condition(y, x) == True):
                    c += 1
        return c

    ## Counts words that satisfy a given condition.
    # @param condition `callable` callback function - the condition to satisfy. 
    # The callback takes a single argument - a Word object
    # and returns `True` if the condition is satisfied and `False` otherwise.
    # If 'condition' is `None`, all words will be counted.
    # @returns `int` number of words that meet the given condition
    def _word_count(self, condition=None):
        c = 0
        for w in self.words:
            if (condition is None) or (condition(w) == True):
                c += 1
        return c
    
    ## Returns an array of word lengths.
    # @returns `list` of `int` array of word lengths
    def _word_lengths(self):
        return [len(w) for w in self.words]

    ## Updates Wordgrid::stats dict with current handy statistics.
    def update_stats(self):
        ## stats dictionary - various handy stats like grid dimensions, word count etc.
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

    ## Saves all words to Wordgrid::old_words to be able to restore() later.
    def save(self):
        self.update_word_strings()
        self.old_words = self.words[:]

    ## Restores words from Wordgrid::old_words written by save().
    def restore(self):
        if not self.old_words is None:
            self.from_words(self.old_words)
    
    ## The `in` operator overload: checks if words contain a given word.
    # @param word `Word` | `str` the Word object or its text representation to find in the grid
    # @returns `bool` `True` if found, `False` otherwise
    # @exception crossword::CWError `word` argument is incorrect
    def __contains__(self, word):
        if isinstance(word, str):            
            word = word.lower() 
        elif not isinstance(word, Word):
            raise CWError(_('Word must be a Word object!')) 
        for w in self.words:
            if (isinstance(word, Word) and w == word) or (isinstance(word, str) and self.get_word_str(w) == word):
                return True            
        return False
    
    ## Convenience for is_complete().
    # @returns `bool` `True` if grid is complete, `False` otherwise
    def __bool__(self):
        return self.is_complete()
    
    ## Python `len()` overload: returns number of words in grid.
    # @returns `int` number of words in grid
    def __len__(self):
        return len(self.words)
    
    ## Python `str()` convertion overload: represents a pretty output of the grid.
    # @returns `str` grid as tabular-formatted text
    # @see print_words(), print_clues(), tostr()
    def __str__(self):
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
            
        
# ******************************************************************************** #

## @brief Implementation of a crossword puzzle with auto generation functionality.
# This class wraps (incapsulates) crossword::Wordgrid to construct and manipulate
# the crossword grid on the low level (file I/O, putting and getting individual words
# and characters, validation etc). It also incorporates a wordsrc::Wordsource object
# to provide the source (or multiple sources) of words for filling the crossword grid
# automatically. The filling (generation) is performed by the Crossword::generate()
# method. Additionally, some useful methods of crossword::Wordgrid are
# re-implemented to account for used words - see Crossword::used.
class Crossword:
    
    ## @brief Initializes Crossword members.
    # @param data `str` | `list` crossword grid source data as used by crossword::Wordgrid constructor
    # @param data_type `str` crossword grid source data type as used by crossword::Wordgrid constructor
    # @param wordsource `wordsrc::Wordsource` | `None` source(s) of words to use in generation
    # @param wordfilter `callable` | `None` word filtering function used in Crossword::suggest().
    # The callback prototype is as follows:
    # (`str` word) -> `bool` `True` if word can be used, `False` if it must be rejected
    # `wordfilter` may be `None` if no filtering is required.
    # @param pos `str` | `list` | `tuple` | `None` word part-of-speech filter:
    # can be a list/tuple (e.g. ['N', 'V']), a single str, e.g. 'N';
    # the value of 'ALL' or `None` means no part-of-speech filter
    # @param log `str` | `None` stream or file path to output debugging info (log messages); may be one of:
    #   * 'stdout' (default): current console stream
    #   * 'stderr': error console stream
    #   * file path: path to output (text) file
    #   * empty string or `None`: no logging will be made
    # @param bufferedlog `bool` whether the log should be buffered (or written on disk only on destruction)
    # or not buffered (default), when log messages will be written immediately
    # @param kwargs `keyword args` additional args passed to crossword::Wordgrid constructor, like:
    # `info`, `on_reset`, `on_clear`, `on_change`, `on_clear_word`, `on_putchar` etc.
    def __init__(self, data=None, data_type='grid', wordsource=None, wordfilter=None, 
                 pos='N', log='stdout', bufferedlog=False, **kwargs):
        ## `str` | `list` crossword grid source data type as used by crossword::Wordgrid constructor
        self.data = DEFAULT_GRID if (data is None and data_type == 'grid') else data
        ## `str` crossword grid source data type as used by crossword::Wordgrid constructor
        self.data_type = data_type
        ## `set` of used words (to rule out duplicate words in CW)
        self.used = set()
        # init Wordgrid
        self.init_data(**kwargs)
        ## `wordsrc::Wordsource` source(s) of words to use in generation
        self.wordsource = wordsource
        ## `callable` | `None` word filtering function used in Crossword::suggest()
        self.wordfilter = wordfilter
        ## `str` | `list` | `tuple` | `None` word part-of-speech filter
        self.pos = pos if (pos and pos != 'ALL') else None
        ## `bool` whether the log should be buffered (or written on disk only on destruction)
        self.bufferedlog = bufferedlog        
        # initialize log stream (if set)
        self.setlog(log)
        
    ## Destructor: flushes and closes log file (if present).
    def __del__(self):
        self.closelog()
        
    ## Initializes the crossword grid data
    # @param kwargs `keyword args` args passed to crossword::Wordgrid constructor
    def init_data(self, **kwargs):
        ## `crossword::Wordgrid` internal crossword grid object
        self.words = Wordgrid(data=self.data, data_type=self.data_type, info=CWInfo(), **kwargs)
        self.reset_used()
        ## `float` start time - used in generate() to mark elapsed time
        self.time_start = timeit.default_timer()
            
    ## Initializes Crossword::log to point to the relevant output stream.
    # @param log `str` | `None` output stream for debug messages, any of:
    #   * 'stdout' (default): standard console output
    #   * 'stderr': error console stream
    #   * file path: path to output (text) file
    #   * empty string or `None`: no logging will be made
    # @see _log()
    def setlog(self, log=''):
        self._slog = log
        self.closelog()
        if log == 'stdout':
            ## output stream (file) for debug messages
            self.log = sys.stdout
        elif log == 'stderr':
            self.log = sys.stderr
        elif log == '' or log is None:
            self.log = None
        else:
            self.log = open(log, 'w', encoding=ENCODING, buffering=-1 if self.bufferedlog else 1)        
            
    ## Prints debug/log message to Crossword::log with optional line-ending char.
    # @param what `str` debug/log message to print
    # @param end `str` optional line-ending
    def _log(self, what, end='\n'):
        try:
            if self.log: print(what, file=self.log, end=end)
        except:
            self.setlog(self._slog)
            if self.log: print(what, file=self.log, end=end)
            
    ## @brief Replaces the text representation of a given word.
    # See description of arguments in Wordgrid::change_word().
    # Reimplemented to remove the old word from Crossword::used.
    def change_word(self, word, new_word):
        if not hasattr(self, 'words'): return
        self.used.discard(self.words.get_word_str(word))
        crosses = self.words.intersects_of(word, False)
        for w in crosses:
            self.used.discard(self.words.get_word_str(w))
        self.words.change_word(word, new_word)
        self.used.add(self.words.get_word_str(word))
        
    ## @brief Clears the given word making its characters blank.
    # See description of arguments in Wordgrid::clear_word().
    # Reimplemented to remove the old word from Crossword::used.
    def clear_word(self, word, force_clear=False):
        if not hasattr(self, 'words'): return
        self.used.discard(self.words.get_word_str(word))
        crosses = self.words.intersects_of(word, False)
        for w in crosses:
            self.used.discard(self.words.get_word_str(w))
        self.words.clear_word(word, force_clear)
        
    ## @brief Clears the crossword grid (making all words blank).
    # See description of arguments in Wordgrid::clear().
    # Reimplemented to clear Crossword::used.
    def clear(self):
        # clear USED list
        self.used.clear()
        # clear cw grid
        self.words.clear()

    ## Prints all words currently contained in Crossword::used list.
    def print_used(self):
        for wstr in self.used:
            print(wstr)
            
    ## Flushes and closes Crossword::log if it points to a file.
    def closelog(self):
        if getattr(self, 'log', None) and self.log != sys.stdout and self.log != sys.stderr:
            self.log.close()
            
    ## Updates the Crossword::used list adding the completed (pre-set) words.
    def add_completed(self):
        for w in self.words.words:
            if self.words.is_word_complete(w):
                self.used.add(self.words.get_word_str(w))

    ## Resets the Crossword::used list (clears and re-adds all completed words).
    def reset_used(self):
        self.used.clear()
        self.add_completed()
        #self.print_used()
        
    ## @brief Fetches suggestions for the given word from the datasets (Crossword::wordsource).
    # The method accounts for the corresponding rules / filters in Crossword::wordfilter
    # and screens off items found in Crossword::used.
    # @param word `str` word pattern to look for in the word source (Crossword::wordsource),
    # e.g. 'f_th__' (will fetch 'father')
    def suggest(self, word):
        # define filtering function 
        def filt(sug):
            # check if word is not in USED list
            not_in_used = not sug in self.used
            # combine that with custom self.wordfilter function, if set
            return (not_in_used and self.wordfilter(sug)) if self.wordfilter else not_in_used
        
        # get suggestions (list) from word source
        return self.wordsource.fetch(word, BLANK, self.pos, filt)
    
    ## @brief Creates a sequential generation path (list of words) forming a connected graph.
    # All words in path are connected through intersections.
    # Algorithm starts from first non-complete word (with one or more blanks),
    # then recursively adds each intersecring word using DFS (depth-first search).
    # The resulting path contains all the words in the CW if `chain_paths == True`,
    # or a single connected graph (list) of words if `chain_paths == False`.
    # @param start_word `Word` the initial word from which generation will start;
    # if `None`, the first incomplete word will be taken
    # @param path `list` pointer to the list of words forming the path (will be 
    # updated by the function)
    # @param recurse `int` the current recursion depth (position on stack);
    # this arg must be zero when starting path generation; each recursive call
    # will increment it and each return will decrement it
    # @param chain_paths `bool` whether to merge all word graphs together into one path (`True`),
    # or make one connected path starting from `start_word` (`False`).
    # In essence, setting this arg to `False` (default) may be useful when
    # generating CW block-wise, where each graph (block of words)
    # is not connected with the others by intersections. In this case,
    # concurrent generation might be used.
    # @param word_filter `callable` filter function to exclude words from search tree.
    # Callback prototype is as follows:
    # (`Word` object) -> `bool` `True` to exclude, `False` to include in path
    def make_path(self, start_word=None, path=[], recurse=0, chain_paths=False, word_filter=None):
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
            
    ## @brief Generates crossword using the iterative algorithm.
    # @warning        
    # Currently the iterative algo does a good job ONLY for fully blank word grids.
    # For partically filled grids, it will generate INCORRECT words, since
    # the traversal path is generated STATICALLY only once and is not
    # amended during word generation. The path exludes all words in USED list,
    # so the algo will fit words without checking how they intersect with existing
    # (used) words in the grid. While this caveat will be dealt with later,
    # prefer the Recursive algo for word grids with some words filled.
    # @param timeout `float` timeout in seconds after which time the generation 
    # will be interrupted with a CWTimeoutError exception.
    # `None` value (default) means no timeout check.
    # @param stopcheck `callable` callback function that must return `True` 
    # to stop the generation and F`alse to continue.
    # If `None` is passed, no stop check is performed.
    # @param on_progress `callable` callback function to monitor currrent generation progress.
    # Prototype is:
    # ([Crossword] this object, `int` completed words count, `int` total words count) -> `None`
    # @returns `bool` `True` on success (all words in CW are filled) and `False` otherwise
    def generate_iter(self, timeout=None, stopcheck=None, on_progress=None):
        # if CW complete, return True
        if self.words: 
            self._log(_(f"\n\tCompleted CW!"))
            return True
        
        self._log(_('Creating word paths...'))
        
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
        
        self._log(_("Created {} paths").format(len(paths)))
        
        # this list will contain Boolean generation results for each path (block of words)
        results = []

        # report progress
        if on_progress:
            on_progress(self, self.words._word_count(self.words.is_word_complete), len(self.words.words))
        
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
                    self._log(_("\nNext word = [{}]").format(self.words.print_word(p[i]['w'])))
                    
                # get string representation of next word in path
                s_word = self.words.get_word_str(p[i]['w'])
                
                # skip word if it's already in USED list
                if s_word in self.used: 
                    self._log(_("Skipping [{}] (found in USED)...").format(s_word))
                    i += 1
                    continue
                
                # get new suggestions from word source if 'sug' is None
                if p[i]['sug'] is None:                    
                    p[i]['sug'] = self.suggest(s_word) 
                    self._log(_("Fetched {} suggestions for [{}]").format(len(p[i]['sug']), s_word))
                    
                # check timeout
                if self.timeout_happened(timeout): raise CWTimeoutError()
                # check for stopping criteria
                if stopcheck and stopcheck(): raise CWStopCheck()
                    
                # if suggestions returned an empty list (means we can't go on with generation)
                if len(p[i]['sug']) == 0:
                    
                    self._log(_("No suggestions for [{}]!").format(s_word))
                    # reset 'sug' list to None (to possibly re-generate on next step)
                    p[i]['sug'] = None
                    self._log(_("Clearing [{}]...").format(s_word), end='')
                    # clear word forcibly, i.e. set ALL characters to BLANK
                    # (this word is unusable as it is, so we must clear it thoroughly)
                    # at the same time, discard word and its intersects from USED list
                    self.clear_word(p[i]['w'], True)

                    # report progress
                    if on_progress:
                        on_progress(self, self.words._word_count(self.words.is_word_complete), len(self.words.words))
                    
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
                                    self._log(_("Clearing [{}]...").format(self.words.print_word(wd['w'])), end='')
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

                        # report progress
                        if on_progress:
                            on_progress(self, self.words._word_count(self.words.is_word_complete), len(self.words.words))
                      
                        # go back to [i]-th path element (word) -- 
                        # it will have been cleared by now, so we'll re-generate it and step forward as usual
                        continue
                    
                    # if we CANNOT go back (we're already or still at first word...)
                    else:
                        # set res to False, since we've failed to generate the current path
                        self._log(_('Start node reached; unable to generate for path!'))
                        res = False
                        # break from current path, go to next one (if any)
                        break
                
                # otherwise, if suggestions are not empty
                else:
                    # remove last suggestion from list and use it for current word
                    # (removing is necessary to be able to step back through or break from path
                    # when all the suggestions are exhausted)
                    sug_word = self.wordsource.pop_word(p[i]['sug'])
                    self._log(_("Trying '{}' for [{}]...").format(sug_word, self.words.get_word_str(p[i]['w'])))
                    # write suggestion to current word (store in word grid)
                    # add new word to USED list (to mark as 'used' and 'visited')
                    self.words.change_word(p[i]['w'], sug_word)
                    # increment path index to step forward to next word in path
                    i += 1
                    # report progress
                    if on_progress:
                        on_progress(self, self.words._word_count(self.words.is_word_complete), len(self.words.words))
                    
            # add generation result for current path to results list
            results.append(res)
            self._log(_("\n\tCompleted path with result = {}").format(res))
            
        self._log(_(f"\n\tCompleted CW!"))
        # return True if all paths have been generated successfully and False otherwise
        return all(results)
        
    ## Generates crossword using the recursice algorithm.
    # @param start_word `Word` the initial word from which generation will start;
    # if `None`, the first incomplete word will be taken
    # @param recurse_level `int` the current recursion depth (position on stack);
    # this arg must be zero when starting generation; each recursive call
    # will increment it and each return will decrement it
    # @param timeout `float` timeout in seconds after which time the generation 
    # will be interrupted with a CWTimeoutError exception.
    # `None` value (default) means no timeout check.
    # @param stopcheck `callable` callback function that must return `True` 
    # to stop the generation and `False` to continue.
    # If `None` is passed, no stop check is performed.
    # @param on_progress `callable` callback function to monitor currrent generation progress.
    # Prototype is:
    # ([Crossword] this object, `int` completed words count, `int` total words count) -> `None`
    # @returns `bool` `True` on success (all words in CW are filled) and `False` otherwise
    def generate_recurse(self, start_word=None, recurse_level=0, timeout=None, stopcheck=None, on_progress=None):
        # check timeout
        if self.timeout_happened(timeout): raise CWTimeoutError()
        # check for stopping criteria
        if stopcheck and stopcheck(): raise CWStopCheck()
                        
        # words must be a valid non-empty container
        if getattr(self, 'words', None) is None:
            raise CWError(_('Words collection is not initialized!')) 
                    
        rec_level = recurse_level

        # report progress
        if on_progress:
            on_progress(self, self.words._word_count(self.words.is_word_complete), len(self.words.words))
        
        # find first incomplete word if start_word == None
        if start_word is None:
            start_word = self.words.find_incomplete(exclude=lambda w: self.words.get_word_str(w) in self.used)
            if start_word is None: return True
            
        # if CW is fully completed, clear USED and return True
        # if len(self.words) == len(self.used): return True
        
        s_word = self.words.get_word_str(start_word)
                       
        # return True (success of generation cycle) if start_word is found in the USED list
        if s_word in self.used: return True
                       
        self._log(_("{}New start word is: {}").format((LOG_INDENT * rec_level), self.words.print_word(start_word)))
            
        # fetch list of suggested words for start_word
        suggested = self.suggest(s_word)
        # if nothing could be fetched return False
        if not suggested:
            self._log(_("{}Unable to generate CW for word '{}'!").format((LOG_INDENT * rec_level), s_word))
            return False
        
        self._log(_("{}Fetched {} suggestions").format((LOG_INDENT * rec_level), len(suggested)))
        
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
            
            self._log(_("{}Trying '{}' for '{}'...").format((LOG_INDENT * rec_level), sugg_word, s_word))
            # replace start_word with next suggestion
            self.words.change_word(start_word, sugg_word)
            # add it to USED list (for next suggest() and generate() calls)
            self.used.add(sugg_word)  
            
            self._log(f"\n{str(self.words)}\n")
            
            # find intersecting words (go for DFS algorithm), don't retrieve coordinates (just words)
            crosses = self.words.intersects_of(start_word, False)
            # if there are no intersects, return True (done current cycle)
            if not crosses: 
                self._log(_("{}No crosses for '{}'").format((LOG_INDENT * rec_level), s_word))
                return True
            
            self._log(_("{}Found {} crosses for '{}': {}").format((LOG_INDENT * rec_level), len(crosses), s_word, (repr([self.words.get_word_str(el) for el in crosses]))))
            
            # iterate over the intersecting words
            
            for cross in crosses:
                
                # check timeout
                if self.timeout_happened(timeout): raise CWTimeoutError()
                # check for stopping criteria
                if stopcheck and stopcheck(): raise CWStopCheck()

                # skip already used words
                if self.words.get_word_str(cross) in self.used:
                    self._log(_("{}Skipping cross '{}'...").format((LOG_INDENT * rec_level), self.words.get_word_str(cross)))
                    ok = True
                    continue
                                
                # increment recurse level
                rec_level += 1
                # attempt to generate from current intersect
                res = self.generate_recurse(cross, rec_level, timeout, stopcheck, on_progress)
                # decrement recurse level
                rec_level -= 1
                                    
                if res: 
                    self._log(_("{}Generated for cross '{}'").format((LOG_INDENT * rec_level), self.words.get_word_str(cross)))
                    # report progress
                    if on_progress:
                        on_progress(self, self.words._word_count(self.words.is_word_complete), len(self.words.words))
                    # set OK to True on success (go to next intersect)
                    ok = True
                    # return True if CW is complete
                    if len(self.words) == len(self.used): return True
                    
                else:
                    # if failed to generate, restore current word to previous (unfilled)
                    self._log(_("{}Failed to generate for cross '{}', restoring grid...").format((LOG_INDENT * rec_level), self.words.get_word_str(cross)))
                    # discard the current (failed) intersect from USED
                    self.used.discard(self.words.get_word_str(cross))
                    # restore the old word (the one before diving into recursive generation)
                    self.words.change_word(start_word, old_start_word)
                    # report progress
                    if on_progress:
                        on_progress(self, self.words._word_count(self.words.is_word_complete), len(self.words.words))
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
            return True if recurse_level > 0 else self.generate_recurse(None, 0, timeout, stopcheck, on_progress)
        
        # otherwise everything is sad...
        self._log(_("{}Unable to generate CW for word '{}'!").format((LOG_INDENT * rec_level), str(start_word)))
        # report progress
        if on_progress:
            on_progress(self, self.words._word_count(self.words.is_word_complete), len(self.words.words))
        return False
    
    ## @brief Checks if the generation operation (or whatever) has timed out.
    # The method gets the elapsed time between the current timer and Crossword::time_start
    # and checks this value against its 'timeout' argument.
    # @param timeout `float` | `int` timeout value to check (in seconds)
    # @returns `bool` `True` if the elapsed time is equal or greater than `timeout`; `False` otherwise
    def timeout_happened(self, timeout=None):
        return ((timeit.default_timer() - self.time_start) >= timeout) if not timeout is None else False
    
    ## Generates (fills) the crossword (grid) using the given generation method (iterative / recursive).
    # @param method `str`: generation method, one of:
    #     * 'iter': use the iterative algorithm
    #     * 'recurse': use the recursive algorithm
    #     * `None` or empty string (default): use recursive algo if cw is fully blank and iter othwerwise
    # @param timeout `float`: terminate generation after the lapse of this many seconds;
    # if `None`, no timeout is set
    # @param stopcheck `callable`: called by generation methods to check if termination is required:
    # see this argument in generate_recurse() and generate_iter()
    # @param onfinish `callable`: called at completion; callback prototype is:
    # onfinish(elapsed: float) -> `None`, where `elapsed: float`: seconds elapsed during generation
    # @param ontimeout `callable`: called at timeout error; callback prototype is:
    # ontimeout(timeout: float) -> `None`, where `timeout: float`: timeout seconds
    # @param onstop `callable`: called if the generation was interrupted via stopcheck; prototype is:
    # onstop() -> `None`
    # @param onerror `callable`: called on uncaught exception; prototype is:
    # onerror(err: Exception) -> `None`, where `err: Exception`: the raised exception 
    # @param onvalidate `callable`: called on validating cw words; prototype is:
    # onvalidate(bad_words: list or `None`) -> `None`, where `bad_word`: `list` of unmatched words or `None` if successful
    # (see validate())
    # @param on_progress `callable`: callback function to monitor currrent generation progress:
    # see this argument in generate_recurse() and generate_iter()
    # @returns `bool` `True` on successful generation and `False` on failure.
    def generate(self, method=None, timeout=60.0, stopcheck=None, 
                 onfinish=None, ontimeout=None, onstop=None, onerror=None, onvalidate=None, on_progress=None):
        # check source
        if not self.wordsource:
            self._log(_('No valid word source for crossword generation!'))
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
            # report progress
            if on_progress:
                on_progress(self, self.words._word_count(self.words.is_word_complete), len(self.words.words))

            if method == 'iter':
                self._log("USING ITERATIVE ALGORITHM...")
                res = self.generate_iter(timeout=timeout, stopcheck=stopcheck, on_progress=on_progress) 
            elif method == 'recurse':
                self._log("USING RECURSIVE ALGORITHM...")
                res = self.generate_recurse(timeout=timeout, stopcheck=stopcheck, on_progress=on_progress)
            elif not method:
                self._log("AUTO SELECTING ALGORITHM...")
                if self.words.count_incomplete() < len(self.words):
                    # cw has some completed words, use recursive ago
                    self._log("USING RECURSIVE ALGORITHM...")
                    res = self.generate_recurse(timeout=timeout, stopcheck=stopcheck, on_progress=on_progress)
                else:
                    # cw is fully blank, use iterative algo
                    self._log("USING ITERATIVE ALGORITHM...")
                    res = self.generate_iter(timeout=timeout, stopcheck=stopcheck, on_progress=on_progress)
            else:
                raise CWError(_("'method' argument ({}) is not valid! Must be one of: 'iter', 'recurse', or None / empty string.").format(repr(method)))
        
        except CWTimeoutError:
            self._log(_("TIMED OUT AT {} SEC!").format(timeout))
            if ontimeout: ontimeout(timeout)
            
        except CWStopCheck:
            self._log(_(f"STOPPED!"))
            if onstop: onstop()
            
        except (CWError, Exception) as err:
            if onerror: onerror(err)

        # report progress
        if on_progress:
            on_progress(self, self.words._word_count(self.words.is_word_complete), len(self.words.words))
            
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
        self._log(_("GENERATION COMPLETED IN {:.1f} SEC.").format(elapsed))
        if onfinish: onfinish(elapsed)
        return res
    
    ## Validates all completed words against the word list (checks they are all present).
    # @returns `list` | `None` list of unmatched words (those not found in Crossword::wordsource)
    # or `None` if all words were matched
    def validate(self):
        # call word source's check_bad() function on all words in CW
        lst_bad = list(filter(lambda w: not self.wordsource.check(w, self.pos, self.wordfilter), self.words.word_list()))
        # if lst_bad is not empty, it will contain words not found in the word source
        if lst_bad:
            self._log(_("No database results for {}!").format(repr(lst_bad)))
            return lst_bad
        else:
            self._log(_('CHECK OK'))
            return None
    
    ## String converter operator overload: outputs Crossword object as a crossword grid.
    def __str__(self):
        return str(self.words)

    ## Creates a crossword grid using one of the four basic 2x2 patterns.
    # @param cols `int` number of columns in grid, >= 2
    # @param rows `int` number of rows in grid, >= 2
    # @param base_pattern `int` basic 2x2 pattern, one of:
    # <pre>
    # 1 =     [*][_]
    #         [_][_]
    # 2 =     [_][*]
    #         [_][_]
    # 3 =     [_][_]
    #         [*][_]
    # 4 =     [_][_]
    #         [_][*]
    # </pre>
    # @returns `str` concatenated (newline-delimited) grid string
    @staticmethod
    def basic_grid(cols, rows, base_pattern=1):
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