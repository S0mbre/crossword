# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package pycross.guisettings
# Stores a single global configurations object - CWSettings::settings
# together with methods to load from and save to compressed JSON files.
from PyQt5 import QtGui, QtCore, QtWidgets
import json, os, gzip

from utils.globalvars import SETTINGS_FILE, MAX_RESULTS, ENCODING

# ******************************************************************************** #

## Application settings class.
class CWSettings:

    ## global app settings dictionary synched with settings files
    # @see `pycross::forms::SettingsDialog`
    settings = { \
    'gui': {
        'theme': 'Fusion', 'toolbar_pos': 0, 'win_pos': (300, 300), 'win_size': (800, 500),
        'toolbar_actions': ['act_new', 'act_open', 'act_save', 'act_saveas', 'act_share', 'SEP',
                            'act_undo', 'act_redo', 'SEP', 'act_edit', 'SEP', 'act_gen',
                            'act_clear', 'act_clear_wd', 'act_erase_wd',
                            'act_suggest', 'act_lookup', 'act_editclue', 'SEP', 'act_wsrc', 'act_info',
                            'act_stats', 'act_print', 'SEP', 'act_config', 'act_update', 'act_help']
        },
    'cw_settings': {'timeout': 60.0, 'method': 'recurse', 'pos': 'N', 'log': None},
    'grid_style': {'scale': 100, 'show': True, 'line': QtCore.Qt.SolidLine, 'header': False,
                  'cell_size': 50.0, 'line_color': QtGui.QColor(QtCore.Qt.gray).rgba(),
                  'line_width': 1,
                  'active_cell_color': 4294967040,
                  'char_case': 'upper',
                  'numbers': {'show': True, 'color': QtGui.QColor(QtCore.Qt.gray).rgba(),
                              'font_size': 8, 'font_name': 'Arial',
                              'font_weight': QtGui.QFont.Normal, 'font_italic': True}},
    'cell_format': \
        {'NORMAL': # normal cells
            {'bg_color': QtGui.QColor(QtCore.Qt.white).rgba(), 'bg_pattern': QtCore.Qt.SolidPattern,
             'fg_color': QtGui.QColor(QtCore.Qt.black).rgba(), 'fg_pattern': QtCore.Qt.SolidPattern,
             'flags': int(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled),
             'font_name': 'Arial', 'font_size': 14, 'font_weight': QtGui.QFont.DemiBold, 'font_italic': False, 'align': QtCore.Qt.AlignCenter},
         'HILITE': # highlighted cells
            {'bg_color': 4294966721, 'bg_pattern': QtCore.Qt.SolidPattern, 'fg_color': QtGui.QColor(QtCore.Qt.black).rgba(),
             'fg_pattern': QtCore.Qt.SolidPattern, 'flags': int(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled),
             'font_name': 'Arial', 'font_size': 14, 'font_weight': QtGui.QFont.DemiBold, 'font_italic': False, 'align': QtCore.Qt.AlignCenter},
         'BLANK': # blank
            {'bg_color': QtGui.QColor(QtCore.Qt.white).rgba(), 'bg_pattern': QtCore.Qt.SolidPattern,
             'fg_color': QtGui.QColor(QtCore.Qt.transparent).rgba(), 'fg_pattern': QtCore.Qt.SolidPattern,
             'flags': int(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled),
             'font_name': 'Arial', 'font_size': 14, 'font_weight': QtGui.QFont.DemiBold, 'font_italic': False, 'align': QtCore.Qt.AlignCenter},
         'FILLER': # filler
             {'bg_color': QtGui.QColor(QtCore.Qt.black).rgba(), 'bg_pattern': QtCore.Qt.SolidPattern,
              'fg_color': QtGui.QColor(QtCore.Qt.transparent).rgba(), 'fg_pattern': QtCore.Qt.SolidPattern,
              'flags': int(QtCore.Qt.NoItemFlags), 'font_name': 'Arial', 'font_size': 14,
              'font_weight': QtGui.QFont.DemiBold, 'font_italic': False, 'align': QtCore.Qt.AlignCenter},
         'FILLER2': # filler2
             {'bg_color': QtGui.QColor(QtCore.Qt.gray).rgba(), 'bg_pattern': QtCore.Qt.SolidPattern,
              'fg_color': QtGui.QColor(QtCore.Qt.transparent).rgba(), 'fg_pattern': QtCore.Qt.SolidPattern,
              'flags': int(QtCore.Qt.NoItemFlags), 'font_name': 'Arial', 'font_size': 14,
              'font_weight': QtGui.QFont.DemiBold, 'font_italic': False, 'align': QtCore.Qt.AlignCenter}
         },
    'wordsrc': {'maxres': MAX_RESULTS, 'sources': [], 'excluded': {'words': [], 'regex': False}},
    'clues':
        {'NORMAL':
            {
                'bg_color': 4294967295, 'bg_pattern': QtCore.Qt.SolidPattern, 'fg_color': QtGui.QColor(QtCore.Qt.black).rgba(),
                'font_name': 'Arial', 'font_size': 9, 'font_weight': QtGui.QFont.Normal, 'font_italic': False, 'align': QtCore.Qt.AlignLeft
            },
         'INCOMPLETE':
            {
                'bg_color': 4294957016, 'bg_pattern': QtCore.Qt.SolidPattern, 'fg_color': QtGui.QColor(QtCore.Qt.black).rgba()
            },
         'COMPLETE':
            {
                'bg_color': 4292870103, 'bg_pattern': QtCore.Qt.SolidPattern, 'fg_color': QtGui.QColor(QtCore.Qt.black).rgba()
            },
         'SURROUNDING':
            {
                'bg_color': 4294967295
            },
         'columns': [{'name': 'Direction', 'visible': True, 'width': -1},
                     {'name': 'No.', 'visible': True, 'width': -1},
                     {'name': 'Clue', 'visible': True, 'width': -1},
                     {'name': 'Letters', 'visible': True, 'width': -1},
                     {'name': 'Reply', 'visible': True, 'width': -1}]
        },
    'lookup':
        {
            'default_lang': 'en',
            'dics': {'show': True, 'exact_match': False, 'bad_pos': 'UNKNOWN', 'show_pos': True,
                       'mw_apikey': '', 'yandex_key': ''},
            'google': {'show': True, 'exact_match': False, 'file_types': [], 'lang': [],
                       'country': [], 'interface_lang': [], 'link_site': '',
                       'related_site': '', 'in_site': '', 'nresults': -1, 'safe_search': False,
                       'api_key': '', 'api_cse': ''}
        },
    'printing':
        {
            'margins': [12, 16, 12, 20], 'layout': 'auto', 'font_embed': True, 'antialias': True,
            'print_cw': True, 'print_clues': True, 'clear_cw': True, 'print_clue_letters': True,
            'print_info': True, 'cw_title': '<t>', 'clues_title': 'Clues',
            'header_font': {
                'font_name': 'Verdana', 'font_size': 20, 'color': QtGui.QColor(QtCore.Qt.blue).rgba(),
                'font_weight': QtGui.QFont.Bold, 'font_italic': False},
            'info_font': {
                'font_name': 'Arial', 'font_size': 14, 'color': QtGui.QColor(QtCore.Qt.black).rgba(),
                'font_weight': QtGui.QFont.Normal, 'font_italic': False},
            'clue_number_font': {
                'font_name': 'Arial', 'font_size': 14, 'color': QtGui.QColor(QtCore.Qt.black).rgba(),
                'font_weight': QtGui.QFont.Bold, 'font_italic': False},
            'clue_font': {
                'font_name': 'Arial', 'font_size': 14, 'color': QtGui.QColor(QtCore.Qt.black).rgba(),
                'font_weight': QtGui.QFont.Normal, 'font_italic': False},
            'clue_letters_font': {
                'font_name': 'Arial', 'font_size': 14, 'color': QtGui.QColor(QtCore.Qt.black).rgba(),
                'font_weight': QtGui.QFont.Normal, 'font_italic': True},
            'color_print': True, 'openfile': True
        },
    'export':
        {
            'openfile': True, 'img_resolution': 72, 'pdf_resolution': 1200,
            'mm_per_cell': 20, 'img_output_quality': 95, 'svg_title': '<t>',
            'svg_description': '', 'clear_cw': True
        },
    'update':
        {
            'check_every': 1, 'auto_update': False,
            'only_major_versions': False,
            'logfile': 'update.log', 'restart_on_update': True
        },
    'sharing':
        {
            'account': '', 'bearer_token': '', 'use_api_key': False,
            'root_folder': 'pycross', 'user': ''
        },
    'plugins':
        {
            'thirdparty':
                {
                    'git': {'active': False, 'exepath': ''},
                    'dbbrowser': {'active': False, 'exepath': '', 'command': '-t <table> <file>'},
                    'text': {'active': False, 'exepath': '', 'command': '<file>'}
                },
            'custom': {'general': []}
        },
    'common':
        {
            'temp_dir': '', 'autosave_cw': True, 'lang': '',
            'web':
                {
                    'proxy': {'use_system': True, 'http': '', 'https': ''},
                    'req_timeout': 5
                }
        }
    }

    ## @brief Validates a settings file and returns its contents as a dictionary.
    # Validation compares the structure of the settings file contents
    # to `CWSettings::settings` and checks if the settings file
    # contains the exact same keys recursively in each root key.
    # @param filepath `str` path to the settings file to load
    # @returns `dict`|`None` settings read from the file as a Python dictionary --
    # see `CWSettings::settings`; or `None` on validation error
    # @warning The app uses GZIP compression in settings files (*.pxjson), so the
    # raw JSON data is not viewable directly when you open such files
    # in a notepad; you may still unpack them using your GZIP-compatible
    # decompression tool.
    @staticmethod
    def validate_file(filepath=SETTINGS_FILE):
        def get_dic_str(d):
            if not isinstance(d, dict): return ''
            vals = []
            for k in sorted(d.keys()):
                l = get_dic_str(d[k])
                vals.append(f"{k}: {l}" if l else k)
            return sorted(vals)

        if not os.path.isfile(filepath): 
            print(f"File '{filepath}' is unavailable!")
            return None
        with gzip.open(filepath, 'rt', encoding=ENCODING) as fsettings:
            try:
                content = fsettings.read()
                d = json.loads(content)
            except Exception as err:
                print(err)
                return None
            keys_default = get_dic_str(CWSettings.settings)
            keys_file = get_dic_str(d)
            if keys_default == keys_file:
                return d
            else:
                print("Keys don't match!")
                #print(f"DEFAULT = {keys_default}")
                #print(f"FILE = {keys_file}")
        return None

    ## Dumps the current app settings into a settings file.
    # @param filepath `str` path to the settings file to save to
    # @warning The app uses GZIP compression in settings files (*.pxjson), so the
    # raw JSON data is not viewable directly when you open such files
    # in a notepad; you may still unpack them using your GZIP-compatible
    # decompression tool.
    # @see CWSettings::load_from_file()
    @staticmethod
    def save_to_file(filepath=SETTINGS_FILE):
        content = json.dumps(CWSettings.settings, indent='\t')
        with gzip.open(filepath, 'wt', encoding=ENCODING) as fsettings:
            fsettings.write(content)

    ## Loads the app settings from a settings file.
    # @param filepath `str` path to the settings file to load from
    # @warning The app uses GZIP compression in settings files (*.pxjson), so the
    # raw JSON data is not viewable directly when you open such files
    # in a notepad; you may still unpack them using your GZIP-compatible
    # decompression tool.
    # @see CWSettings::save_to_file()
    @staticmethod
    def load_from_file(filepath=SETTINGS_FILE):
        d = CWSettings.validate_file(filepath)
        if not d:
            raise Exception("File '{}' is unavailable or has an invalid format!".format(filepath))
        CWSettings.settings.update(d)