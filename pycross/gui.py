# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package pycross.gui
# The GUI app main window implementation -- see MainWindow class.
from PyQt5 import QtGui, QtCore, QtWidgets, QtPrintSupport, QtSvg
from subprocess import Popen
import os, json, re, threading, math, traceback, webbrowser

from utils.globalvars import *
from utils.utils import *
from utils.update import Updater
from utils.onlineservices import Cloudstorage, Share
from utils.graphs import make_chart, data_from_dict
from guisettings import CWSettings
from dbapi import Sqlitedb
from forms import (MsgBox, LoadCwDialog, CwTable, ClickableLabel, CrosswordMenu, 
                    SettingsDialog, WordSuggestDialog, PrintPreviewDialog,
                    CwInfoDialog, DefLookupDialog, ReflectGridDialog, AboutDialog, 
                    ShareDialog, KloudlessAuthDialog)
from crossword import Word, Crossword, CWError, FILLER, FILLER2, BLANK
from wordsrc import DBWordsource, TextWordsource, TextfileWordsource, MultiWordsource
from browser import Browser

# ******************************************************************************** #

## Crossword generation thread class
class GenThread(QThreadStump):
    ## `QtCore.pyqtSignal` Timeout signal
    sig_timeout = QtCore.pyqtSignal(float)
    ## `QtCore.pyqtSignal` Interrupt / stop signal
    sig_stopped = QtCore.pyqtSignal()
    ## `QtCore.pyqtSignal` Crossword word validation signal
    sig_validate = QtCore.pyqtSignal('PyQt_PyObject')
    ## `QtCore.pyqtSignal` On-progress (generation) signal
    sig_progress = QtCore.pyqtSignal('PyQt_PyObject', int, int)

    ## Initializes signals binding them to callbacks passed to constructor
    def __init__(self, on_gen_timeout=None, on_gen_stopped=None, on_gen_validate=None, on_gen_progress=None,  
                 on_start=None, on_finish=None, on_run=None, on_error=None):
        super().__init__(on_start=on_start, on_finish=on_finish, on_run=on_run, on_error=on_error)
        if on_gen_timeout: self.sig_timeout.connect(on_gen_timeout)
        if on_gen_stopped: self.sig_stopped.connect(on_gen_stopped)
        if on_gen_validate: self.sig_validate.connect(on_gen_validate)
        if on_gen_progress: self.sig_progress.connect(on_gen_progress)

# ******************************************************************************** #

## Crossword sharing (in social networks) thread class
class ShareThread(QThreadStump):
    ## `QtCore.pyqtSignal` On-progress (sharing) signal
    sig_progress = QtCore.pyqtSignal(int, str)
    ## `QtCore.pyqtSignal` File upload signal
    sig_upload_file = QtCore.pyqtSignal(str, str)
    ## `QtCore.pyqtSignal` API key request signal
    sig_apikey_required = QtCore.pyqtSignal('PyQt_PyObject')
    ## `QtCore.pyqtSignal` Bearer token request signal
    sig_bearer_required = QtCore.pyqtSignal('PyQt_PyObject')
    ## `QtCore.pyqtSignal` URL prepared signal
    sig_prepare_url = QtCore.pyqtSignal(str)
    ## `QtCore.pyqtSignal` Clipboard copy signal
    sig_clipboard_write = QtCore.pyqtSignal(str)

    ## Initializes signals binding them to callbacks passed to constructor
    def __init__(self, on_progress=None, on_upload=None, on_clipboard_write=None,
                 on_apikey_required=None, on_bearer_required=None, on_prepare_url=None,
                 on_start=None, on_finish=None, on_run=None, on_error=None):
        super().__init__(on_start=on_start, on_finish=on_finish, on_run=on_run, on_error=on_error)
        if on_progress: self.sig_progress.connect(on_progress)
        if on_upload: self.sig_upload_file.connect(on_upload)
        if on_clipboard_write: self.sig_clipboard_write.connect(on_clipboard_write)
        if on_apikey_required: self.sig_apikey_required.connect(on_apikey_required)
        if on_bearer_required: self.sig_bearer_required.connect(on_bearer_required)
        if on_prepare_url: self.sig_prepare_url.connect(on_prepare_url)

# ******************************************************************************** #

## The application's main GUI window
class MainWindow(QtWidgets.QMainWindow):
    
    ## Initializes class members
    def __init__(self, **kwargs):        
        super().__init__()
        ## `crossword::Crossword` internal crossword generator object
        self.cw = None   
        ## `str` currently opened cw file                      
        self.cw_file = ''             
        ## `bool` flag showing that current cw has been changed since last save         
        self.cw_modified = True                
        ## `Word` currently selected word in grid
        self.current_word = None
        ## `QtWidgets.QTableWidgetItem` last pressed cell in cw grid
        self.last_pressed_item = None     
        ## `utils::onlineservices::Share` object     
        self.sharer = None       
        ## `wordsrc::MultiWordsource` word source instance              
        self.wordsrc = MultiWordsource()       
        ## `list` files to delete on startup / close
        self.garbage = []                      
        ## `GenThread` cw generation worker thread
        self.gen_thread = GenThread(on_gen_timeout=self.on_gen_timeout, on_gen_stopped=self.on_gen_stop, 
                                    on_gen_validate=self.on_gen_validate, on_gen_progress=self.on_gen_progress, 
                                    on_start=self.on_generate_start, on_finish=self.on_generate_finish,
                                    on_run=self.generate_cw_worker, on_error=self.on_gen_error)
        ## `ShareThread` sharer worker thread
        self.share_thread = ShareThread(on_progress=self.on_share_progress, 
            on_upload=self.on_share_upload, on_clipboard_write=self.on_share_clipboard_write,
            on_apikey_required=self.on_share_apikey_required, on_bearer_required=self.on_share_bearer_required,
            on_prepare_url=self.on_share_prepare_url,
            on_start=self.on_share_start, on_finish=self.on_share_finish, on_run=self.on_share_run,
            on_error=self.on_share_error)

        ## `list` thread list to keep track of all spawned threads
        self.threads = ['gen_thread', 'share_thread']
        
        # create window elements
        self.initUI(not kwargs.get('empty', False))
        self.setAcceptDrops(True) 
        ## `forms::SettingsDialog` instance (settings window)
        self.dia_settings = SettingsDialog(self)
        # execute actions for command-line args, if present
        self.execute_cli_args(**kwargs)

    ## Simple util method to print stuff to console.
    # @param what `str` message body
    # @param end `str` line ending
    def _log(self, what, end='\n'):
        print(what, end=end)
        
    ## Creates all window elements: layouts, panels, toolbars, widgets.
    # @param autoloadcw `bool` whether to load crossword automatically from autosave file (utils::globalvars::SAVEDCW_FILE)
    def initUI(self, autoloadcw=True):
        # actions
        self.create_actions()
        # language combo
        self.UI_create_lang_combo()
        # main toolbar
        self.UI_create_toolbar()  
        # main menu
        self.UI_create_menu()  
        # central items (cw grid and clues)
        self.UI_create_central_widget()
        # status bar
        self.UI_create_statusbar()
        # context menus
        self.UI_create_context_menus()
               
        self.setMinimumSize(500, 300)
        # the default title = 'pycrossword'
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QtGui.QIcon(f"{ICONFOLDER}/main.png"))
        # apply settings stored in CWSettings.settings
        self.apply_config(autoloadcw=autoloadcw)        
        # show window
        self.show()
        # update actions' status (enabled)
        self.update_actions()

    ## Creates the application actions (`QAction` instances) which are
    # then added to the main toolbar, main menu and context menus.
    def create_actions(self):
        ## `QtWidgets.QAction` new crossword action
        self.act_new = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/crossword.png"), _('New'))
        self.act_new.setToolTip(_('Create new crossword'))
        self.act_new.setShortcuts(QtGui.QKeySequence.New)
        self.act_new.triggered.connect(self.on_act_new)
        ## `QtWidgets.QAction` open crossword (file) action
        self.act_open = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/folder-15.png"), _('Open'))
        self.act_open.setToolTip(_('Open crossword from file'))
        self.act_open.setShortcuts(QtGui.QKeySequence.Open)
        self.act_open.triggered.connect(self.on_act_open)
        ## `QtWidgets.QAction` crossword save action
        self.act_save = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/save.png"), _('Save'))
        self.act_save.setToolTip(_('Save crossword'))
        self.act_save.setShortcuts(QtGui.QKeySequence.Save)
        self.act_save.triggered.connect(self.on_act_save)
        ## `QtWidgets.QAction` crossword save as (export) action
        self.act_saveas = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/saveas.png"), _('Save As...'))
        self.act_saveas.setToolTip(_('Save crossword as new file'))
        self.act_saveas.setShortcuts(QtGui.QKeySequence.SaveAs)
        self.act_saveas.triggered.connect(self.on_act_saveas)
        ## `QtWidgets.QAction` crossword close action
        self.act_close = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/close.png"), _('Close'))
        self.act_close.setToolTip(_('Close current crossword'))
        self.act_close.setShortcuts(QtGui.QKeySequence.Close)
        self.act_close.triggered.connect(self.on_act_close)
        ## `QtWidgets.QAction` crossword reload (from file) action
        self.act_reload = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/repeat.png"), _('Reload'))
        self.act_reload.setToolTip(_('Reload crossword from file'))
        self.act_reload.setShortcuts(QtGui.QKeySequence.Refresh)
        self.act_reload.triggered.connect(self.on_act_reload)
        ## `QtWidgets.QAction` crossword share action
        self.act_share = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/share-1.png"), _('Share'))
        self.act_share.setToolTip(_('Share crossword in social networks'))
        self.act_share.setShortcut(QtGui.QKeySequence('F10'))
        self.act_share.triggered.connect(self.on_act_share)
        ## `QtWidgets.QAction` crossword edit action (toggle editing mode)
        self.act_edit = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/edit.png"), _('Edit'))
        self.act_edit.setToolTip(_('Edit crossword'))
        self.act_edit.setCheckable(True)
        self.act_edit.setShortcut(QtGui.QKeySequence('Ctrl+e'))
        self.act_edit.toggled.connect(self.on_act_edit)   
        ## `QtWidgets.QAction` add row action
        self.act_addrow = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/add_row.png"), _('Add row'))
        self.act_addrow.setToolTip(_('Add row before selected'))
        self.act_addrow.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL, QtCore.Qt.Key_Plus))
        self.act_addrow.triggered.connect(self.on_act_addrow)     
        ## `QtWidgets.QAction` delete row action
        self.act_delrow = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/delete_row.png"), _('Delete row'))
        self.act_delrow.setToolTip(_('Delete row'))
        self.act_delrow.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL, QtCore.Qt.Key_Minus))
        self.act_delrow.triggered.connect(self.on_act_delrow)
        ## `QtWidgets.QAction` add column action
        self.act_addcol = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/add_col.png"), _('Add column'))
        self.act_addcol.setToolTip(_('Add column before selected'))
        self.act_addcol.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL, QtCore.Qt.Key_Equal))
        self.act_addcol.triggered.connect(self.on_act_addcol)         
        ## `QtWidgets.QAction` delete column action
        self.act_delcol = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/delete_col.png"), _('Delete column'))
        self.act_delcol.setToolTip(_('Delete column'))
        self.act_delcol.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL, QtCore.Qt.Key_Underscore))
        self.act_delcol.triggered.connect(self.on_act_delcol)
        ## `QtWidgets.QAction` reflect (duplicate) grid action
        self.act_reflect = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/windows-1.png"), _('Duplicate'))
        self.act_reflect.setToolTip(_('Duplicate (reflect) grid cells to any direction'))
        self.act_reflect.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL, QtCore.Qt.Key_7))
        self.act_reflect.triggered.connect(self.on_act_reflect)
        ## `QtWidgets.QAction` crossword generate (fill) action
        self.act_gen = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/flash.png"), _('Generate'))
        self.act_gen.setToolTip(_('Generate (solve) crossword'))
        self.act_gen.setShortcut(QtGui.QKeySequence('Ctrl+g'))
        self.act_gen.triggered.connect(self.on_act_gen)
        ## `QtWidgets.QAction` stop (current operation) action
        self.act_stop = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/stop-1.png"), _('Stop'))
        self.act_stop.setToolTip(_('Stop operation'))
        self.act_stop.setShortcuts(QtGui.QKeySequence.Undo)
        self.act_stop.triggered.connect(self.on_act_stop)
        self.act_stop.changed.connect(self.on_act_stop_changed)
        self.act_stop.setCheckable(True)
        ## `QtWidgets.QAction` grid clear action
        self.act_clear = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/dust.png"), _('Clear'))
        self.act_clear.setToolTip(_('Clear all words'))
        self.act_clear.setShortcut(QtGui.QKeySequence('Ctrl+d'))
        self.act_clear.triggered.connect(self.on_act_clear)
        ## `QtWidgets.QAction` clear word action
        self.act_clear_wd = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/minus.png"), _('Clear word'))
        self.act_clear_wd.setToolTip(_('Clear word'))
        self.act_clear_wd.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL, QtCore.Qt.Key_Delete))
        self.act_clear_wd.triggered.connect(self.on_act_clear_wd)
        ## `QtWidgets.QAction` erase word action
        self.act_erase_wd = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/error.png"), _('Erase word'))
        self.act_erase_wd.setToolTip(_('Erase word'))
        self.act_erase_wd.setShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL, QtCore.Qt.SHIFT, QtCore.Qt.Key_Delete))
        self.act_erase_wd.triggered.connect(self.on_act_erase_wd)
        ## `QtWidgets.QAction` suggest word action
        self.act_suggest = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/magic-wand.png"), _('Suggest word'))
        self.act_suggest.setToolTip(_('Suggest word'))
        self.act_suggest.setShortcuts(QtGui.QKeySequence.Find)
        self.act_suggest.triggered.connect(self.on_act_suggest)
        ## `QtWidgets.QAction` lookup word action
        self.act_lookup = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/worldwide.png"), _('Lookup word'))
        self.act_lookup.setToolTip(_('Lookup word definition'))
        self.act_lookup.setShortcut(QtGui.QKeySequence('Ctrl+l'))
        self.act_lookup.triggered.connect(self.on_act_lookup)
        ## `QtWidgets.QAction` go to clue action
        self.act_editclue = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/key.png"), _('Edit clue'))
        self.act_editclue.setToolTip(_('Edit clue'))
        self.act_editclue.setShortcut(QtGui.QKeySequence('Ctrl+k'))
        self.act_editclue.triggered.connect(self.on_act_editclue)
        ## `QtWidgets.QAction` edit word sources action
        self.act_wsrc = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/database-3.png"), _('Word sources'))
        self.act_wsrc.setToolTip(_('Select wordsources'))
        self.act_wsrc.setShortcut(QtGui.QKeySequence('Ctrl+m'))
        self.act_wsrc.triggered.connect(self.on_act_wsrc)
        ## `QtWidgets.QAction` show / edit crossword info action
        self.act_info = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/info1.png"), _('Info'))
        self.act_info.setToolTip(_('Show / edit crossword info (Ctrl+I)'))
        self.act_info.setShortcut(QtGui.QKeySequence('Ctrl+i'))
        self.act_info.triggered.connect(self.on_act_info)
        ## `QtWidgets.QAction` print (cw / clues) action
        self.act_print = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/print.png"), _('Print'))
        self.act_print.setToolTip(_('Print crossword and/or clues'))
        self.act_print.setShortcuts(QtGui.QKeySequence.Print)
        self.act_print.triggered.connect(self.on_act_print)
        ## `QtWidgets.QAction` configure settings action
        self.act_config = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/settings-5.png"), _('Settings'))
        self.act_config.setToolTip(_('Configure settings'))
        self.act_config.setShortcut(QtGui.QKeySequence('F11'))
        self.act_config.triggered.connect(self.on_act_config)
        ## `QtWidgets.QAction` check for update action
        self.act_update = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/cloud-computing.png"), _('Update'))
        self.act_update.setToolTip(_('Check for updates'))
        self.act_update.setShortcut(QtGui.QKeySequence('Ctrl+u'))
        self.act_update.triggered.connect(self.on_act_update)
        ## `QtWidgets.QAction` show help docs action
        self.act_help = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/info.png"), _('Help'))
        self.act_help.setToolTip(_('Show help'))
        self.act_help.setShortcuts(QtGui.QKeySequence.HelpContents)
        self.act_help.triggered.connect(self.on_act_help)
        ## `QtWidgets.QAction` show About action
        self.act_about = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/main.png"), _('About'))
        self.act_about.setToolTip(_('Show About'))
        self.act_about.setShortcut(QtGui.QKeySequence('F2'))
        self.act_about.triggered.connect(self.on_act_about)
        ## `QtWidgets.QAction` show crossword stats action
        self.act_stats = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/analytics.png"), _('Show stats'))
        self.act_stats.setToolTip(_('Show detailed crossword statistics'))
        self.act_stats.setShortcut(QtGui.QKeySequence('F9'))
        self.act_stats.triggered.connect(self.on_act_stats)
        ## `QtWidgets.QAction` quit application action
        self.act_exit = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/exit.png"), _('Quit'))
        self.act_exit.setToolTip(_('Quit application'))
        self.act_exit.setShortcuts(QtGui.QKeySequence.Quit)
        self.act_exit.triggered.connect(self.on_act_exit)
    
    ## Creates the app's main toolbar (which can also be hidden in settings).
    def UI_create_toolbar(self):
        ## `QtWidgets.QToolBar` main toolbar
        self.toolbar_main = QtWidgets.QToolBar()
        self.toolbar_main.setMovable(False)
        self.toolbar_main.toggleViewAction().setEnabled(False)
        self.toolbar_main.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.toolbar_main.customContextMenuRequested.connect(self.on_toolbar_contextmenu)        
        self.addToolBar(self.toolbar_main)

    ## Fills main toolbar from app settings (CWSettings::settings).
    def toolbar_from_settings(self):
        self.toolbar_main.clear()
        for act_ in CWSettings.settings['gui']['toolbar_actions']:
            if act_ == 'SEP':
                self.toolbar_main.addSeparator()
            else:
                self.toolbar_main.addAction(getattr(self, act_))
        # add lang combo
        self.toolbar_main.addSeparator()
        self.toolbar_main.addWidget(self.combo_lang).setVisible(True)
        self.toolbar_main.show()

    ## Creates the langugage combo box and fills it with supported languages.
    def UI_create_lang_combo(self):
        ## `QtWidgets.QComboBox` UI language combo
        self.combo_lang = QtWidgets.QComboBox()
        self.combo_lang.setEditable(False)
        for lang in APP_LANGUAGES:
            self.combo_lang.addItem(QtGui.QIcon(f"{ICONFOLDER}/{lang[3]}"), f"{lang[0]}{(' (' + lang[2] + ')') if lang[2] else ''}", lang[1])
        index = self.combo_lang.findData(CWSettings.settings['common'].get('lang', ''))
        if index >= 0:
            self.combo_lang.setCurrentIndex(index)
        self.combo_lang.currentIndexChanged.connect(self.on_combo_lang)

    ## Creates the application's main menu.
    def UI_create_menu(self):
        ## `QtWidgets.QMenu` UI main menu
        self.menu_main = self.menuBar()
        ## `QtWidgets.QMenu` 'File' menu
        self.menu_main_file = self.menu_main.addMenu(_('&File'))
        self.menu_main_file.addAction(self.act_new)
        self.menu_main_file.addSeparator()
        self.menu_main_file.addAction(self.act_open)
        self.menu_main_file.addAction(self.act_save)
        self.menu_main_file.addAction(self.act_saveas)
        self.menu_main_file.addSeparator()
        self.menu_main_file.addAction(self.act_reload)
        self.menu_main_file.addAction(self.act_close)
        self.menu_main_file.addSeparator()
        self.menu_main_file.addAction(self.act_share)
        self.menu_main_file.addSeparator()
        self.menu_main_file.addAction(self.act_print)
        self.menu_main_file.addSeparator()
        self.menu_main_file.addAction(self.act_exit)
        ## `QtWidgets.QMenu` 'Edit' menu
        self.menu_main_edit = self.menu_main.addMenu(_('&Edit'))
        self.menu_main_edit.addAction(self.act_edit)
        self.menu_main_edit.addSeparator()
        self.menu_main_edit.addAction(self.act_clear)
        self.menu_main_edit.addAction(self.act_clear_wd)
        self.menu_main_edit.addAction(self.act_erase_wd)
        self.menu_main_edit.addSeparator()
        self.menu_main_edit.addAction(self.act_suggest)
        self.menu_main_edit.addAction(self.act_lookup)
        self.menu_main_edit.addAction(self.act_editclue)
        self.menu_main_edit.addSeparator()
        self.menu_main_edit.addAction(self.act_addrow)
        self.menu_main_edit.addAction(self.act_delrow)
        self.menu_main_edit.addSeparator()
        self.menu_main_edit.addAction(self.act_addcol)        
        self.menu_main_edit.addAction(self.act_delcol)
        self.menu_main_edit.addSeparator()
        self.menu_main_edit.addAction(self.act_reflect)
        self.menu_main_edit.addSeparator()
        #self.menu_main_edit.addAction(self.act_addrow)
        #self.menu_main_edit.addAction(self.act_addcol)
        self.menu_main_edit.addSeparator()
        self.menu_main_edit.addAction(self.act_config)
        ## `QtWidgets.QMenu` 'View' menu
        self.menu_main_view = self.menu_main.addMenu(_('&View'))
        self.act_view_showtoolbar = self.menu_main_view.addAction(_('Show toolbar'))
        self.act_view_showtoolbar.setCheckable(True)
        self.act_view_showtoolbar.setChecked(True)
        self.act_view_showtoolbar.setToolTip(_('Show / hide toolbar'))
        self.act_view_showtoolbar.toggled.connect(self.on_act_view_showtoolbar)
        self.menu_main_view.addSeparator()
        self.menu_main_view.addAction(self.act_info)
        self.menu_main_view.addAction(self.act_stats)
        ## `QtWidgets.QMenu` 'Generate' menu
        self.menu_main_gen = self.menu_main.addMenu(_('&Generate'))
        self.menu_main_gen.addAction(self.act_gen)
        self.menu_main_gen.addSeparator()
        self.menu_main_gen.addAction(self.act_wsrc)
        ## `QtWidgets.QMenu` 'Help' menu
        self.menu_main_help = self.menu_main.addMenu(_('&Help'))
        self.menu_main_help.addAction(self.act_help)
        self.menu_main_help.addSeparator()
        self.menu_main_help.addAction(self.act_update)
        self.menu_main_help.addSeparator()
        self.menu_main_help.addAction(self.act_about)
    
    ## Creates the main UI elements: the crossword grid and clues table.
    def UI_create_central_widget(self):
        ## `QtWidgets.QSplitter` central widget
        self.splitter1 = QtWidgets.QSplitter()
        ## `QtWidgets.QWidget` cw layout container
        self.cw_widget = QtWidgets.QWidget()
        ## `QtWidgets.QVBoxLayout` cw layout
        self.layout_vcw = QtWidgets.QVBoxLayout()
        ## `forms::CwTable` cw grid
        self.twCw = CwTable(on_key=self.on_cw_key)
        self.twCw.setSortingEnabled(False)
        self.twCw.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.twCw.setDropIndicatorShown(True)
        self.twCw.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.twCw.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.twCw.setTabKeyNavigation(False)
        self.twCw.setGridStyle(CWSettings.settings['grid_style']['line'])
        self.twCw.setShowGrid(CWSettings.settings['grid_style']['show'])
        self.twCw.horizontalHeader().setVisible(CWSettings.settings['grid_style']['header'])
        self.twCw.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.twCw.verticalHeader().setVisible(CWSettings.settings['grid_style']['header'])
        self.twCw.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.twCw.clearSelection()
        self.twCw.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.twCw.customContextMenuRequested.connect(self.on_twCw_contextmenu)
        self.twCw.itemClicked.connect(self.on_cw_item_clicked)
        self.twCw.currentItemChanged.connect(self.on_cw_current_item_changed)
        
        ## `QtWidgets.QSlider` cw scale slider
        self.slider_cw_scale = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_cw_scale.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.slider_cw_scale.setMinimum(100)
        self.slider_cw_scale.setMaximum(300)
        self.slider_cw_scale.setSingleStep(10)
        self.slider_cw_scale.setPageStep(50)
        #self.slider_cw_scale.setTickPosition(QtWidgets.QSlider.TicksBelow)
        #self.slider_cw_scale.setTickInterval(10)
        self.slider_cw_scale.setValue(CWSettings.settings['grid_style']['scale'])
        ## `QtWidgets.QLabel` cw table scale indicator
        self.l_cw_scale = QtWidgets.QLabel()
        self.l_cw_scale.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.slider_cw_scale.valueChanged.connect(self.on_slider_cw_scale)
        ## `QtWidgets.QHBoxLayout` cw table scale layout
        self.layout_cw_scale = QtWidgets.QHBoxLayout()
        self.layout_cw_scale.addWidget(self.slider_cw_scale)
        self.layout_cw_scale.addWidget(self.l_cw_scale)
        self.layout_vcw.addWidget(self.twCw)
        self.layout_vcw.addLayout(self.layout_cw_scale)
        # set layout to container
        self.cw_widget.setLayout(self.layout_vcw)        
        # add to splitter
        self.splitter1.addWidget(self.cw_widget)

        ## `QtWidgets.QTreeView` clues table
        self.tvClues = QtWidgets.QTreeView()
        self.tvClues.setDragEnabled(True)
        self.tvClues.setAcceptDrops(True)
        self.tvClues.setDropIndicatorShown(True)
        self.tvClues.setSortingEnabled(True)   
        self.tvClues.setSelectionMode(1)
        self.tvClues.setSelectionBehavior(1)       
        self.tvClues.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        #self.tvClues.customContextMenuRequested.connect(self.on_tvClues_contextmenu)
        self.splitter1.addWidget(self.tvClues)        
        
        # add splitter1 as central widget
        self.setCentralWidget(self.splitter1)
        # update cw and actions
        self.update_cw()
    
    ## Creates the main window's status bar.
    def UI_create_statusbar(self):
        ## `QtWidgets.QStatusBar` main status bar
        self.statusbar = QtWidgets.QStatusBar()        
        self.statusbar.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed) 
        ## `QtWidgets.QProgressBar` progress bar inside status bar (hidden by default)
        self.statusbar_pbar = QtWidgets.QProgressBar(self.statusbar)
        self.statusbar_pbar.setTextVisible(True)
        self.statusbar_pbar.setRange(0, 100)
        self.statusbar_pbar.setValue(0)
        self.statusbar_pbar.setVisible(False)
        self.statusbar.addPermanentWidget(self.statusbar_pbar)
        ## `QtWidgets.QToolButton` stop current operation button
        self.statusbar_btnstop = QtWidgets.QToolButton()
        self.statusbar_btnstop.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.statusbar_btnstop.setDefaultAction(self.act_stop)
        self.statusbar_btnstop.hide()
        self.statusbar.addPermanentWidget(self.statusbar_btnstop)
        ## `QtWidgets.QLabel` status bar text 1 (app version)
        self.statusbar_l1 = QtWidgets.QLabel(self.statusbar)
        self.statusbar.addPermanentWidget(self.statusbar_l1)
        ## `forms::ClickableLabel` status bar text 2 (other messages)
        self.statusbar_l2 = ClickableLabel(self.statusbar)
        self.statusbar_l2.dblclicked.connect(self.on_statusbar_l2_dblclicked)
        color_to_stylesheet(QtGui.QColor(QtCore.Qt.darkGreen), self.statusbar_l2.styleSheet(), 'color')
        self.statusbar_l2.setStyleSheet('color: maroon;')
        self.statusbar_l2.setToolTip(_('Double-click to update'))
        self.statusbar.addPermanentWidget(self.statusbar_l2)        
        #self.layout_hgrid3.addWidget(self.statusbar)
        self.setStatusBar(self.statusbar)
        
    ## Creates all context menus for main window.
    def UI_create_context_menus(self):
        ## `forms::CrosswordMenu` context menu for MainWindow::twCw
        self.menu_crossword = CrosswordMenu(self)

    ## Looks for valid command-line commands (to open a file, etc.) and executes them.
    # @param kwargs `keyword arguments` commands to execute
    def execute_cli_args(self, **kwargs):
        # look for 'new' command
        newcw = kwargs.get('new', False)
        if newcw:
            # create new cw
            self.cw = Crossword(data=Crossword.basic_grid(kwargs.get('cols', 15), kwargs.get('rows', 15), kwargs.get('pattern', 1)), data_type='grid',
                                wordsource=self.wordsrc, wordfilter=self.on_filter_word, pos=CWSettings.settings['cw_settings']['pos'],
                                log=CWSettings.settings['cw_settings']['log'])                    
            self.update_cw()        
            self.act_edit.setChecked(True)
            return
        # look for 'open' command
        openfile = kwargs.get('open', None)
        if openfile:
            self.open_cw(openfile)
            return

    ## Clears any temps left by the app's previous launches.
    # @param delete_update_log `bool` whether to delete the 'update.log' file left from previous update
    def delete_temp_files(self, delete_update_log=True):
        # update.log
        updatelog = os.path.join(os.path.dirname(__file__), 'update.log')
        # check update info
        try:
            s = ''
            with open(updatelog, 'r', encoding=ENCODING) as filein:
                s = filein.read()
            if _('UPDATE SUCCEEDED') in s:                
                ts = os.path.getmtime(updatelog)
                self.updater.update_info['last_update'] = timestamp_to_str(ts)
                self.updater._write_update_info()
            if delete_update_log:
                self.garbage.append(updatelog)
        except Exception:
            pass
            #self._log(err)

        # clear all files found in self.garbage
        for filepath in self.garbage:
            try:
                os.remove(filepath)
            except:
                continue
        
    ## Applies settings found in CWSettings::settings and updates the settings file.
    def apply_config(self, save_settings=True, autoloadcw=True):
        # autoload saved cw (see CWSettings::settings['common']['autosave_cw'])
        if autoloadcw: self.autoload_cw()
        
        # gui
        if CWSettings.settings['gui']['theme'] and CWSettings.settings['gui']['theme'] != QtWidgets.QApplication.instance().style().objectName():
            QtWidgets.QApplication.instance().setStyle(CWSettings.settings['gui']['theme'])
        # update window geometry from settings (last saved pos and size)
        self.move(CWSettings.settings['gui']['win_pos'][0], CWSettings.settings['gui']['win_pos'][1])
        self.resize(CWSettings.settings['gui']['win_size'][0], CWSettings.settings['gui']['win_size'][1])
        tb = CWSettings.settings['gui']['toolbar_pos']
        if tb < 4:
            TOOLBAR_AREAS = {0: QtCore.Qt.TopToolBarArea, 1: QtCore.Qt.BottomToolBarArea, 2: QtCore.Qt.LeftToolBarArea, 3: QtCore.Qt.RightToolBarArea}
            self.addToolBar(TOOLBAR_AREAS[tb], self.toolbar_main)
            self.toolbar_main.show()
            self.act_view_showtoolbar.setChecked(True)
        elif tb == 4:
            self.toolbar_main.hide()
            self.act_view_showtoolbar.setChecked(False)
        # toolbar items
        self.toolbar_from_settings()
            
        # wordsrc
        self.update_wordsrc()        
        # cw_settings
        if self.cw: self.update_cw_params()
        # grid_style
        self.twCw.setGridStyle(CWSettings.settings['grid_style']['line'])
        self.twCw.setShowGrid(CWSettings.settings['grid_style']['show'])
        self.twCw.horizontalHeader().setVisible(CWSettings.settings['grid_style']['header'])
        self.twCw.verticalHeader().setVisible(CWSettings.settings['grid_style']['header'])
        style = color_to_stylesheet(QtGui.QColor.fromRgba(CWSettings.settings['grid_style']['line_color']), self.twCw.styleSheet(), 'gridline-color')
        style = property_to_stylesheet('border-width', CWSettings.settings['grid_style']['line_width'], style)
        style = color_to_stylesheet(QtGui.QColor.fromRgba(CWSettings.settings['cell_format']['FILLER2']['bg_color']), style, 'background-color')
        style = color_to_stylesheet(QtGui.QColor.fromRgba(CWSettings.settings['grid_style']['active_cell_color']), style, 'selection-background-color')
        style = color_to_stylesheet(QtGui.QColor.fromRgba(CWSettings.settings['cell_format']['HILITE']['fg_color']), style, 'selection-color')
        self.twCw.setStyleSheet(style)
        # cell_format, numbers, cell size etc...
        self.update_cw(False)
        self.slider_cw_scale.setValue(CWSettings.settings['grid_style']['scale'])
        # apply settings to clue table (column order and width)
        self.adjust_clues_header_columns()

        # updater
        ## `utils::update::Updater` instance (used to run app update checks and updates)
        self.updater = Updater(APP_NAME, APP_VERSION, GIT_REPO, UPDATE_FILE,
            make_abspath(CWSettings.settings['update']['logfile']),
            CWSettings.settings['update']['check_every'], 
            CWSettings.settings['update']['only_major_versions'],
            CWSettings.settings['plugins']['thirdparty']['git']['exepath'] \
                if (CWSettings.settings['plugins']['thirdparty']['git']['active'] and \
                    CWSettings.settings['plugins']['thirdparty']['git']['exepath']) else None,
            on_get_recent=self.on_get_recent, on_before_update=self.on_before_update,
            on_norecent=self.on_norecent)

        # sharer
        if self.sharer: 
            self.sharer.cloud.init_settings()
        
        # save settings file
        if save_settings:
            CWSettings.save_to_file(SETTINGS_FILE)
        
    ## Changes the scale of the crossword grid.
    # @param scale_factor `int` the scale factor in percent values
    # @param update_label `bool` whether to update the caption below the scale slider
    def scale_cw(self, scale_factor=100, update_label=True): 
        # write to settings
        CWSettings.settings['grid_style']['scale'] = scale_factor
        # apply scale to fonts in grid   
        self.reformat_cells()
        # show scale text
        if update_label:
            self.l_cw_scale.setText(f"{int(scale_factor)}%")

        cell_sz = int(CWSettings.settings['grid_style']['cell_size'] * scale_factor / 100.)        

        for i in range(self.twCw.columnCount()):
            self.twCw.setColumnWidth(i, cell_sz)
            for j in range(self.twCw.rowCount()):
                if i == 0:
                    self.twCw.setRowHeight(j, cell_sz)
                    
    ## Updates the `enabled` property of each action depending on which actions are currently available.
    def update_actions(self):
        b_cw = not self.cw is None
        gen_running = self.gen_thread.isRunning() if getattr(self, 'gen_thread', None) else False
        gen_interrupted = self.gen_thread.isInterruptionRequested() if getattr(self, 'gen_thread', None) else False
        share_running = self.share_thread.isRunning() if getattr(self, 'share_thread', None) else False
        share_interrupted = self.share_thread.isInterruptionRequested() if getattr(self, 'share_thread', None) else False
        self.act_new.setEnabled(not gen_running and not share_running)
        self.act_open.setEnabled(not gen_running and not share_running)
        self.act_save.setEnabled(b_cw and not gen_running and (self.cw_modified or not self.cw_file))
        self.act_saveas.setEnabled(b_cw and not gen_running and not share_running)
        self.act_close.setEnabled(b_cw and not gen_running and not share_running)
        self.act_reload.setEnabled(b_cw and not gen_running and not share_running)
        self.act_share.setEnabled(b_cw and not gen_running and not share_running)
        self.act_edit.setEnabled(b_cw and not gen_running and not share_running)
        self.act_addcol.setEnabled(b_cw and not gen_running and not share_running and self.act_edit.isChecked())
        self.act_addrow.setEnabled(b_cw and not gen_running and not share_running and self.act_edit.isChecked())
        self.act_delcol.setEnabled(b_cw and not gen_running and not share_running and self.act_edit.isChecked())
        self.act_delrow.setEnabled(b_cw and not gen_running and not share_running and self.act_edit.isChecked())
        self.act_reflect.setEnabled(b_cw and not gen_running and not share_running and self.act_edit.isChecked())
        self.act_gen.setEnabled(b_cw and not gen_running and not share_running and bool(self.wordsrc))
        if not gen_running and not share_running: self.act_stop.setChecked(False)
        self.act_stop.setVisible(b_cw and (gen_running and not gen_interrupted) or (share_running and not share_interrupted))        
        self.act_clear.setEnabled(b_cw and not gen_running and not share_running)
        self.act_clear_wd.setEnabled(b_cw and not gen_running and not share_running)
        self.act_erase_wd.setEnabled(b_cw and not gen_running and not share_running)
        self.act_suggest.setEnabled(b_cw and not gen_running and bool(self.wordsrc) and (not self.current_word is None))
        self.act_lookup.setEnabled(b_cw and not gen_running and (not self.current_word is None) and not self.cw.words.is_word_blank(self.current_word))
        self.act_editclue.setEnabled(b_cw and not gen_running)
        self.act_wsrc.setEnabled(b_cw and not gen_running)
        self.act_info.setEnabled(b_cw and not gen_running)
        self.act_stats.setEnabled(b_cw and not gen_running and not share_running)
        self.act_print.setEnabled(b_cw and not gen_running and not share_running)
        self.act_config.setEnabled(not gen_running)
        self.act_update.setEnabled(not gen_running and not share_running)
        if hasattr(self, 'updater'):
            self.act_update.setEnabled(self.act_update.isEnabled() and self.updater.git_installed)
        #self.act_help.setEnabled(not gen_running)
        #self.act_about.setEnabled(not gen_running)
        self.twCw.setEnabled(b_cw and not gen_running)
        self.tvClues.setEnabled(b_cw and not gen_running)
        
    ## Updates MainWindow::wordsrc from the global settings in CWSettings::settings.
    def update_wordsrc(self):
        self.wordsrc.clear()
        self.wordsrc.max_fetch = CWSettings.settings['wordsrc']['maxres']
        # MultiWordsource.order is by default 'prefer-last', so just append sources
        for src in CWSettings.settings['wordsrc']['sources']:
            if not src['active']: continue
            if src['type'] == 'db':
                if src['dbtype'].lower() == 'sqlite':
                    db = Sqlitedb()
                    if not db.setpath(src['file'], fullpath=(not src['file'].lower() in LANG), recreate=False, connect=True):
                        self._log(_("DB path {} unavailable!").format(src['file']))
                        continue
                    self.wordsrc.add(DBWordsource(src['dbtables'], db, shuffle=src['shuffle']))
                    
            elif src['type'] == 'file':
                self.wordsrc.add(TextfileWordsource(src['file'], enc=src['encoding'], delimiter=src['delim'], shuffle=src['shuffle']))
                
            elif src['type'] == 'list' and src['words']:
                words = []
                if src['haspos']:                    
                    for w in src['words']:
                        w = w.split(src['delim'])
                        words.append((w[0], tuple(w[1:]) if len(w) > 1 else None))
                else:
                    words = src['words']
                self.wordsrc.add(TextWordsource(words, shuffle=src['shuffle']))

    ## Updates cw data and view.
    # @param rescale `bool` whether rescaling the grid is required
    def update_cw(self, rescale=True):
        # update grid
        self.update_cw_grid()
        # rescale grid
        if rescale:
            self.on_slider_cw_scale(CWSettings.settings['grid_style']['scale'])
            #self.scale_cw(CWSettings.settings['grid_style']['scale'])
            #self.slider_cw_scale.setValue(CWSettings.settings['grid_style']['scale'])
        # update window title
        self.setWindowTitle(f"{APP_NAME}{(' - ' + os.path.basename(self.cw_file)) if (self.cw_file and self.cw_file != SAVEDCW_FILE) else ''}")

    ## Reads the crossword grid from a text file and returns the grid as a list of rows.
    # @param gridfile `str` the full path to the text file containing the cw grid structure
    # @returns `list` list of rows (strings) representing a crossword grid
    def grid_from_file(self, gridfile):
        cwgrid = []
        
        try:
            with open(gridfile, 'r', encoding=ENCODING) as file:
                for ln in file:
                    s = ln
                    if s.endswith('\n'): s = s[:-1]
                    if s.endswith('\r'): s = s[:-1]
                    if not s: break
                    cwgrid.append(s)
        except UnicodeDecodeError as err:
            self._log(err)
            
        return cwgrid
    
    ## Saves the currently open crossword (MainWindow::cw) to the default autosave file (utils::globalvars::SAVEDCW_FILE).
    def autosave_cw(self):
        if not self.cw:
            try:
                os.remove(SAVEDCW_FILE)
                return
            except:
                pass
        else:
            self.cw.words.to_file(SAVEDCW_FILE)
            self.cw_modified = False
        
    ## Loads self.cw from the default autosave file (utils::globalvars::SAVEDCW_FILE) if present.
    def autoload_cw(self):
        if self.cw or not CWSettings.settings['common']['autosave_cw'] or not os.path.isfile(SAVEDCW_FILE): return
        try:
            self.cw = Crossword(data=SAVEDCW_FILE, data_type='file',
                                    wordsource=self.wordsrc, wordfilter=self.on_filter_word, pos=CWSettings.settings['cw_settings']['pos'],
                                    log=CWSettings.settings['cw_settings']['log'])
            self.cw_file = SAVEDCW_FILE
            self.update_cw()
            self.cw_modified = False
        except Exception as err:
            self._log(err)
            self.cw = None
    
    ## Checks if a given cw grid cell is found in a given Word instance.
    def _item_in_word(self, cell_item: QtWidgets.QTableWidgetItem, word: Word):
        return word.does_cross((cell_item.column(), cell_item.row()))

    ## Loads the crossword (MainWindow::cw) from a given file.
    # @param selected_path `str` the full file path to the file from which the crossword is loaded
    def open_cw(self, selected_path):
        ext = os.path.splitext(selected_path)[1][1:]
        if ext in ('xpf', 'ipuz'):
            # cw file
            self.cw = Crossword(data=selected_path, data_type='file',
                                wordsource=self.wordsrc, wordfilter=self.on_filter_word, pos=CWSettings.settings['cw_settings']['pos'],
                                log=CWSettings.settings['cw_settings']['log'])
        else:
            # text file with grid
            self.cw = Crossword(data=self.grid_from_file(selected_path), data_type='grid',
                                wordsource=self.wordsrc, wordfilter=self.on_filter_word, pos=CWSettings.settings['cw_settings']['pos'],
                                log=CWSettings.settings['cw_settings']['log'])
        self.cw_file = selected_path
        self.update_cw()
        self.cw_modified = False

    ## Closes the currently open crossword (freeing MainWindow::cw).
    def close_cw(self):
        self.cw = None
        self.cw_file = ''
        self.last_pressed_item = None
        self.current_word = None
        self.cw_modified = False
        self.twCw.clear()
        self.update_clues_model()        
        self.update_actions()
    
    ## Updates the currently selected word in the grid and clues table.
    # @param on_intersect `str` one of:
    #   * 'current' = leave current direction
    #   * 'h' = switch to across word
    #   * 'v' = switch to down word
    #   * 'flip' = toggle current from across to down or vice-versa
    def update_current_word(self, on_intersect='current'):
        if not self.cw: return
        sel_item = self.twCw.currentItem()
        if not sel_item: 
            return
        coord = (sel_item.column(), sel_item.row())
        words = self.cw.words.find_by_coord(coord, False)
        if words['h'] and words['v']:
            # found intersection            
            if on_intersect == 'h':
                self.current_word = words['h']
            elif on_intersect == 'v':
                self.current_word = words['v']
            elif on_intersect == 'flip':
                if self.current_word == words['h']:
                    self.current_word = words['v']
                elif self.current_word == words['v']:
                    self.current_word = words['h']
                else:
                    self.current_word = words['h']
            elif self.current_word != words['h'] and self.current_word != words['v']:
                self.current_word = words['h']
        elif words['h']:
            # only across available
            self.current_word = words['h']
        elif words['v']:
            # only down available
            self.current_word = words['v']
        else:
            self.current_word = None
        
        self.act_suggest.setEnabled((not self.cw is None) and (not self.gen_thread.isRunning()) and bool(self.wordsrc) and (not self.current_word is None))
        self.select_clue()
        self.update_actions()

    ## Updates the settings (CWSettings::settings) with current clue table's column parameters.
    def update_clue_column_settings(self):
        model = self.tvClues.model()
        header = self.tvClues.header()
        cols = []
        for i in range(header.count()):
            model_index = header.logicalIndex(i)
            header_item = model.horizontalHeaderItem(model_index)
            if header_item:
                cols.append({'name': header_item.data(), 
                            'visible': not header.isSectionHidden(model_index), 
                            'width': header.sectionSize(model_index)})
        if cols: CWSettings.settings['clues']['columns'] = cols

    ## Gets the logical column number of clues table by the column header (title).
    # @param colname `str` the column title (must be the original English name!)
    # @returns `int` the logical column index (independent of manual column reordering in the view)
    def _logical_col_by_name(self, colname):
        model = self.tvClues.model()
        if not model: return -1
        header = self.tvClues.header()
        for i in range(header.count()):
            model_index = header.logicalIndex(i)
            if model.horizontalHeaderItem(model_index).data() == colname:
                return model_index
        return -1

    ## Gets the clue table column settings from CWSettings::settings given its logical index.
    # @param index `int` the logical column index (independent of manual column reordering in the view)
    # @returns `dict` the corresponding column's settings found in `CWSettings::settings['clues']['columns']`
    def _col_setting_by_logical_index(self, index):
        model = self.tvClues.model()
        if not model: return None
        colitem = model.horizontalHeaderItem(index)
        if not colitem: return None
        colname = colitem.data()
        for col in CWSettings.settings['clues']['columns']:
            if col['name'] == colname:
                return col
        return None

    ## Returns Word object from self.cw corresponding to the given clue item.
    # @param item `QtGui.QStandardItem` the item in the clues table
    def _word_from_clue_item(self, item: QtGui.QStandardItem):
        if not self.cw or item.rowCount(): return None
        root_item = item.parent()
        if not root_item: return None
        try:
            col = self._logical_col_by_name('No.')
            if col < 0: return None
            num = int(root_item.child(item.row(), col).text())
            wdir = 'h' if root_item.text() == _('ACROSS') else 'v'
            return self.cw.words.find_by_num_dir(num, wdir)
        except Exception as err:
            self._log(err)
            return None

    ## Returns items from a single row in the clues table corresponding
    # to the given Word object. 
    # @param word `Word` a Word instance (representing a single word in the crossword)
    # @returns `dict` clue items as a dict: 
    # @code
    # {'num': num, 'text': 'word string', 'clue': 'clue string'}
    # @endcode
    def _clue_items_from_word(self, word: Word):
        datamodel = self.tvClues.model()
        if not datamodel or word is None: return None
        dirs = {'h': _('ACROSS'), 'v': _('DOWN')}
        items = datamodel.findItems(dirs[word.dir])
        if not len(items): return None
        root_item = items[0]
        col = self._logical_col_by_name('No.')
        if col < 0: return None
        for row in range(root_item.rowCount()):
            item_num = root_item.child(row, col)
            try:
                num = int(item_num.text())
                if num == word.num:
                    return {'num': item_num, 'text': root_item.child(row, self._logical_col_by_name('Reply')), 'clue': root_item.child(row, self._logical_col_by_name('Clue'))}
            except:
                continue
        return None

    ## Updates the reply values in clues table for given grid coordinate. 
    # @param coord `2-tuple` the grid coordinate (see crossword::Coords)
    def update_clue_replies(self, coord):
        if not self.cw: return
        datamodel = self.tvClues.model()
        if not datamodel: return
        words = self.cw.words.find_by_coord(coord, False)
        for wdir in words:
            if words[wdir] is None: continue
            clue_items = self._clue_items_from_word(words[wdir])
            if not clue_items: continue
            txt = self.cw.words.get_word_str(words[wdir]).upper()
            clue_items['text'].setText(txt)
        self.reformat_clues()
    
    ## Selects (and if necessary scrolls to) the clue item corresponding to the currently selected word.
    def select_clue(self):
        if self.tvClues.hasFocus(): return
        sel_model = self.tvClues.selectionModel()
        if not sel_model: return
        sel_model.clear()
        try:
            if not self.current_word:
                raise Exception(_('No current word'))
            datamodel = self.tvClues.model()
            root_item = datamodel.item(0 if self.current_word.dir == 'h' else 1)
            if not root_item:
                raise Exception(_('No root item'))
            cnt = datamodel.rowCount(root_item.index())
            for row in range(cnt):
                item_num = root_item.child(row, 1)
                try:
                    if int(item_num.text()) == self.current_word.num:
                        # found clue   
                        item_index = root_item.child(row, 0).index()
                        self.tvClues.scrollTo(item_index)   
                        sel_model.select(item_index, 
                            QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)                        
                        break
                except Exception as err:
                    self._log(err)
                    continue
        except:
            return
                
    ## Updates the internal formatting (colors, fonts) in the crossword grid for a given cell.
    # @param cell_item `QtWidgets.QTableWidgetItem` the cell that must be formatted
    def set_cell_formatting(self, cell_item: QtWidgets.QTableWidgetItem):
        
        def format_cell(cell_item, dic_format):   
            cell_item.setBackground(QtGui.QBrush(QtGui.QColor.fromRgba(dic_format['bg_color']), dic_format['bg_pattern']))
            cell_item.setForeground(QtGui.QBrush(QtGui.QColor.fromRgba(dic_format['fg_color']), dic_format['fg_pattern']))
            if self.act_edit.isChecked():
                cell_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            else:
                cell_item.setFlags(QtCore.Qt.ItemFlags(dic_format['flags']))
            font = make_font(dic_format['font_name'], dic_format['font_size'] * (CWSettings.settings['grid_style']['scale'] / 100.), dic_format['font_weight'], dic_format['font_italic'])
            cell_item.setFont(font)
            cell_item.setTextAlignment(QtCore.Qt.Alignment(dic_format['align']))
                        
        if self.current_word and self._item_in_word(cell_item, self.current_word):
            # hilite
            format_cell(cell_item, CWSettings.settings['cell_format']['HILITE'])
        else:     
            ch = cell_item.text()
            k = 'NORMAL'
            if ch == '' or ch == BLANK: 
                k = 'BLANK'
            elif ch == FILLER:
                k = 'FILLER'
            elif ch == FILLER2:
                k = 'FILLER2'
            format_cell(cell_item, CWSettings.settings['cell_format'][k])
        
    ## Updates the internal formatting (colors, fonts) of the crossword grid.
    def reformat_cells(self):
        rows = self.twCw.rowCount()
        cols = self.twCw.columnCount()
        for r in range(rows):
            for c in range(cols):
                cell_item = self.twCw.item(r, c)
                if cell_item:
                    self.set_cell_formatting(cell_item)
        self.twCw.show()
    
    ## @brief Updates (fills) the crossword grid from the internal crossword::Crossword object (self.cw).
    # This function resizes, fills the grid, updates the cell formatting and updates (fills) 
    # the clues table.
    def update_cw_grid(self):
        if not isinstance(self.cw, Crossword): return
        try:
            self.twCw.itemClicked.disconnect()
            self.twCw.currentItemChanged.disconnect()
        except:
            pass
        self.last_pressed_item = None
        self.current_word = None
        curr_cell = (self.twCw.currentRow(), self.twCw.currentColumn())
        old_gridsize = (self.twCw.rowCount(), self.twCw.columnCount())
        self.twCw.clear()
        self.twCw.setRowCount(self.cw.words.height)
        self.twCw.setColumnCount(self.cw.words.width)
        self.cw.reset_used()
        for row in range(self.cw.words.height):
            for col in range(self.cw.words.width):
                coord = (col, row)
                words = self.cw.words.find_by_coord(coord)
                w = words['h'] or words['v']
                ch = self.cw.words.get_char(coord)
                self.twCw.setItem(row, col, self.make_cell_item('' if ch == BLANK else ch, w.num if w else ''))
        self.update_current_word()    
        self.reformat_cells()            
        self.update_clues_model()
        self.twCw.itemClicked.connect(self.on_cw_item_clicked)
        self.twCw.currentItemChanged.connect(self.on_cw_current_item_changed)
        if curr_cell[0] >= 0 and curr_cell[1] >= 0 and (old_gridsize == (self.twCw.rowCount(), self.twCw.columnCount())):
            self.twCw.setCurrentCell(*curr_cell)
        self.cw_modified = True
        self.update_actions()
        
    ## Creates a crossword cell item (`QtWidgets.QTableWidgetItem`) with given text and number.
    # @param text `str` the cell text (1 character)
    # @param icon_text `str` the text of the number caption (default = empty)
    # @returns `QtWidgets.QTableWidgetItem` cell object that can be inserted into MainWindow::twCw
    def make_cell_item(self, text, icon_text=''):
        text = text.lower() if CWSettings.settings['grid_style']['char_case'] == 'lower' else text.upper()
        if not icon_text or not CWSettings.settings['grid_style']['numbers']['show']: 
            return QtWidgets.QTableWidgetItem(text)
        pixmap = QtGui.QPixmap(15, 15)
        pixmap.fill(QtGui.QColor(QtCore.Qt.transparent))
        icon = QtGui.QIcon()
        painter = QtGui.QPainter()     
        if painter.begin(pixmap):
            painter.setBackgroundMode(QtCore.Qt.TransparentMode)
            #painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            font = make_font(CWSettings.settings['grid_style']['numbers']['font_name'], 
                             CWSettings.settings['grid_style']['numbers']['font_size'],
                             CWSettings.settings['grid_style']['numbers']['font_weight'],
                             CWSettings.settings['grid_style']['numbers']['font_italic'])
            painter.setFont(font)
            painter.setPen(QtGui.QPen(QtGui.QColor.fromRgba(CWSettings.settings['grid_style']['numbers']['color'])))
            painter.drawStaticText(0, 0, QtGui.QStaticText(str(icon_text)))
            painter.end()
            icon = QtGui.QIcon(pixmap)
        return QtWidgets.QTableWidgetItem(icon, text)
        
    ## Updates the core settings of MainWindow::cw (internal crossword::Crossword instance) from CWSettings::settings.
    def update_cw_params(self):
        if not isinstance(self.cw, Crossword): return
        self.cw.closelog()
        self.cw.wordsource = self.wordsrc
        self.cw.pos = CWSettings.settings['cw_settings']['pos']
        self.cw.setlog(CWSettings.settings['cw_settings']['log'])
        # excluded filter
        self.cw.wordfilter = None
        if CWSettings.settings['wordsrc']['excluded']['words']:
            if CWSettings.settings['wordsrc']['excluded']['regex']:
                self.cw.wordfilter = lambda w: not any(re.fullmatch(pattern, w, re.I) for pattern in CWSettings.settings['wordsrc']['excluded']['words'])
            else:
                self.cw.wordfilter = lambda w: not any(w.lower() == pattern.lower() for pattern in CWSettings.settings['wordsrc']['excluded']['words'])

    ## Updates (regenerates) the clues table from the clues contained in the current crossword.
    def update_clues_model(self):

        def _localize_colname(name):
            if name == 'Direction':
                return _('Direction')
            elif name == 'No.':
                return _('No.')
            elif name == 'Clue':
                return _('Clue')
            elif name == 'Letters':
                return _('Letters')
            elif name == 'Reply':
                return _('Reply')
            return ''

        sort_role = QtCore.Qt.UserRole + 2
        delegate = self.tvClues.itemDelegate()
        if delegate:
            try:
                delegate.commitData.disconnect()
            except:
                pass
        self.tvClues.setModel(None)
        ## `QtGui.QStandardItemModel` underlying data model for MainWindow::tvClues
        self.cluesmodel = QtGui.QStandardItemModel(0, 5)
        self.cluesmodel.setSortRole(sort_role)
        col_labels = [col['name'] for col in CWSettings.settings['clues']['columns']]
        #self.cluesmodel.setHorizontalHeaderLabels(_localize_colnames(col_labels))
        for i, col_label in enumerate(col_labels):
            header_item = QtGui.QStandardItem(_localize_colname(col_label))
            header_item.setData(col_label)
            self.cluesmodel.setHorizontalHeaderItem(i, header_item)
        if not self.cw: 
            self.tvClues.setModel(self.cluesmodel)
            self.tvClues.show()
            return
        root_items = {_('ACROSS'): 'h', _('DOWN'): 'v'}
        for k in sorted(root_items, key=lambda key: root_items[key]):
            root_item = QtGui.QStandardItem(QtGui.QIcon(f"{ICONFOLDER}/crossword.png"), k)
            root_item.setData(k, sort_role)
            for w in self.cw.words.words:
                if w.dir != root_items[k]: continue
                item_dir = QtGui.QStandardItem(QtGui.QIcon(), '')
                item_dir.setData('', sort_role)
                item_dir.setFlags(QtCore.Qt.ItemIsEnabled)
                val = w.num
                item_num = QtGui.QStandardItem(str(val))
                item_num.setData(val, sort_role)
                item_num.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                val = w.clue
                item_clue = QtGui.QStandardItem(val)
                item_clue.setData(val, sort_role)
                item_clue.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                val = len(w)
                item_letters = QtGui.QStandardItem(str(val))
                item_letters.setData(val, sort_role)
                item_letters.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                val = self.cw.words.get_word_str(w).upper()
                item_reply = QtGui.QStandardItem(val)
                item_reply.setData(val, sort_role)
                item_reply.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                items = {'Direction': item_dir, 'No.': item_num, 'Clue': item_clue, 'Letters': item_letters, 'Reply': item_reply}
                root_item.appendRow([items[k] for k in col_labels])
            self.cluesmodel.appendRow(root_item)
            #for i in range(len(col_labels)):
            #    self.cluesmodel.item(root_item.row(), i).setFlags(QtCore.Qt.ItemIsEnabled)
        self.tvClues.setModel(self.cluesmodel)
        self.clues_show_hide_cols()
        self.tvClues.header().sectionMoved.connect(self.on_tvClues_column_moved)
        self.tvClues.selectionModel().selectionChanged.connect(self.on_tvClues_selected)
        self.tvClues.selectionModel().currentChanged.connect(self.on_tvClues_current_changed)
        self.tvClues.sortByColumn(0, 0)
        self.tvClues.show()
        self.tvClues.expandAll()
        self.reformat_clues()
        self.select_clue()
        delegate = self.tvClues.itemDelegate()
        if delegate:
            delegate.commitData.connect(self.on_clues_editor_commit)

    ## Shows or hides columns in the clues table based on current settings.
    def clues_show_hide_cols(self):
        header = self.tvClues.header()
        header.setDropIndicatorShown(True)
        for icol in range(header.count()):
            index = header.logicalIndex(icol)
            col_setting = self._col_setting_by_logical_index(index)
            if col_setting:
                header.setSectionHidden(index, not col_setting['visible'])

    ## Sets formatting in clues table according to word status (filled / empty).
    def reformat_clues(self):     
        datamodel = self.tvClues.model()
        if not datamodel: return
        header = self.tvClues.header()
        for row in range(datamodel.rowCount()):
            root_item = datamodel.item(row)
            for row_clue in range(root_item.rowCount()):
                fstyle = ''
                for icol in range(header.count()):
                    model_index = header.logicalIndex(icol)
                    colitem = datamodel.horizontalHeaderItem(model_index)
                    if not colitem: continue
                    col_name = colitem.data()
                    item = root_item.child(row_clue, model_index)
                    if col_name == 'Clue':
                        fstyle = 'COMPLETE' if item.text() else 'INCOMPLETE'
                    elif col_name == 'Reply':
                        fstyle = 'COMPLETE' if not BLANK in item.text() else 'INCOMPLETE'
                    else:
                        fstyle = 'NORMAL'
                    bgstyle = QtGui.QBrush(QtGui.QColor.fromRgba(CWSettings.settings['clues'][fstyle]['bg_color']), CWSettings.settings['clues'][fstyle]['bg_pattern'])
                    item.setBackground(bgstyle)
                    fgstyle = QtGui.QBrush(QtGui.QColor.fromRgba(CWSettings.settings['clues'][fstyle]['fg_color']), QtCore.Qt.SolidPattern)
                    item.setForeground(fgstyle)
                    item.setTextAlignment(QtCore.Qt.Alignment(CWSettings.settings['clues']['NORMAL']['align']))
                    font = make_font(CWSettings.settings['clues']['NORMAL']['font_name'], 
                                    CWSettings.settings['clues']['NORMAL']['font_size'], 
                                    CWSettings.settings['clues']['NORMAL']['font_weight'], 
                                    CWSettings.settings['clues']['NORMAL']['font_italic'])
                    item.setFont(font)
        style = color_to_stylesheet(QtGui.QColor.fromRgba(CWSettings.settings['clues']['SURROUNDING']['bg_color']), self.tvClues.styleSheet())
        self.tvClues.setStyleSheet(style)
                
    ## Default word source filter for Crossword constructor.
    # @return `bool` set to `True` (don't use any extra filters)
    def on_filter_word(self, word: str):
        return True

    ## Slot fires when the share thread (MainWindow::share_thread) starts up.
    # Clears status bar messages and updates actions.
    @QtCore.pyqtSlot()
    def on_share_start(self):
        self.statusbar.clearMessage()
        self.update_actions()

    ## Slot fires during the sharing thread's progress.
    # @param percent `int` percent complete
    # @param status `str` status message to show in status bar
    @QtCore.pyqtSlot(int, str)
    def on_share_progress(self, percent, status):
        #self.statusbar_pbar.setValue(percent)
        #self.statusbar_pbar.show()
        self.statusbar.showMessage(status)

    ## Slot fires when MainWindow::share_thread has uploaded the file (crossword) 
    # to the cloud storage.
    # @param filepth `str` the source file full path
    # @param url `str` the destination URL where the file is uploaded
    @QtCore.pyqtSlot(str, str)
    def on_share_upload(self, filepth, url):
        self.statusbar.showMessage(_("Uploaded '{}' to '{}'").format(filepth, url))
        # add file to garbage for future collection
        self.garbage.append(filepth)

    ## Slot fires when the sharer has copied the destination URL of the shared file to the clipboard.
    # @param url `str` the destination URL where the file is uploaded
    @QtCore.pyqtSlot(str)
    def on_share_clipboard_write(self, url):
        clipboard_copy(url)
        MsgBox(_("Copied URL '{}' to clipboard").format(url), self)

    ## Slot fires when the sharer (MainWindow::share_thread) has encountered an error.
    # @param thread `QtCore.QThread` the sharer thread (ShareThread)
    # @param err `str` the error message
    @QtCore.pyqtSlot(QtCore.QThread, str)
    def on_share_error(self, thread, err):
        #MsgBox(err, self, 'Error', 'error')
        self._log(err)

    ## Slot fires when the sharer (MainWindow::share_thread) has completed its operation.
    @QtCore.pyqtSlot()
    def on_share_finish(self):
        #self.statusbar_pbar.hide()
        self.statusbar.clearMessage()
        self.update_actions()
    
    ## Slot fires when the sharer (MainWindow::share_thread) must ask user for an API key.
    # @param res `list` input data for the request handler:
    #   `res[0]` = API key entered by user `str`
    #   `res[1]` = user dialog result `bool`: `True` = OK, `False` = Cancel
    @QtCore.pyqtSlot('PyQt_PyObject')
    def on_share_apikey_required(self, res):
        res1 = UserInput(parent=self, label=_('Enter your API key'), textmode='password')
        res[0] = res1[0]
        res[1] = res1[1]

    ## Slot fires when the sharer (MainWindow::share_thread) must ask user for a Bearer Token.
    # @param res `list` input data for the request handler:
    #   `res[0]` = Bearer Token entered by user `str`
    #   `res[1]` = user dialog result `bool`: `True` = OK, `False` = Cancel
    @QtCore.pyqtSlot('PyQt_PyObject')
    def on_share_bearer_required(self, res):
        
        @QtCore.pyqtSlot()
        def on_gettoken():
            secret = generate_uuid()
            req = Cloudstorage.OAUTH_URL.format(secret)
            MsgBox(_('Authorize your app on the webpage and paste the access token here.'))
            webbrowser.open(req, new=2)
            # TODO: hook on browser and verify secret key in resulting page content
        
        dia_gettoken = KloudlessAuthDialog(on_gettoken, self)
        result = dia_gettoken.exec()
        res[0] = dia_gettoken.le_token.text()
        res[1] = bool(result)

    ## Slot fires when the sharer has prepared the URL for sharing on a social network.
    # @param url `str` the sharing URL generated by sharer (specific to the selected social network)
    @QtCore.pyqtSlot(str)
    def on_share_prepare_url(self, url):
        self.share_thread.lock()
        try:
            self.share_url(url)
        finally:
            self.share_thread.unlock()

    ## Main worker slot (function) for the sharer thread (MainWindow::share_thread).
    @QtCore.pyqtSlot()
    def on_share_run(self):

        # 1) cloud (25%) 2) export cw (25%) 3) upload (25%) 4) share (25%)

        prog = 0
        share_target = None
        share_title = None
        share_notes = None
        share_tags = None
        share_source = None
        ext = ''

        def on_upload_(filepath, url):
            nonlocal prog
            self.share_thread.sig_upload_file.emit(filepath, url)
            prog += 25
            self.share_thread.sig_progress.emit(prog, _('Opening share link...'))
        
        try:
            self.share_thread.lock()
            share_target = self.dia_share.combo_target.currentText()
            share_title = self.dia_share.le_title.text()
            share_notes = self.dia_share.te_notes.toPlainText()
            share_tags = self.dia_share.le_tags.text()
            share_source = self.dia_share.le_source.text()
            if self.dia_share.rb_pdf.isChecked(): 
                ext = '.pdf'
            elif self.dia_share.rb_jpg.isChecked(): 
                ext = '.jpg'
            elif self.dia_share.rb_png.isChecked(): 
                ext = '.png'
            elif self.dia_share.rb_svg.isChecked(): 
                ext = '.svg'
            elif self.dia_share.rb_xpf.isChecked(): 
                ext = '.xpf'
            elif self.dia_share.rb_ipuz.isChecked(): 
                ext = '.ipuz'
        except:
            self.share_thread.unlock()
            traceback.print_exc(limit=None)
            return
        finally:
            self.share_thread.unlock()

        if not share_target: return
        
        if not self.sharer:
            self.share_thread.sig_progress.emit(prog, _('Setting up cloud storage...'))
            try:
                self.share_thread.lock()
                self.create_cloud(self.share_thread)
            except:
                self.share_thread.unlock()
                traceback.print_exc(limit=None)
                return
            finally:
                self.share_thread.unlock()
            prog = 25

        # get temp dir
        self.share_thread.sig_progress.emit(prog, _('Exporting crossword...'))

        temp_file = ''
        try:
            self.share_thread.lock()
            temp_dir = os.path.abspath(CWSettings.settings['common']['temp_dir'] or get_tempdir())
            temp_file = os.path.join(temp_dir, generate_uuid() + ext)
            # export cw
            if not self._save_cw(temp_file): return
        except:
            self.share_thread.unlock()
            traceback.print_exc(limit=None)
            return
        finally:
            self.share_thread.unlock()

        prog = 50
        self.share_thread.sig_progress.emit(prog, _('Uploading file to cloud...'))

        # share file
        try:      
            self.sharer.on_upload = on_upload_        
            self.sharer.share(temp_file, share_target, share_title,
                              share_notes, 'google', share_tags,
                              share_source)
            prog = 100
            self.share_thread.sig_progress.emit(prog, _('Finished'))
        except:
            traceback.print_exc(limit=None)
            return

        # add temp_file to garbage bin
        try:
            self.share_thread.lock()
            self.garbage.append(temp_file)
        finally:
            self.share_thread.unlock()

    ## @brief Initializes the sharer object (MainWindow::sharer).
    # Uploads exported crosswords (as images, PDF etc) to the Kloudless cloud storage and
    # shares the resulting URL in social networks (via the Shareaholic service).
    # @param thread `QtCore.QThread` the sharer thread (ShareThread)
    def create_cloud(self, thread):
        cloud = Cloudstorage(CWSettings.settings, auto_create_user=False,
                on_user_exist=lambda username: False, on_update_users=None,
                on_error=lambda err: thread.sig_error.emit(thread, err) if thread else None,
                show_errors=thread is None, 
                on_apikey_required=lambda res: thread.sig_apikey_required.emit(res) if thread else None,
                on_bearer_required=lambda res: thread.sig_bearer_required.emit(res) if thread else None,
                timeout=(CWSettings.settings['common']['web']['req_timeout'] * 1000) or None)
        
        username = CWSettings.settings['sharing']['user'] or None
        if not username:
            reply = MsgBox(_("You don't have a registered user name for uploading and sharing files.\n"
            "Would you like to set a new user name yourself (YES) or let {} assign the name for you (NO)?").format(APP_NAME),
            None, _('Create new user'), 'ask')
            if reply == 'yes':
                # ask for new user name                
                while not username:
                    res = UserInput(parent=self, title=_('Create new user'), label=_('Enter user name:'))
                    if not res[1]: 
                        MsgBox(_("{} will generate a new user name automatically").format(APP_NAME), self, _('Create new user'))
                        break
                    if cloud._user_exists(res[0]):
                        reply2 = MsgBox(_("Username {} is already occupied!\nUser another name (YES) or create name for you (NO)?").format(res[0]),
                                        self, _('Create new user'), 'warn', ['yes', 'no'])                       
                        if reply2 == 'yes':
                            continue
                        else:
                            break
                    else:
                        username = res[0]
                        break
        # create / find user
        cloud.on_user_exist = lambda username: True
        cloud._find_or_create_user(username)   

        on_prepare_url = None
        if CWSettings.settings['sharing']['use_own_browser']:
            on_prepare_url = lambda url: thread.sig_prepare_url.emit(url) if thread else self.share_url
        on_clipboard_write = lambda url: thread.sig_clipboard_write.emit(url) if thread else None
        
        ## utils::onlineservices::Share instance used for cloud upload / sharing
        self.sharer = Share(cloud, on_clipboard_write=on_clipboard_write, 
                            on_prepare_url=on_prepare_url, stop_check=self.act_stop.isChecked,
                            timeout=(CWSettings.settings['common']['web']['req_timeout'] * 1000) or None)

    ## Opens a share link in inbuilt or external browser (for sharing)
    # @param url `str` the share URL generated by MainWindow::sharer
    # @param headers `dict` HTTP headers passed to the request
    # @param error_keymap `dict` error code-to-message mapping 
    # @see utils::onlineservices::Share
    def share_url(self, url, headers={'Content-Type': 'application/json'}, error_keymap=Share.ERRMAP):
        if not hasattr(self, 'browser'):
            self.browser = Browser()
        try:
            self.browser.navigate(url)
        except:
            traceback.print_exc(limit=None) 

    ## @brief Creates and optionally shows the inbuilt python code editor.
    # @param source `str` | `None` source code to set in editor (`None` clears the existing code)
    # @param show `bool` whether to show the editor window
    # @see utils::synteditor
    def create_syneditor(self, source=None, show=True):
        from utils.synteditor import SynEditorWidget
        if not hasattr(self, 'syneditor'):
            ## `utils::synteditor::SynEditorWidget` inbuilt python code editor
            self.syneditor = SynEditorWidget(source=source)
        else:
            self.syneditor.editor.setText(source or '')
        if show: self.syneditor.show()

    ## Slot fires when the cw generation thread (MainWindow::gen_thread) starts up.
    # Performs preliminary UI element setups.
    @QtCore.pyqtSlot()
    def on_generate_start(self):
        self.statusbar_pbar.reset()
        self.statusbar_pbar.setFormat('%p%')
        self.statusbar_pbar.show()
        self.update_actions()

    ## Slot fires when the cw generation thread (MainWindow::gen_thread) has completed.
    @QtCore.pyqtSlot() 
    def on_generate_finish(self):
        self.statusbar_pbar.hide()
        self.statusbar_pbar.reset()
        self.update_cw_grid()

    ## Slot fires when the cw generation thread (MainWindow::gen_thread) has timed out.
    # @param timeout_ `float` timeout in (fractions of) seconds
    @QtCore.pyqtSlot(float)
    def on_gen_timeout(self, timeout_):
        MsgBox(_("Timeout occurred at {} seconds!").format(timeout_), self, _('Timeout'), 'warn')

    ## Slot fires when the cw generation thread (MainWindow::gen_thread) has been stopped.
    @QtCore.pyqtSlot()
    def on_gen_stop(self):
        MsgBox("Generation stopped!", self, _('Stopped'), 'warn')

    ## Slot fires when the cw generation thread (MainWindow::gen_thread) has encountered an error.
    # @param thread `QtCore.QThread` the generation thread object (GenThread)
    # @param err `str` the error message
    @QtCore.pyqtSlot(QtCore.QThread, str)
    def on_gen_error(self, thread, err):
        MsgBox(_("Generation failed with error:{}{}").format(NEWLINE, err), self, _('Error'), 'error')

    ## Slot fires when the cw generator has completed and needs to validate the words in the grid.
    # @param bad_ `list` list of words `str` that haven't passed validation (not found in active word sources)
    @QtCore.pyqtSlot('PyQt_PyObject')
    def on_gen_validate(self, bad_):
        MsgBox(_("Generation finished!{}{}").format(NEWLINE, (_('Check OK') if not bad_ else _('The following words failed validation: ') + repr(bad_))), 
                self, _('Generation finished'), 'info' if not bad_ else 'warn')

    ## Slot fires to show progress of cw generation thread (MainWindow::gen_thread).
    # @param cw_ `crossword::Crossword` pointer to the crossword::Crossword object that runs the generation
    # @param complete_ `int` number of completed (filled) words
    # @param total_ `int` total number of words in cw grid
    @QtCore.pyqtSlot('PyQt_PyObject', int, int)
    def on_gen_progress(self, cw_, complete_, total_):
        perc = complete_ * 100.0 / total_
        self.statusbar_pbar.setValue(perc)
        self.statusbar_pbar.setFormat(f"%v% - {complete_} / {total_}")

    ## Main worker function for the cw generation thread (MainWindow::gen_thread).
    # Generates (fills) the current crossword (MainWindow::cw)
    def generate_cw_worker(self):
        method = ''
        timeout = 0.0
        self.gen_thread.lock()
        try:
            self.update_wordsrc()
            self.update_cw_params()       
            method = CWSettings.settings['cw_settings']['method']  
            timeout = CWSettings.settings['cw_settings']['timeout']   
        finally:
            self.gen_thread.unlock()

        self.cw.generate(method=method, 
                         timeout=timeout,
                         stopcheck=self.act_stop.isChecked,
                         ontimeout=lambda timeout_: self.gen_thread.sig_timeout.emit(timeout_),
                         onstop=lambda: self.gen_thread.sig_stopped.emit(),
                         onerror=lambda err_: self.gen_thread.sig_error.emit(self.gen_thread, str(err_)),
                         onvalidate=lambda bad_: self.gen_thread.sig_validate.emit(bad_),
                         on_progress=lambda cw_, complete_, total_: self.gen_thread.sig_progress.emit(cw_, complete_, total_))

    ## Util function to save or export current crossword to a given file and file type.
    # @param filepath `str` the full path to the file where the cw must be saved.
    # If not set (`None`), MainWindow::cw_file will be used (the currently open cw file)
    # @param file_type `str` | `int` the file type used to save / export the crossword.
    # If not set (`None`), the app will attempt to infer it from the filepath extension.
    # Otherwise, it can be a string representing the file filter - see _get_filetype() - CWSAVE_FILTERS,
    # or an integer representing the index of the filter in _get_filetype() - CWSAVE_FILTERS
    def _save_cw(self, filepath=None, file_type=None):
        def _guess_filetype(filepath):
            if not filepath: return -1
            ext = os.path.splitext(filepath)[1][1:].lower()
            if ext in ('xpf', 'ipuz'): return 0
            if ext == 'pdf': return 1
            if ext in ('jpg', 'png', 'tif', 'tiff', 'bmp'): return 2
            if ext == 'svg': return 3
            return 4

        def _get_filetype(filtername):
            CWSAVE_FILTERS = [_('Crossword file (*.xpf *.ipuz)'), _('PDF file (*.pdf)'), 
                    _('Image file (*.jpg *.png *.tif *.tiff *.bmp)'), _('SVG vector image (*.svg)'),
                    _('Text file (*.txt)'), _('All files (*.*)')]
            try:
                return CWSAVE_FILTERS.index(filtername)
            except:
                pass
            return -1
            
        if filepath is None:
            filepath = self.cw_file
            
        if file_type is None:
            file_type = _guess_filetype(filepath)
        else:
            if isinstance(file_type, str):
                file_type = _get_filetype(file_type)
            elif not isinstance(file_type, int):
                file_type = -1

        if not filepath or file_type == -1: return None

        try:    
            ext = os.path.splitext(filepath)[1][1:].lower()

            if file_type == 0:
                # xpf, ipuz                
                self.cw.words.to_file(filepath, ext)

            elif file_type == 1:
                # pdf
                self.print_cw(filepath, False)
                
            elif file_type == 2 or file_type == 3:
                # image (svg, jpg, bmp, tif, tiff, png)
                self.export_cw(filepath)

            else:
                # just grid
                with open(filepath, 'w', encoding=ENCODING) as fout:
                    fout.write(self.cw.words.tostr())

            if not os.path.isfile(filepath):
                raise Exception(_("Error saving crossword to '{}'").format(filepath))
           
            return (filepath, file_type)

        except Exception as err:
            MsgBox(str(err), self, _('Error'), 'error')
            return None
        
    ## Saves / exports the current crossword (MainWindow::cw) to a given file and file type.
    # @see Description in _save_cw()
    def save_cw(self, filepath=None, file_type=None):
        res = self._save_cw(filepath, file_type)
        if not res: return False
        if filepath is None:
            filepath = self.cw_file
        if res[1] in (2, 3) and CWSettings.settings['export']['openfile']:
            run_exe(filepath if getosname() == 'Windows' else f'xdg-open "{filepath}"', True, False, shell=True)    

        self.cw_file = os.path.abspath(res[0])
        self.cw_modified = False
        self.update_actions()
        return True

    ## @brief Exports crossword grid to image file.
    # The following formats are supported: JPG, PNG, TIFF, BMP (raster), SVG (vector)
    # @param filepath `str` the destination file path
    # @param scale `float` output image scale factor
    def export_cw(self, filepath, scale=1.0):
        # settings
        export_settings = CWSettings.settings['export']

        # deselect words
        self.twCw.clearSelection()
        self.current_word = None
        self.reformat_cells()  
       
        # todo: add settings for size        
        scale_factor = export_settings['img_resolution'] / 25.4 * export_settings['mm_per_cell']
        cw_size = QtCore.QSize(self.twCw.columnCount() * scale_factor, self.twCw.rowCount() * scale_factor)
        
        ext = os.path.splitext(filepath)[1][1:].lower()        
        if ext == 'svg':
            # svg                
            svg_generator = QtSvg.QSvgGenerator()
            svg_generator.setFileName(filepath)
            svg_generator.setResolution(export_settings['img_resolution'])
            svg_generator.setSize(cw_size)
            svg_generator.setViewBox(QtCore.QRect(QtCore.QPoint(0, 0), cw_size))
            svg_generator.setTitle(self._apply_macros(export_settings['svg_title'], self.cw.words))
            svg_generator.setDescription(self._apply_macros(export_settings['svg_description'], self.cw.words))
            painter = QtGui.QPainter()
            if painter.begin(svg_generator):
                self._paint_cwgrid(painter, svg_generator.viewBoxF(), export_settings['clear_cw'])
                painter.end()
        
        elif ext in ('jpg', 'png', 'tif', 'tiff', 'bmp'):
            # image                     
            img = QtGui.QImage(cw_size, QtGui.QImage.Format_ARGB32)
            painter = QtGui.QPainter()
            if painter.begin(img):
                self._paint_cwgrid(painter, QtCore.QRectF(img.rect()), export_settings['clear_cw'])
                painter.end()    
                img.save(filepath, quality=export_settings['img_output_quality'])  
        
    ## Prints current crossword (and optionally clues) to file or printer.  
    # @param pdf_file `str` | `None` path to PDF file or `None` to print to a physical printer
    # @param show_preview `bool` `True` to show print preview dialog - see forms::PrintPreviewDialog
    def print_cw(self, pdf_file=None, show_preview=True):
        settings = CWSettings.settings['printing']

        # deselect words
        self.twCw.clearSelection()
        self.current_word = None
        self.reformat_cells()        

        printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.HighResolution)
        printer.setOutputFormat(QtPrintSupport.QPrinter.PdfFormat if pdf_file else QtPrintSupport.QPrinter.NativeFormat)
        printer.setOutputFileName(pdf_file if pdf_file else '')
        printer.setPageMargins(settings['margins'][0], settings['margins'][2], 
                               settings['margins'][1], settings['margins'][3], 
                               QtPrintSupport.QPrinter.Millimeter)
        if settings['layout'] == 'auto':
            printer.setPageOrientation(QtGui.QPageLayout.Portrait if self.cw.words.height > self.cw.words.width else QtGui.QPageLayout.Landscape)
        elif settings['layout'] == 'portrait':
            printer.setPageOrientation(QtGui.QPageLayout.Portrait)
        elif settings['layout'] == 'landscape':
            printer.setPageOrientation(QtGui.QPageLayout.Landscape)
        printer.setFullPage(False)
        # try to set highest resolution
        printer.setResolution(max(printer.supportedResolutions()))
        # font embedding
        printer.setFontEmbeddingEnabled(settings['font_embed'])

        try:
            if not pdf_file:
                dia_print = QtPrintSupport.QPrintDialog(printer)
                dia_print.setOptions(QtPrintSupport.QAbstractPrintDialog.PrintToFile | 
                                    QtPrintSupport.QAbstractPrintDialog.PrintShowPageSize |
                                    QtPrintSupport.QAbstractPrintDialog.PrintCollateCopies)

                if not dia_print.exec(): return
                printer = dia_print.printer()

            else:
                printer.setResolution(CWSettings.settings['export']['pdf_resolution'])
                printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.A4))

            if show_preview:
                dia_preview = PrintPreviewDialog(printer, self, self)
                dia_preview.ppreview.paintRequested.connect(self.on_preview_paint)
                if dia_preview.exec():
                    dia_preview.write_settings()
                    dia_preview.ppreview.print()  
            else:
                self.on_preview_paint(printer)

            if settings['openfile'] and printer.outputFormat() == QtPrintSupport.QPrinter.PdfFormat:
                pdf_file = printer.outputFileName()
                if os.path.isfile(pdf_file):
                    run_exe(pdf_file if getosname() == 'Windows' else f'xdg-open "{pdf_file}"', True, False, shell=True)

        except Exception as err:            
            MsgBox(str(err), self, _('Error'), 'error')
            traceback.print_exc(limit=None) 
            return

    ## @brief Util function: replaces string macros like '\<t\>' by crossword metadata, like crossword::CWInfo::title.
    # The following macros are supported:
    # <pre>
    #   * '\<t\>' = cw title
    #   * '\<a\>' = cw author
    #   * '\<p\>' = cw publisher
    #   * '\<c\>' = cw copyright
    #   * '\<d\>' = cw date
    #   * '\<rows\>' = number of rows
    #   * '\<cols\>' = number of columns
    # </pre>
    # @param txt `str` the text containing macros
    # @param grid `crossword::Wordgrid` the crossword::Wordgrid object (crosword grid)
    # @returns `str` text after macro replacements
    def _apply_macros(self, txt, grid):
        txt = txt.replace('<t>', grid.info.title).replace('<a>', grid.info.author)
        txt = txt.replace('<p>', grid.info.publisher).replace('<c>', grid.info.cpyright)
        txt = txt.replace('<d>', datetime_to_str(grid.info.date, '%m/%d/%Y'))
        txt = txt.replace('<rows>', str(grid.height)).replace('<cols>', str(grid.width))
        return txt

    ## @brief Prints current crossword (and optionally clues) to print preview form.
    # This slot is connected to print preview dialog's paintRequested() signal.
    # @param printer `QtPrintSupport.QPrinter` the printer object
    @QtCore.pyqtSlot(QtPrintSupport.QPrinter)
    def on_preview_paint(self, printer):    
        if not printer or self.twCw.rowCount() < 1 or self.twCw.columnCount() < 1: return
        painter = QtGui.QPainter()        
        if not painter.begin(printer):
            MsgBox(_('Printing error'), self, _('Error'), 'error')
            return

        settings = CWSettings.settings['printing']

        painter.setRenderHint(QtGui.QPainter.Antialiasing, settings['antialias'])
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, settings['antialias'])
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QtGui.QPainter.LosslessImageRendering, True)

        page_rect = printer.pageRect()
        paper_rect = printer.paperRect()
        margins = printer.pageLayout().marginsPixels(printer.resolution())
        
        try:            
            painter.save()
            top_offset = 0 

            # title and info            
                     
            txt = self._apply_macros(settings['cw_title'], self.cw.words)  
            if txt:
                painter.setPen(QtGui.QPen(QtGui.QColor.fromRgba(settings['header_font']['color'])))
                painter.setFont(make_font(settings['header_font']['font_name'], 
                    settings['header_font']['font_size'], settings['header_font']['font_weight'], 
                    settings['header_font']['font_italic']))
                text_rect = painter.fontMetrics().boundingRect(txt)
                painter.drawStaticText(page_rect.width() / 2 - text_rect.width() / 2, top_offset, QtGui.QStaticText(txt))
                top_offset += text_rect.height() + 40
            
            if settings['print_info']:

                painter.setPen(QtGui.QPen(QtGui.QColor.fromRgba(settings['info_font']['color'])))
                painter.setFont(make_font(settings['info_font']['font_name'], 
                    settings['info_font']['font_size'], settings['info_font']['font_weight'], 
                    settings['info_font']['font_italic']))
                font_metrics = QtGui.QFontMetrics(painter.font())

                if self.cw.words.info.author:
                    txt = _("by {}").format(self.cw.words.info.author)                
                    text_rect = font_metrics.boundingRect(txt)
                    painter.drawStaticText(page_rect.width() - text_rect.width(), top_offset, QtGui.QStaticText(txt))
                    top_offset += text_rect.height() + 40

                if self.cw.words.info.publisher:
                    txt = _("Published by {}").format(self.cw.words.info.publisher)
                    text_rect = font_metrics.boundingRect(txt)
                    painter.drawStaticText(page_rect.width() - text_rect.width(), top_offset, QtGui.QStaticText(txt))
                    top_offset += text_rect.height() + 40

                if self.cw.words.info.cpyright:
                    txt = _("© {}").format(self.cw.words.info.cpyright)
                    text_rect = font_metrics.boundingRect(txt)
                    painter.drawStaticText(page_rect.width() - text_rect.width(), top_offset, QtGui.QStaticText(txt))
                    top_offset += text_rect.height() + 40

                if self.cw.words.info.date:
                    txt = datetime_to_str(self.cw.words.info.date, '%m/%d/%Y')
                    text_rect = font_metrics.boundingRect(txt)
                    painter.drawStaticText(page_rect.width() - text_rect.width(), top_offset, QtGui.QStaticText(txt))
                    top_offset += text_rect.height() + 40
            
            # cw    
            if settings['print_cw']:   
                painter.translate(paper_rect.topLeft())
                cw_rect = page_rect.adjusted(-margins.left(), top_offset - margins.top(), -margins.right(), -top_offset - margins.bottom())
                self._paint_cwgrid(painter, cw_rect, settings['clear_cw'])

                """
                # alternative method: render widget directly
                scales = (page_rect.width() / float(self.twCw.viewport().width()),
                        page_rect.height() / float(self.twCw.viewport().height()))
                scale = min(scales)
                painter.translate(paper_rect.topLeft())
                painter.scale(scale, scale)
                painter.translate(0, 200 if top_offset else 0)
                self.twCw.viewport().render(painter, flags=QtWidgets.QWidget.RenderFlags(QtWidgets.QWidget.DrawChildren))
                """

            # clues          
            if not settings['print_clues']:
                painter.end()
                return

            if settings['print_cw'] and not printer.newPage():
                raise Exception(_('Cannot make new page!'))
                
            painter.restore()
            top_offset = 0

            if settings['clues_title']:
                painter.setPen(QtGui.QPen(QtGui.QColor.fromRgba(settings['header_font']['color'])))
                painter.setFont(make_font(settings['header_font']['font_name'], 
                    settings['header_font']['font_size'], settings['header_font']['font_weight'], 
                    settings['header_font']['font_italic']))    
                txt = self._apply_macros(settings['clues_title'], self.cw.words)        
                text_rect = painter.fontMetrics().boundingRect(txt)
                painter.drawStaticText(page_rect.width() / 2 - text_rect.width() / 2, top_offset, QtGui.QStaticText(txt))
                top_offset += text_rect.height() + 200

            wdir = ''
            row_height = 0

            for word in self.cw.words.words:

                left_offset = 0

                if (top_offset + row_height) > (page_rect.height() - margins.bottom()):
                    if not printer.newPage():
                        raise Exception(_('Cannot make new page!'))                    
                    painter.translate(paper_rect.topLeft())
                    top_offset = 0

                painter.setPen(QtGui.QPen(QtGui.QColor.fromRgba(settings['clue_number_font']['color'])))
                painter.setFont(make_font(settings['clue_number_font']['font_name'], 
                    settings['clue_number_font']['font_size'], settings['clue_number_font']['font_weight'], 
                    settings['clue_number_font']['font_italic']))
                font_metrics = QtGui.QFontMetrics(painter.font())

                if wdir != word.dir:
                    txt = _('ACROSS:') if word.dir == 'h' else _('DOWN:')   
                    row_height = font_metrics.boundingRect(txt).height()
                    top_offset += 200
                    if (top_offset + row_height) > (page_rect.height() - margins.bottom()):
                        if not printer.newPage():
                            raise Exception(_('Cannot make new page!'))                    
                        painter.translate(paper_rect.topLeft())
                        top_offset = 0
                    text_rect = painter.drawText(left_offset, top_offset, 
                        page_rect.width() - left_offset, 
                        page_rect.height() - top_offset - margins.bottom(), 
                        (QtCore.Qt.AlignLeft | QtCore.Qt.TextWordWrap), txt)
                    top_offset += text_rect.height() + 200
                    wdir = word.dir

                if (top_offset + row_height) > (page_rect.height() - margins.bottom()):
                    if not printer.newPage():
                        raise Exception(_('Cannot make new page!'))                    
                    painter.translate(paper_rect.topLeft())
                    top_offset = 0
                
                txt = f"{word.num}. "
                text_rect1 = painter.drawText(left_offset, top_offset, 
                    page_rect.width() - left_offset, 
                    page_rect.height() - top_offset - margins.bottom(), 
                    (QtCore.Qt.AlignLeft | QtCore.Qt.TextWordWrap), txt)
                left_offset += text_rect1.width()

                painter.setPen(QtGui.QPen(QtGui.QColor.fromRgba(settings['clue_font']['color'])))
                painter.setFont(make_font(settings['clue_font']['font_name'], 
                    settings['clue_font']['font_size'], settings['clue_font']['font_weight'], 
                    settings['clue_font']['font_italic']))

                txt = f"{word.clue}   "
                text_rect2 = painter.drawText(left_offset, top_offset, 
                    page_rect.width() - left_offset - 500, 
                    page_rect.height() - top_offset - margins.bottom(), 
                    (QtCore.Qt.AlignLeft | QtCore.Qt.TextWordWrap), txt)
                left_offset += text_rect2.width()

                text_rect3 = text_rect2
                if settings['print_clue_letters']:
                    painter.setPen(QtGui.QPen(QtGui.QColor.fromRgba(settings['clue_letters_font']['color'])))
                    painter.setFont(make_font(settings['clue_letters_font']['font_name'], 
                        settings['clue_letters_font']['font_size'], settings['clue_letters_font']['font_weight'], 
                        settings['clue_letters_font']['font_italic']))
                    txt = _("[{} letters]").format(len(word))                    
                    text_rect3 = painter.drawText(left_offset, top_offset, 
                        page_rect.width() - left_offset, 
                        page_rect.height() - top_offset - margins.bottom(), 
                        (QtCore.Qt.AlignLeft | QtCore.Qt.TextWordWrap), txt)
                
                row_height = max(text_rect1.height(), text_rect2.height(), text_rect3.height())
                top_offset += row_height + 50  
            
        except Exception as err:
            MsgBox(str(err), self, _('Error'), 'error')
            traceback.print_exc(limit=None) 

        finally:
            painter.end()

    ## Paints cw grid by `QtGui.QPainter` object, constrained by cliprect (QRectF).
    # @param painter `QtGui.QPainter` the painter object
    # @param cliprect `QtCore.Qt.QRectF` clip rectangle inside which the painting will be made
    # @param clear_cw `bool` whether to clear all words from the crossword before painting
    # (words will be restored after the painting has finished)
    def _paint_cwgrid(self, painter, cliprect=None, clear_cw=True):
        
        # if cliprect is not set, use the entire painter's viewport 
        if not cliprect: cliprect = painter.viewport()

        # shortcuts for number and gridline settings
        num_settings = CWSettings.settings['grid_style']['numbers']
        gridline_width = CWSettings.settings['grid_style']['line_width']
        # number of rows and columns
        cols = self.twCw.columnCount()
        rows = self.twCw.rowCount()
        # calculate cell size
        cell_w = int((cliprect.width() + gridline_width) / cols + 2 * gridline_width)
        cell_h = int((cliprect.height() + gridline_width) / rows + 2 * gridline_width)
        cell_sz = min(cell_w, cell_h)
        # vertical offset (start = cliprect top position)
        v_offset = cliprect.top()

        # for each row...
        for r in range(rows):
            # horizontal offset (start = cliprect left position)
            h_offset = cliprect.left()
            # for each column...
            for c in range(cols):            
                # cell coordinate tuple (col, row)
                coord = (c, r)
                # get cell character from underlying cw grid
                ch = self.cw.words.get_char(coord)
                # if it's a 'surrounding' cell (FILLER2) we'll skip it (don't paint)
                if ch == FILLER2:
                    # increment horizontal (column) offset
                    h_offset += cell_sz - 2 * gridline_width
                    continue

                # get words starting with that coordinate
                words = self.cw.words.find_by_coord(coord)
                # use either the Across or the Down word (whichever is found)
                w = words['h'] or words['v']
                # cell format settings -- for a normal cell...
                dic_format = CWSettings.settings['cell_format']['NORMAL']
                if ch == FILLER:
                    # ...for a blocked (FILLER) cell...
                    dic_format = CWSettings.settings['cell_format']['FILLER']
                elif ch == BLANK:
                    # ...for a blank cell...
                    dic_format = CWSettings.settings['cell_format']['BLANK']

                # pick corresponding brush, pen and font for cell
                brush_cell = QtGui.QBrush(QtGui.QColor.fromRgba(dic_format['bg_color']), dic_format['bg_pattern'])
                brush_cell_border = QtGui.QBrush(QtGui.QColor.fromRgba(CWSettings.settings['grid_style']['line_color']))
                pen_cell = QtGui.QPen(brush_cell_border, gridline_width,
                                      CWSettings.settings['grid_style']['line'])
                font_cell = make_font(dic_format['font_name'], dic_format['font_size'],
                                      dic_format['font_weight'], dic_format['font_italic'])
                pen_cell_font = QtGui.QPen(QtGui.QColor.fromRgba(dic_format['fg_color']))

                # draw cell rect (accounting for border width)
                cell_rect = QtCore.QRectF(h_offset + gridline_width, v_offset + gridline_width, 
                                          cell_sz - 2 * gridline_width, cell_sz - 2 * gridline_width)
                painter.setPen(pen_cell)
                painter.setBrush(brush_cell)
                painter.drawRect(cell_rect)

                # draw word number (if configured to show in settings)
                if num_settings['show'] and not w is None:                    
                    pen_num_font = QtGui.QPen(QtGui.QColor.fromRgba(num_settings['color']))
                    font_num = make_font(num_settings['font_name'], num_settings['font_size'],
                                         num_settings['font_weight'], num_settings['font_italic'])
                    painter.setPen(pen_num_font)
                    painter.setFont(font_num)
                    # draw in top-left quarter of the cell
                    painter.drawText(cell_rect.x(), cell_rect.y(), cell_rect.width() // 2, cell_rect.height() // 2,
                                    QtCore.Qt.AlignCenter, str(w.num))

                # draw text (letter) if that's a normal cell (not blank or filler)
                if not clear_cw and ch != BLANK and ch != FILLER:
                    ch = ch.upper() if CWSettings.settings['grid_style']['char_case'] == 'upper' else ch.lower()
                    painter.setPen(pen_cell_font)
                    painter.setFont(font_cell)
                    painter.drawText(cell_rect.toRect(), dic_format['align'], ch)

                # increment h_offset (next column)
                h_offset += cell_sz - 2 * gridline_width

            # increment v_offset (next row)
            v_offset += cell_sz - 2 * gridline_width
    
    ## Updates the required GUI settings in the settings file before the application quits
    # (to restore them upon next startup).
    def update_settings_before_quit(self):
        # window size and pos
        pos = self.pos()
        CWSettings.settings['gui']['win_pos'] = (pos.x(), pos.y())
        CWSettings.settings['gui']['win_size'] = (self.width(), self.height())
        CWSettings.settings['common']['lang'] = self.combo_lang.currentData()
        # clues column widths
        self.update_clue_column_settings()

    ## Shows the Suggest Word dialog (forms::WordSuggestDialog) to suggest variants for a given word.
    # @param wordstr `str` the string representation (mask) of the target word
    # (crossword::FILLER, crossword::FILLER2 and crossword::BLANK symbols are used)
    # @returns `str` | `None` selected word in suggest dialog or `None` if nothing was selected (cancelled)
    def get_word_suggestion(self, wordstr):        
        self.update_wordsrc()     
        if (self.cw is None) or (not bool(self.wordsrc)) or (self.current_word is None): return None   
        dia_suggest = WordSuggestDialog(self, wordstr, False, self.cw.suggest, self)
        if not dia_suggest.exec(): return None
        return dia_suggest.selected or None

    ## Applies clues header column widths from CWSettings::settings.
    def adjust_clues_header_columns(self):
        header = self.tvClues.header()
        if header and not header.isHidden():
            for i in range(header.count()):
                if not self.tvClues.isColumnHidden(i):
                    width = CWSettings.settings['clues']['columns'][i]['width']
                    if width > 0:
                        self.tvClues.setColumnWidth(i, width) 

    ## Callback for MainWindow::updater, fires when a new release is found.
    # @param new_version `str` new version found on the server, e.g. '1.1'
    def on_get_recent(self, new_version):
        if 'version' in new_version:
            self.statusbar_l2.setText(_("Update ready: v. {}").format(new_version['version']))
        return True

    ## Stops all running threads.
    def stop_all_threads(self):
        for thread in self.threads:
            thread_ = getattr(self, thread, None)
            if thread_ is None or not thread_.isRunning(): continue
            thread_.quit()
            if not thread_.wait(5000):
                try:
                    thread_.terminate()
                except:
                    pass         

    ## Checks if the current crossword has been modified and asks user to save it.
    # @param cancellable `bool` whether the save dialog can be cancelled by user
    # @returns `str` user's reply from the request dialog, e.g. 'yes' or 'no'
    def check_save_required(self, cancellable=True):
        if self.cw and self.cw_modified:
            btn = ['yes', 'no']
            if cancellable: btn.append('cancel')
            reply = MsgBox(_('You have unsaved changes in your current crossword. Would you like to save them?'), self, _('Confirm Action'), 'ask', btn=btn)
            if reply == 'yes': 
                self.on_act_save(False)   
            return reply
        return None
        
    # ----- Overrides (events, etc) ----- #
    
    ## Fires when the window is about to show.
    # @param event `QtGui.QShowEvent` the handled event
    def showEvent(self, event):    
        # show 
        event.accept()

        # clear temps
        self.delete_temp_files()

        # update status bar
        self.statusbar_l1.setText(_("v. {}").format(APP_VERSION))
        if self.updater.git_installed:
            if CWSettings.settings['update']['auto_update']:
                self.updater.on_norecent = None
                self.on_act_update(False)
            else:
                self.updater.check_update()
        
    ## Fires when the window is about to close.
    # @param event `QtGui.QCloseEvent` the handled event
    def closeEvent(self, event):
        # kill threads
        self.stop_all_threads()
        # save cw
        if CWSettings.settings['common']['autosave_cw']:
            self.autosave_cw()
        else:
            self.check_save_required(False)
        # save settings file
        self.update_settings_before_quit()
        CWSettings.save_to_file(SETTINGS_FILE)
        # clear temps        
        self.delete_temp_files(False)
        # close
        event.accept()

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            filepath = mimeData.urls()[0].toString(QtCore.QUrl.PreferLocalFile).replace('/', os.path.sep)
            self.statusbar.showMessage(filepath)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QtGui.QDragLeaveEvent):
        self.statusbar.clearMessage()
        event.accept()

    def dropEvent(self, event: QtGui.QDropEvent):
        # handle dropped files
        mimeData = event.mimeData()
        if not mimeData.hasUrls(): 
            event.ignore()
            return
        # get first file path
        filepath = mimeData.urls()[0].toString(QtCore.QUrl.PreferLocalFile).replace('/', os.path.sep)
        ext = os.path.splitext(filepath)[1][1:].lower()
        try:
            if ext == 'pxjson':
                # load settings file
                if filepath != SETTINGS_FILE:
                    reply = MsgBox(_('Are you sure to apply new settings from "{}"?').format(filepath), 
                                    self, _('Confirm Action'), 'ask')
                    if reply == 'yes':
                        readSettings(filepath, False)
                        self.apply_config(False, False)
            else: 
                # assume cw file    
                reply = self.check_save_required()
                if reply == '' or reply == 'cancel': return
                self.open_cw(filepath)
        except Exception as err:
            MsgBox(str(err), self, _('Error'), 'error')
        self.statusbar.clearMessage() 

    # ----- SLOTS ----- #

    ## Fires when a key is pressed in the crossword grid.
    # @param event `QtGui.QKeyEvent` the handled event
    # @see forms::CwTable
    @QtCore.pyqtSlot(QtGui.QKeyEvent)
    def on_cw_key(self, event: QtGui.QKeyEvent):
        # get key
        key = event.key()   
        # get text
        txt = event.text().strip()
        # filter unused
        if key != QtCore.Qt.Key_Delete and key != QtCore.Qt.Key_Backspace and \
            key != QtCore.Qt.Key_Space and \
            not txt in (BLANK, FILLER, FILLER2) and not txt.isalpha():
                return 
        # get modifiers (e.g. Ctrl, Shift, Alt)
        modifiers = event.modifiers()
        # find focused item
        cell_item = self.twCw.currentItem()
        # quit if no selected item
        if not cell_item: return
        is_filler = cell_item.text() in (FILLER, FILLER2)
        # quit if it's a filler and grid is not in edit mode
        if is_filler and not self.act_edit.isChecked(): return
        
        coord = (cell_item.column(), cell_item.row())
        inc = -1 if key == QtCore.Qt.Key_Backspace else 1           
        next_item = self.twCw.item(cell_item.row() if self.current_word.dir == 'h' else cell_item.row() + inc,
                                   cell_item.column() + inc if self.current_word.dir == 'h' else cell_item.column()) \
                                   if self.current_word else None
        
        if key == QtCore.Qt.Key_Delete or key == QtCore.Qt.Key_Backspace:            
            
            if modifiers == QtCore.Qt.NoModifier:
                # delete current
                self.cw.words.put_char(coord, BLANK)
                if is_filler:
                    self.cw.words.reset()
                    self.cw.reset_used()
                    self.update_cw_grid()
                    return
                else:
                    cell_item.setText('')
                    self.cw.reset_used()
                    self.update_clue_replies(coord)
                
            elif modifiers == QtCore.Qt.ControlModifier:
                # clear word
                if self.current_word: 
                    self.cw.clear_word(self.current_word, False)
                    #self.cw.words.reset()
                    self.update_cw_grid()
                    return
            
            elif modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                # clear word forcibly
                if self.current_word: 
                    self.cw.clear_word(self.current_word, True)
                    #self.cw.words.reset()
                    self.update_cw_grid()
                    return
            
            if next_item and not next_item.text() in (FILLER, FILLER2):
                self.twCw.setCurrentItem(next_item)
            else:
                self.reformat_cells()
                
        elif key == QtCore.Qt.Key_Space:
            # flip current word
            self.update_current_word('flip')
            self.reformat_cells()

        else:  

            txt = event.text()
            txt = BLANK if not txt.strip() else txt[0]
            
            if not self.act_edit.isChecked() and txt in (FILLER, FILLER2):
                return
            # set text
            old_txt = self.cw.words.get_char(coord)
            try:
                self.cw.words.put_char(coord, txt)
                self.cw.reset_used()
            except CWError as err:
                #self.cw.words.put_char(coord, BLANK)
                return
                
            txt = self.cw.words.get_char(coord)
            if txt in (FILLER, FILLER2):
                self.cw.words.reset()
                self.cw.reset_used()
                self.update_cw_grid()
                return
            else:
                txt = txt.lower() if CWSettings.settings['grid_style']['char_case'] == 'lower' else txt.upper()
                cell_item.setText('' if txt == BLANK else txt)
                self.update_clue_replies(coord)
                if txt != old_txt: self.cw_modified = True
                self.update_actions()
            
            if next_item and not next_item.text() in (FILLER, FILLER2):
                self.twCw.setCurrentItem(next_item)
            else:
                self.reformat_cells()

    ## Fires when the application is about to update.
    # @param old_version `str` the current app version
    # @param new_version `str` the new app version found on the server
    # @returns `bool` `True` if user accepts the update or `False` otherwise
    def on_before_update(self, old_version, new_version):
        option = QtWidgets.QMessageBox.question(self, _('Application update'),
                _("Do you wish to update your current version {} "
                "to version {}\n"
                "(release date: {})?").format(old_version, new_version['version'], new_version['date']))
        return option == QtWidgets.QMessageBox.Yes

    ## Fires when the updater has found no newer versions on the server.
    def on_norecent(self):
        MsgBox(_('No updates are available'), self)
                        
    # ----- Slots ----- #
    
    ## Slot for MainWindow::act_new: creates a new crossword from file, structure or parameters.
    @QtCore.pyqtSlot(bool)        
    def on_act_new(self, checked):

        reply = self.check_save_required()
        if reply == '' or reply == 'cancel': return

        if not hasattr(self, 'dia_load'):
            ## `forms::LoadCwDialog` CW load dialog
            self.dia_load = LoadCwDialog(self)
        if not self.dia_load.exec(): return
        if self.cw: self.cw.closelog()
        
        self.cw_file = ''
        
        if self.dia_load.rb_grid.isChecked():
            selected_path = self.dia_load.le_pattern.text()
            self.cw = Crossword(data=self.grid_from_file(selected_path), data_type='grid',
                                wordsource=self.wordsrc, wordfilter=self.on_filter_word, pos=CWSettings.settings['cw_settings']['pos'],
                                log=CWSettings.settings['cw_settings']['log'])
            self.cw_file = selected_path
        
        elif self.dia_load.rb_file.isChecked():
            selected_path = self.dia_load.le_file.text()
            self.cw = Crossword(data=selected_path, data_type='file',
                                wordsource=self.wordsrc, wordfilter=self.on_filter_word, pos=CWSettings.settings['cw_settings']['pos'],
                                log=CWSettings.settings['cw_settings']['log'])
            self.cw_file = selected_path
       
        elif self.dia_load.rb_empty.isChecked():
            cols = int(self.dia_load.le_cols.text())
            rows = int(self.dia_load.le_rows.text())
            patn = self.dia_load.combo_pattern.currentIndex() + 1
            self.cw = Crossword(data=Crossword.basic_grid(cols, rows, patn), data_type='grid',
                                wordsource=self.wordsrc, wordfilter=self.on_filter_word, pos=CWSettings.settings['cw_settings']['pos'],
                                log=CWSettings.settings['cw_settings']['log'])            
        else:
            return

        #print(str(self.cw.words.info))
        self.update_cw()
        
        if self.dia_load.rb_empty.isChecked():
            self.act_edit.setChecked(True)
            
    ## Slot for MainWindow::act_open: loads crossword from a file (showing an Open File dialog).
    # @see open_cw()
    @QtCore.pyqtSlot(bool)
    def on_act_open(self, checked):

        reply = self.check_save_required()
        if reply == '' or reply == 'cancel': return

        selected_path = QtWidgets.QFileDialog.getOpenFileName(self, _('Select file'), os.getcwd(), _('Crossword files (*.xpf *.ipuz);;All files (*.*)'))
        if not selected_path[0]: return
        self.open_cw(selected_path[0].replace('/', os.sep))
    
    ## Slot for MainWindow::act_save: saves current crossword to the same file it was opened from
    # and resets its modified status to `False`.
    # @see save_cw()
    @QtCore.pyqtSlot(bool)
    def on_act_save(self, checked):
        if not self.cw or not self.cw_modified: return
        if not self.cw_file:
            self.on_act_saveas(False)
        else:
            self.save_cw()   

    ## Slot for MainWindow::act_saveas: shows a Save As dialog and saves current crossword to the selected file
    # and resets its modified status to `False`.
    # @see save_cw()
    @QtCore.pyqtSlot(bool)
    def on_act_saveas(self, checked):
        if not self.cw: return
        
        CWSAVE_FILTERS = [_('Crossword file (*.xpf *.ipuz)'), _('PDF file (*.pdf)'), 
                  _('Image file (*.jpg *.png *.tif *.tiff *.bmp)'), _('SVG vector image (*.svg)'),
                  _('Text file (*.txt)'), _('All files (*.*)')]
        fname = 'crossword.xpf'
        selected_path = QtWidgets.QFileDialog.getSaveFileName(self, _('Select file'), os.path.join(os.getcwd(), fname), 
            ';;'.join(CWSAVE_FILTERS), CWSAVE_FILTERS[0])
        if not selected_path[0]: return
        self.save_cw(selected_path[0].replace('/', os.sep), selected_path[1])

    ## Slot for MainWindow::act_reload: reloads current crossword from the original file
    # (user will be asked to save the changes first, if the cw has been modified).
    @QtCore.pyqtSlot(bool)
    def on_act_reload(self, checked):
        if not self.cw_file: return
        if self.cw and self.cw_modified:
            reply = MsgBox(_('You have unsaved changes in your current crossword. Are you sure to reload it from the file (all changes will be lost)?'), self, _('Confirm Action'), 'ask')
            if reply != 'yes': return
        old_cw = self.cw
        try:
            self.cw = Crossword(data=self.cw_file, data_type='file',
                                    wordsource=self.wordsrc, wordfilter=self.on_filter_word, pos=CWSettings.settings['cw_settings']['pos'],
                                    log=CWSettings.settings['cw_settings']['log'])
            self.update_cw()
        except Exception as err:
            self._log(err)
            try:
                self.cw = old_cw
                self.update_cw()
            except Exception as err2:
                self._log(err2)

    ## Slot for MainWindow::act_close: closes current crossword calling close_cw().
    @QtCore.pyqtSlot(bool)
    def on_act_close(self, checked):
        reply = self.check_save_required()
        if reply == '' or reply == 'cancel': return
        self.close_cw()

    ## @brief Slot for MainWindow::act_share: shares current crossword in social networks.
    # The share dialog MainWindow::dia_share is shown for user to configure the sharing settings.
    @QtCore.pyqtSlot(bool)
    def on_act_share(self, checked):
        ## share settings dialog    
        self.dia_share = ShareDialog(self, self)
        if not self.dia_share.exec(): return
        if not hasattr(self, 'share_thread') or self.share_thread is None:
            self.share_thread = ShareThread(on_progress=self.on_share_progress, 
            on_upload=self.on_share_upload, on_clipboard_write=self.on_share_clipboard_write,
            on_apikey_required=self.on_share_apikey_required, on_bearer_required=self.on_share_bearer_required,
            on_prepare_url=self.on_share_prepare_url,
            on_start=self.on_share_start, on_finish=self.on_share_finish, on_run=self.on_share_run,
            on_error=self.on_share_error)
        self.share_thread.start()
        
    ## Slot for MainWindow::act_exit: quits the application calling `close()` on the main window.
    @QtCore.pyqtSlot(bool)
    def on_act_exit(self, checked):
        self.close()

    ## @brief Slot for MainWindow::act_addrow: adds a new row after the selected one.
    # The action is available only in the Editing mode (when MainWindow::act_edit is checked).
    @QtCore.pyqtSlot(bool)
    def on_act_addrow(self, checked):
        if not self.cw or not self.act_edit.isChecked(): return 
        if self.twCw.currentRow() >= 0:
            self.cw.words.add_row(self.twCw.currentRow())
            self.update_cw()

    ## @brief Slot for MainWindow::act_addcol: adds a new column after the selected one.
    # The action is available only in the Editing mode (when MainWindow::act_edit is checked).
    @QtCore.pyqtSlot(bool)
    def on_act_addcol(self, checked):
        if not self.cw or not self.act_edit.isChecked(): return 
        if self.twCw.currentColumn() >= 0:
            self.cw.words.add_column(self.twCw.currentColumn())
            self.update_cw()

    ## @brief Slot for MainWindow::act_delrow: deletes the selected row.
    # The action is available only in the Editing mode (when MainWindow::act_edit is checked).
    @QtCore.pyqtSlot(bool)
    def on_act_delrow(self, checked):
        if not self.cw or not self.act_edit.isChecked(): return 
        if self.twCw.currentRow() >= 0:
            self.cw.words.remove_row(self.twCw.currentRow())
            self.update_cw()

    ## @brief Slot for MainWindow::act_delcol: deletes the selected column.
    # The action is available only in the Editing mode (when MainWindow::act_edit is checked).
    @QtCore.pyqtSlot(bool)
    def on_act_delcol(self, checked):
        if not self.cw or not self.act_edit.isChecked(): return 
        if self.twCw.currentColumn() >= 0:
            self.cw.words.remove_column(self.twCw.currentColumn())
            self.update_cw()

    ## @brief Slot for MainWindow::act_reflect: reflects (duplicates) the current cw grid
    # (all cells) to any position (left, right, up, down).
    # The action is available only in the Editing mode (when MainWindow::act_edit is checked).
    @QtCore.pyqtSlot(bool)
    def on_act_reflect(self, checked):
        if not self.cw or not self.act_edit.isChecked(): return 
        if not hasattr(self, 'dia_reflect'):
            ## `forms::ReflectGridDialog` reflect / duplicate dialog
            self.dia_reflect = ReflectGridDialog(self)
        if not self.dia_reflect.exec(): return
        direction = ''
        if self.dia_reflect.act_down.isChecked():
            direction = 'd'
        elif self.dia_reflect.act_up.isChecked():
            direction = 'u'
        elif self.dia_reflect.act_right.isChecked():
            direction = 'r'
        elif self.dia_reflect.act_left.isChecked():
            direction = 'l'
        border = ''
        if self.dia_reflect.act_b1.isChecked():
            border = '  '
        elif self.dia_reflect.act_b2.isChecked():
            border = '* '
        elif self.dia_reflect.act_b3.isChecked():
            border = ' *'
        elif self.dia_reflect.act_b4.isChecked():
            border = '**'
        self.cw.words.reflect(direction, self.dia_reflect.chb_mirror.isChecked(), self.dia_reflect.chb_reverse.isChecked(), border)
        self.update_cw()

    ## @brief Slot for MainWindow::act_clear_wd: clears currently selected word without affecting
    # any crossing words.
    # This action effectively clears only the 'free' letters in the selected word.
    # @see Compare with on_act_erase_wd() that erases all letters in the word.
    # Also see Crossword::clear_word()
    @QtCore.pyqtSlot(bool)
    def on_act_clear_wd(self, checked):
        if not self.cw or not self.current_word or self.cw.words.is_word_blank(self.current_word):
            return
        self.cw.clear_word(self.current_word, False)
        self.update_cw_grid()

    ## @brief Slot for MainWindow::act_erase_wd: clears currently selected word (all letters).
    # Compared to on_act_clear_wd(), this action affects crossing words, if any, since
    # it clears ALL the letters in the word, clearing them from the crossing words as well.
    # @see Also see Crossword::clear_word()
    @QtCore.pyqtSlot(bool)
    def on_act_erase_wd(self, checked):
        if not self.cw or not self.current_word or self.cw.words.is_word_blank(self.current_word):
            return
        self.cw.clear_word(self.current_word, True)
        self.update_cw_grid()
    
    ## Slot for MainWindow::act_gen: generates (fills) the current crossword taking word
    # suggestions from the active word sources.
    # @see Crossword::generate()
    @QtCore.pyqtSlot(bool)        
    def on_act_gen(self, checked):
        if not self.cw: return     
        if not hasattr(self, 'gen_thread') or self.gen_thread is None:
            self.gen_thread = GenThread(on_gen_timeout=self.on_gen_timeout, on_gen_stopped=self.on_gen_stop, 
                                    on_gen_validate=self.on_gen_validate, on_gen_progress=self.on_gen_progress,
                                    on_start=self.on_generate_start, on_finish=self.on_generate_finish,
                                    on_run=self.generate_cw_worker, on_error=self.on_gen_error) 
        self.gen_thread.start()
        self.update_actions()
        
    ## @brief Slot for MainWindow::act_stop: stops the currently running operation(s).
    # These operations can be either cw generation or cw sharing, which run
    # in a separate thread, to avoid blocking the UI.
    # @see stop_all_threads()
    @QtCore.pyqtSlot(bool)        
    def on_act_stop(self, checked):
        if checked:
            self.stop_all_threads()

    ## @brief On Changed slot for MainWindow::act_stop.
    # Hides or shows the Stop button in the status bar based on the action's visibility.
    @QtCore.pyqtSlot() 
    def on_act_stop_changed(self):
        if hasattr(self, 'statusbar_btnstop'):
            self.statusbar_btnstop.setVisible(self.act_stop.isVisible())
    
    ## @brief Slot for MainWindow::act_edit: updates cell formatting in crossword and actions.
    @QtCore.pyqtSlot(bool)        
    def on_act_edit(self, checked):
        self.reformat_cells()
        self.update_actions()

    ## @brief Slot for MainWindow::act_view_showtoolbar: shows or hides the main toolbar.
    @QtCore.pyqtSlot(bool)
    def on_act_view_showtoolbar(self, checked):
        last_tb_pos = CWSettings.settings['gui']['toolbar_pos']
        if checked:
            tb = last_tb_pos if last_tb_pos < 4 else 0
            TOOLBAR_AREAS = {0: QtCore.Qt.TopToolBarArea, 1: QtCore.Qt.BottomToolBarArea, 2: QtCore.Qt.LeftToolBarArea, 3: QtCore.Qt.RightToolBarArea}
            self.addToolBar(TOOLBAR_AREAS[tb], self.toolbar_main)
            self.toolbar_main.show()
            CWSettings.settings['gui']['toolbar_pos'] = tb
        else:
            self.toolbar_main.hide()
            CWSettings.settings['gui']['toolbar_pos'] = 4

    ## @brief Slot for MainWindow::act_editclue: activates the editing mode for the current word's clue.
    @QtCore.pyqtSlot(bool)        
    def on_act_editclue(self, checked):
        clue = self._clue_items_from_word(self.current_word)
        if not clue: return
        index = clue['clue'].index()
        if not self.tvClues.isIndexHidden(index):
            self.tvClues.setFocus()
            self.tvClues.edit(index)
    
    ## @brief Slot for MainWindow::act_clear: clears the current crossword.
    # @see Crossword::clear()
    @QtCore.pyqtSlot(bool)        
    def on_act_clear(self, checked):
        if not self.cw: return
        self.cw.clear()
        self.update_cw_grid()

    ## @brief Slot for MainWindow::act_suggest: brings up a list of words for the selected one in the grid
    # and lets the user place it into the grid.
    # @see get_word_suggestion()
    @QtCore.pyqtSlot(bool)        
    def on_act_suggest(self, checked):
        if not self.cw: return
        wordstr = self.cw.words.get_word_str(self.current_word)
        sug = self.get_word_suggestion(wordstr)
        if not sug or sug.lower() == wordstr.lower(): return
        #print(f"Changing '{wordstr}' for '{sug}'...")
        self.cw.change_word(self.current_word, sug)
        self.update_cw_grid()

    ## @brief Slot for MainWindow::act_lookup: looks up the current word's definition / meaning
    # in a dictionary and/or Google.
    # The looked-up definition may then be used to fill the corresponding clue.
    @QtCore.pyqtSlot(bool)
    def on_act_lookup(self, checked):
        if not self.cw: return
                    
        if CWSettings.settings['lookup']['dics']['show'] or CWSettings.settings['lookup']['google']['show']:
            wordstr = self.cw.words.get_word_str(self.current_word)
            if not hasattr(self, 'dia_lookup'):
                ## word meaning lookup dialog
                self.dia_lookup = DefLookupDialog(wordstr, parent=self)
            else:
                self.dia_lookup.word = wordstr
                self.dia_lookup.init()
            if self.dia_lookup.exec():
                # insert definition into clue
                txt = ''
                if self.dia_lookup.rb_dict.isChecked():
                    txt = self.dia_lookup.te_dict_defs.toPlainText().strip()
                else:
                    txt = self.dia_lookup.te_google_res.toPlainText().strip()
                clue_items = self._clue_items_from_word(self.current_word)
                if clue_items and txt:
                    clue_items['clue'].setText(txt)
                    self.current_word.clue = txt
                    self.reformat_clues()
        else:
            MsgBox(_('No lookup sources are active! Please go to Settings (F11) to verify your lookup source configuration.'), 
                   self, _('No Lookup Sources'), 'warn')
        
    ## @brief Slot for MainWindow::act_wsrc: opens the word source settings to let the use
    # choose / add word sources for crossword generation.
    @QtCore.pyqtSlot(bool) 
    def on_act_wsrc(self, checked):
        self.dia_settings.tree.setCurrentItem(self.dia_settings.tree.topLevelItem(2).child(0))
        self.on_act_config(False)
    
    ## @brief Slot for MainWindow::act_info: shows the crossword information window
    # where the user can change cw attributes like `title`, `author`, etc.
    # @see CwInfoDialog
    @QtCore.pyqtSlot(bool)        
    def on_act_info(self, checked):
        if not self.cw: return
        if not hasattr(self, 'dia_info'):
            ## crossword information edit dialog
            self.dia_info = CwInfoDialog(self, self)
        else:
            self.dia_info.init()            
        if self.dia_info.exec():
            self.cw.words.info = self.dia_info.to_info()
        
    ## @brief Slot for MainWindow::act_print: prints current CW and/or clues to printer or PDF.
    # @see print_cw()
    @QtCore.pyqtSlot(bool)        
    def on_act_print(self, checked):
        if not self.cw: return
        self.print_cw()
    
    ## @brief Slot for MainWindow::act_config: shows the application Settings dialog.
    # If the dialog is closed by pressing OK, the new settings are applied with apply_config()
    @QtCore.pyqtSlot(bool)        
    def on_act_config(self, checked):
        if not self.dia_settings.exec(): return
        settings = self.dia_settings.to_settings()
        # apply settings only if they are different from current
        if json.dumps(settings, sort_keys=True) != json.dumps(CWSettings.settings, sort_keys=True):
            CWSettings.settings = settings
            self.apply_config()

    ## @brief Slot for MainWindow::act_update: checks for app updates on the server (github).
    # If a new version is available and the user accepts it, the app will close down
    # and update itself, then start up again.
    # @see MainWindow::updater
    @QtCore.pyqtSlot(bool)        
    def on_act_update(self, checked):    
        if not self.updater.git_installed: return
        # run update
        if self.updater.update(True) == False: return
        # close self
        self.close()
   
    ## @brief Slot for MainWindow::act_help: opens up the Help documentation.
    @QtCore.pyqtSlot(bool)        
    def on_act_help(self, checked):
        MsgBox(_('To be implemented in next release ))'), self, _('Show help docs')) 

    ## @brief Slot for MainWindow::act_about: shows the About dialog.
    @QtCore.pyqtSlot(bool)        
    def on_act_about(self, checked):
        if not hasattr(self, 'dia_about'):
            ## About dialog
            self.dia_about = AboutDialog(self)
        self.dia_about.exec()

    ## @brief Slot for MainWindow::act_stats: shows the current crossword's statistics.
    # The stats is accumulated with Wordgrid::update_stats() and includes the following data:
    # <pre>
    #   * word count
    #   * completed word count
    #   * blank word count
    #   * Down word count
    #   * Across word count
    #   * words with completed clues count
    # </pre>
    # The data is visualized as an HTML chart in the inbuilt or system web browser.
    @QtCore.pyqtSlot(bool)
    def on_act_stats(self, checked):
        if not self.cw: return
        self.cw.words.update_stats()

        def on_chart_save(filename):
            url = os.path.abspath(filename)
            self.garbage.append(url)
            if not hasattr(self, 'browser'):
                ## inbuilt web browser
                self.browser = Browser()
                self.browser.navigate(url)
            try:
                self.browser.navigate(url, False)
            except:
                traceback.print_exc(limit=None)

        d1 = data_from_dict({'Words': self.cw.words.stats['word_count'],
              'Complete': self.cw.words.stats['complete_word_count'],
              'Blank': self.cw.words.stats['blank_word_count'],
              'Across': self.cw.words.stats['across_word_count'],
              'Down': self.cw.words.stats['down_word_count'],
              'With clues': self.cw.words.stats['withclues_word_count']})
        c = self.cw.words.stats['word_count']
        d1['labels'] = [f'{d*100.0/c:.0f} %' for d in d1['y']]

        make_chart(d1, 'bar', x_title='y', x_props={'type': 'quantitative', 'title': None, 'scale': (0, max(d1['y'] + 10))}, 
                   y_title='x', y_props={'type': 'nominal', 'title': None, 'sort': list(d1['x'])}, 
                   color={'shorthand': 'x:N', 'legend': None},
                   text_col='labels:N', 
                   text_props={'align': 'left', 'baseline': 'middle', 'dx': 3},
                   interactive=False, scale_factor=10, svg=True, on_save=on_chart_save)

    ## @brief Fires when MainWindow::statusbar_l2 is double-clicked.
    # When double-clicked on the app version (if a new version is available), the updater is launched.
    # @see on_act_update()
    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def on_statusbar_l2_dblclicked(self, event):
        if not self.statusbar_l2.text(): return
        self.on_act_update(False)
        
    ## @brief Fires when MainWindow::slider_cw_scale is moved: rescales the crossword grid.
    # @param value `int` the MainWindow::slider_cw_scale value (scale %)
    # @see scale_cw()
    @QtCore.pyqtSlot(int)
    def on_slider_cw_scale(self, value):
        self.scale_cw(value)        
        
    ## @brief Fires when a new cw grid cell is focused.
    # @param current `QtWidgets.QTableWidgetItem` the currently focused cell
    # @param previous `QtWidgets.QTableWidgetItem` the previously focused cell
    @QtCore.pyqtSlot(QtWidgets.QTableWidgetItem, QtWidgets.QTableWidgetItem)
    def on_cw_current_item_changed(self, current, previous):      
        self.update_current_word('flip' if self.last_pressed_item==current else 'current')            
        self.reformat_cells()
        self.last_pressed_item = current
        
    ## @brief Fires when a cw grid cell is clicked (pressed).
    # @param item `QtWidgets.QTableWidgetItem` the pressed cell
    @QtCore.pyqtSlot(QtWidgets.QTableWidgetItem)
    def on_cw_item_clicked(self, item):
        if self.twCw.currentItem() == item:
            self.update_current_word('flip' if self.last_pressed_item==item else 'current')            
            self.reformat_cells()
            self.last_pressed_item = item

    ## @brief Fires when the custom context meny is requested on the crossword grid.
    # @param point `QtCore.QPoint` the current cursor position (relative to grid coordinates)
    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_twCw_contextmenu(self, point):
        if not self.current_word: return
        cell_item = self.twCw.itemAt(point)
        if not cell_item: return
        self.menu_crossword.exec(self.twCw.mapToGlobal(point))

    ## @brief Fires when the custom context meny is requested on the main toolbar.
    # @param point `QtCore.QPoint` the current cursor position (relative to toolbar coordinates)
    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_toolbar_contextmenu(self, point):
        @QtCore.pyqtSlot() 
        def on_tb_contextmenuaction():
            self.dia_settings.tree.setCurrentItem(self.dia_settings.tree.topLevelItem(3).child(3))
            self.on_act_config(False)
        menu = QtWidgets.QMenu(self)
        menu.addAction(QtGui.QIcon(f"{ICONFOLDER}/settings-5.png"), _('Configure toolbar...'), on_tb_contextmenuaction)
        menu.exec(self.toolbar_main.mapToGlobal(point))

    ## @brief Fires when one or severals clue rows are selected in MainWindow::tvClues.
    # @param selected `QtCore.QItemSelection` the selected items
    # @param deselected `QtCore.QItemSelection` the deselected items
    @QtCore.pyqtSlot(QtCore.QItemSelection, QtCore.QItemSelection)
    def on_tvClues_selected(self, selected, deselected):
        model = self.tvClues.model()
        for idx in selected.indexes():
            item = model.itemFromIndex(idx)
            if not item or item.column() > 0: continue
            item.setIcon(QtGui.QIcon(f"{ICONFOLDER}/flag-2.png"))
        for idx in deselected.indexes():
            item = model.itemFromIndex(idx)
            if not item or item.column() > 0: continue
            item.setIcon(QtGui.QIcon())

    ## @brief Fires when the currenly selected clue item in MainWindow::tvClues has changed.
    # @param current `QtCore.QModelIndex` the currently selected items
    # @param previous `QtCore.QModelIndex` the previously selected items
    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def on_tvClues_current_changed(self, current, previous):
        if self.twCw.hasFocus(): return
        model = self.tvClues.model()
        item = model.itemFromIndex(current)
        if not item: return
        word = self._word_from_clue_item(item)     
        if word:  
            self.current_word = word
            self.twCw.setCurrentItem(None)
            self.twCw.setCurrentCell(word.start[1], word.start[0])

    ## @brief Fires when the clues table columns have been moved by dragging.
    # @param logicalIndex `int` the column's logical (independent) index
    # @param oldVisualIndex `int` the column's previous position (as seen in the table)
    # @param newVisualIndex `int` the column's new position (as seen in the table)
    # @see update_clue_column_settings()
    @QtCore.pyqtSlot(int, int, int)
    def on_tvClues_column_moved(self, logicalIndex, oldVisualIndex, newVisualIndex):
        # save new column order to global settings
        self.update_clue_column_settings()

    ## @brief Fires every time a cell in clues table has been edited (manually) and
    # is about to write data back to the underlying model. 
    # We implement this slot to validate the entered text, update the CW grid and the clues table.
    # @param editor `QtWidgets.QWidget` the internal widget used for editing the clue item (here = QLineEdit)
    @QtCore.pyqtSlot('QWidget*')
    def on_clues_editor_commit(self, editor):      
        model = self.tvClues.model()
        if not model: return
        index = self.tvClues.currentIndex()
        item = model.itemFromIndex(index)
        if not item: return
        word = self._word_from_clue_item(item)
        if not word: return
        parent = item.parent()
        if parent is None: return
        item_params = {'parent': (parent.row(), parent.column()) if parent else None, 'item': (item.row(), item.column())}
        txt = editor.text()
        col = item.column()
        if col == 4:
            # word text 
            ltxt = len(txt)
            lword = len(word)
            if ltxt > lword:
                txt = txt[:lword]
            elif ltxt < lword:
                txt += BLANK * (lword - ltxt)
            try:
                #print(f"Changing '{str(word)}' to '{txt}'...")
                item.setText(txt)
                self.cw.change_word(word, txt)
                self.update_cw_grid()      
            except CWError as err:
                self._log(err)

        elif col == 2:
            # word clue
            item.setText(txt)
            word.clue = txt
            self.reformat_clues()

        # re-activate clue cell (after update_cw_grid operation - full model reset)
        model = self.tvClues.model()
        parent = model.item(item_params['parent'][0], item_params['parent'][1])
        if parent:
            item = parent.child(item_params['item'][0], item_params['item'][1])
            if item:
                self.tvClues.setCurrentIndex(item.index())
        # restore focus (update_cw_grid removes focus from tvClues)
        self.tvClues.setFocus()

    def set_selected_lang(self):
        CWSettings.settings['common']['lang'] = self.combo_lang.currentData()

    ## @brief Fires when a new language in the language combo is picked.
    # @param index `int` the selected index in the language combo
    @QtCore.pyqtSlot(int)
    def on_combo_lang(self, index):
        lang = self.combo_lang.itemData(index)
        sel_lang = None
        for l in APP_LANGUAGES:
            if l[1] == lang:
                sel_lang = l
                break
        if sel_lang is None: return
        if sel_lang == '': lang = ''
        CWSettings.settings['common']['lang'] = lang
        CWSettings.save_to_file(SETTINGS_FILE)
        reply = MsgBox(sel_lang[4], self, _('Language settings'), 'ask')
        if reply == 'yes': 
            restart_app(self.close)
