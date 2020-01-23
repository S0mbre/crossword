# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

from PyQt5 import QtGui, QtCore, QtWidgets
import json, os

from utils.globalvars import *

# ******************************************************************************** #

class CWSettings:
    
    settings = { \
    'gui': {
        'theme': 'Fusion', 'toolbar_pos': 0, 'win_pos': (300, 300), 'win_size': (800, 500),
        'toolbar_actions': ['act_new', 'act_open', 'act_save', 'act_saveas', 'act_share', 'SEP', 
                            'act_edit', 'act_addrow', 'act_delrow', 'act_addcol', 'act_delcol', 'SEP', 
                            'act_reflect', 'SEP', 'act_gen', 'act_clear', 'act_clear_wd', 'act_erase_wd', 
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
            'timeout': 5,
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
            'root_folder': '', 'user': '', 'use_own_browser': True
        },
    'common':
        {
            'temp_dir': '', 'autosave_cw': True, 'lang': ''
        }
    } # settings
         
    @staticmethod
    def validate_file(filepath=SETTINGS_FILE):
        def get_dic_str(d):
            if not isinstance(d, dict): return ''
            vals = []
            for k in sorted(d.keys()):
                l = get_dic_str(d[k])                
                vals.append(f"{k}: {l}" if l else k)                
            return sorted(vals)

        if not os.path.isfile(filepath): return None
        with open(filepath, 'r', encoding=ENCODING) as fsettings:
            try:
                d = json.load(fsettings)
            except:
                return None
            if get_dic_str(d) == get_dic_str(CWSettings.settings):
                return d
        return None

    @staticmethod     
    def save_to_file(filepath=SETTINGS_FILE):    
        with open(filepath, 'w', encoding=ENCODING) as fsettings:
            json.dump(CWSettings.settings, fsettings, indent='\t')            
    
    @staticmethod
    def load_from_file(filepath=SETTINGS_FILE):
        d = CWSettings.validate_file(filepath)
        if not d:
            raise Exception(_("File '{}' is unavailable or has an invalid format!").format(filepath))
        CWSettings.settings.update(d)