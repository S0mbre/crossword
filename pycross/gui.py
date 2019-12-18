# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

from PyQt5 import QtGui, QtCore, QtWidgets, QtPrintSupport, QtSvg
from subprocess import Popen
import os, json, re, threading, math, traceback
from utils.utils import *
from utils.update import Updater
from guisettings import CWSettings
from dbapi import Sqlitedb
from forms import (MsgBox, LoadCwDialog, CwTable, ClickableLabel, CrosswordMenu, 
                    SettingsDialog, WordSuggestDialog, PrintPreviewDialog,
                    CwInfoDialog, DefLookupDialog, ReflectGridDialog)
from crossword import Word, Crossword, CWError, FILLER, FILLER2, BLANK
from wordsrc import DBWordsource, TextWordsource, TextfileWordsource, MultiWordsource

## ******************************************************************************** ##

class GenThread(QThreadStump):
    sig_timeout = QtCore.pyqtSignal(float)
    sig_stopped = QtCore.pyqtSignal()
    sig_validate = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, on_gen_timeout=None, on_gen_stopped=None, on_gen_validate=None,  
                 on_start=None, on_finish=None, on_run=None, on_error=None):
        super().__init__(on_start=on_start, on_finish=on_finish, on_run=on_run, on_error=on_error)
        if on_gen_timeout: self.sig_timeout.connect(on_gen_timeout)
        if on_gen_stopped: self.sig_stopped.connect(on_gen_stopped)
        if on_gen_validate: self.sig_validate.connect(on_gen_validate)

## ******************************************************************************** ##

class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self):        
        super().__init__()
        self.readSettings()
        self.cw = None
        self.cw_file = ''                      # currently opened cw file
        self.cw_modified = True                # flag showing that current cw has been changed since last save
        self.current_word = None               # current word in grid
        self.last_pressed_item = None
        self.wordsrc = MultiWordsource()
        self.gen_thread = GenThread(on_gen_timeout=self.on_gen_timeout, on_gen_stopped=self.on_gen_stop, 
                                    on_gen_validate=self.on_gen_validate,
                                    on_start=self.on_generate_start, on_finish=self.on_generate_finish,
                                    on_run=self.generate_cw_worker, on_error=self.on_gen_error)
        self.updater = Updater(CWSettings.settings['update'], self.close, 
        self.on_get_recent, self.on_before_update, self.on_noupdate_available)
        self.initUI()
        
    def _log(self, what, end='\n'):
        print(what, end=end)
        
    def readSettings(self):
        sfile = os.path.abspath(SETTINGS_FILE)
        if not CWSettings.validate_file(sfile):
            CWSettings.save_to_file(sfile)
        else:
            try:
                CWSettings.load_from_file(sfile)
            except Exception as err:
                self._log(err)
    
    def initUI(self):
        self.UI_create_toolbar()  
        self.UI_create_menu()  
        self.UI_create_central_widget()
        self.UI_create_statusbar()
        self.UI_create_context_menus()
        
        self.setGeometry(CWSettings.settings['gui']['win_pos'][0], CWSettings.settings['gui']['win_pos'][1], 
            CWSettings.settings['gui']['win_size'][0], CWSettings.settings['gui']['win_size'][1])
        self.setMinimumSize(500, 300)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QtGui.QIcon(f"{ICONFOLDER}/main.png"))
        self.apply_config()        
        self.adjust_clues_header_columns()
        self.show()
        self.update_actions()
    
    def UI_create_toolbar(self):
        self.toolbar_main = QtWidgets.QToolBar()
        self.toolbar_main.setMovable(False)
        self.act_new = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/crossword.png"), 'New')
        self.act_new.setToolTip('Create new crossword (Ctrl+N)')
        self.act_new.setShortcut(QtGui.QKeySequence('Ctrl+n'))
        self.act_new.triggered.connect(self.on_act_new)
        self.act_open = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/folder-15.png"), 'Open')
        self.act_open.setToolTip('Open crossword from file (Ctrl+O)')
        self.act_open.setShortcut(QtGui.QKeySequence('Ctrl+o'))
        self.act_open.triggered.connect(self.on_act_open)
        self.act_save = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/save.png"), 'Save')
        self.act_save.setToolTip('Save crossword (Ctrl+S)')
        self.act_save.setShortcut(QtGui.QKeySequence('Ctrl+s'))
        self.act_save.triggered.connect(self.on_act_save)
        self.act_saveas = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/saveas.png"), 'Save As...')
        self.act_saveas.setToolTip('Save crossword as new file (Ctrl+Shift+S)')
        self.act_saveas.setShortcut(QtGui.QKeySequence('Ctrl+Shift+s'))
        self.act_saveas.triggered.connect(self.on_act_saveas)
        self.act_share = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/share-1.png"), 'Share...')
        self.act_share.setToolTip('Share crossword in social networks (F10)')
        self.act_share.setShortcut(QtGui.QKeySequence('F10'))
        self.act_share.triggered.connect(self.on_act_share)
        self.toolbar_main.addSeparator()
        self.act_edit = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/edit.png"), 'Edit')
        self.act_edit.setToolTip('Edit crossword (Ctrl+E)')
        self.act_edit.setCheckable(True)
        self.act_edit.setShortcut(QtGui.QKeySequence('Ctrl+e'))
        self.act_edit.toggled.connect(self.on_act_edit)   
        self.act_addrow = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/add_row.png"), 'Add row')
        self.act_addrow.setToolTip('Add row before selected')
        self.act_addrow.triggered.connect(self.on_act_addrow)     
        self.act_delrow = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/delete_row.png"), 'Delete row')
        self.act_delrow.setToolTip('Delete row')
        self.act_delrow.triggered.connect(self.on_act_delrow)
        self.act_addcol = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/add_col.png"), 'Add column')
        self.act_addcol.setToolTip('Add column before selected')
        self.act_addcol.triggered.connect(self.on_act_addcol)         
        self.act_delcol = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/delete_col.png"), 'Delete column')
        self.act_delcol.setToolTip('Delete column')
        self.act_delcol.triggered.connect(self.on_act_delcol)
        self.toolbar_main.addSeparator()
        self.act_reflect = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/windows-1.png"), 'Duplicate')
        self.act_reflect.setToolTip('Duplicate (reflect) grid cells to any direction')
        self.act_reflect.triggered.connect(self.on_act_reflect)
        self.toolbar_main.addSeparator()
        self.act_gen = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/flash.png"), 'Generate')
        self.act_gen.setToolTip('Generate (solve) crossword (Ctrl+G)')
        self.act_gen.setShortcut(QtGui.QKeySequence('Ctrl+g'))
        self.act_gen.triggered.connect(self.on_act_gen)
        self.act_stop = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/stop-1.png"), 'Stop')
        self.act_stop.setToolTip('Stop generation (Ctrl+Z)')
        self.act_stop.setShortcut(QtGui.QKeySequence('Ctrl+z'))
        self.act_stop.setCheckable(True)
        self.act_clear = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/dust.png"), 'Clear')
        self.act_clear.setToolTip('Clear all words (Ctrl+D)')
        self.act_clear.setShortcut(QtGui.QKeySequence('Ctrl+d'))
        self.act_clear.triggered.connect(self.on_act_clear)
        self.act_clear_wd = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/minus.png"), 'Clear word')
        self.act_clear_wd.setToolTip('Clear word')
        self.act_clear_wd.triggered.connect(self.on_act_clear_wd)
        self.act_erase_wd = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/error.png"), 'Erase word')
        self.act_erase_wd.setToolTip('Erase word')
        self.act_erase_wd.triggered.connect(self.on_act_erase_wd)
        self.act_suggest = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/magic-wand.png"), 'Suggest word')
        self.act_suggest.setToolTip('Suggest word (Ctrl+F)')
        self.act_suggest.setShortcut(QtGui.QKeySequence('Ctrl+f'))
        self.act_suggest.triggered.connect(self.on_act_suggest)
        self.act_lookup = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/worldwide.png"), 'Lookup word')
        self.act_lookup.setToolTip('Lookup word definition (Ctrl+L)')
        self.act_lookup.setShortcut(QtGui.QKeySequence('Ctrl+l'))
        self.act_lookup.triggered.connect(self.on_act_lookup)
        self.act_editclue = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/key.png"), 'Edit clue')
        self.act_editclue.setToolTip('Edit clue (Ctrl+K)')
        self.act_editclue.setShortcut(QtGui.QKeySequence('Ctrl+k'))
        self.act_editclue.triggered.connect(self.on_act_editclue)
        self.toolbar_main.addSeparator()
        self.act_wsrc = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/database-3.png"), 'Word sources')
        self.act_wsrc.setToolTip('Select wordsources (Ctrl+W)')
        self.act_wsrc.setShortcut(QtGui.QKeySequence('Ctrl+w'))
        self.act_wsrc.triggered.connect(self.on_act_wsrc)
        self.act_info = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/info1.png"), 'Info')
        self.act_info.setToolTip('Show / edit crossword info (Ctrl+I)')
        self.act_info.setShortcut(QtGui.QKeySequence('Ctrl+i'))
        self.act_info.triggered.connect(self.on_act_info)
        self.act_print = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/print.png"), 'Print')
        self.act_print.setToolTip('Print crossword and/or clues (Ctrl+P)')
        self.act_print.setShortcut(QtGui.QKeySequence('Ctrl+p'))
        self.act_print.triggered.connect(self.on_act_print)
        self.toolbar_main.addSeparator()
        self.act_config = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/settings-5.png"), 'Config')
        self.act_config.setToolTip('Configure parameters (F11)')
        self.act_config.setShortcut(QtGui.QKeySequence('F11'))
        self.act_config.triggered.connect(self.on_act_config)
        self.act_update = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/cloud-computing.png"), 'Check update')
        self.act_update.setToolTip('Check for updates (Ctrl+U)')
        self.act_update.setShortcut(QtGui.QKeySequence('Ctrl+u'))
        self.act_update.triggered.connect(self.on_act_update)
        self.act_help = self.toolbar_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/info.png"), 'Help')
        self.act_help.setToolTip('Show help (F1)')
        self.act_help.setShortcut(QtGui.QKeySequence('F1'))
        self.act_help.triggered.connect(self.on_act_help)
        self.addToolBar(self.toolbar_main)

    def UI_create_menu(self):
        self.menu_main = self.menuBar()
        self.menu_main_file = self.menu_main.addMenu('&File')
        self.menu_main_file.addAction(self.act_new)
        self.menu_main_file.addSeparator()
        self.menu_main_file.addAction(self.act_open)
        self.menu_main_file.addAction(self.act_save)
        self.menu_main_file.addAction(self.act_saveas)
        self.menu_main_file.addSeparator()
        self.menu_main_file.addAction(self.act_share)
        self.menu_main_file.addSeparator()
        self.menu_main_file.addAction(self.act_print)
        self.menu_main_file.addSeparator()
        self.act_exit = self.menu_main_file.addAction(QtGui.QIcon(f"{ICONFOLDER}/exit.png"), 'Exit')
        self.act_exit.setToolTip('Exit (Ctrl+q)')
        self.act_exit.setShortcut(QtGui.QKeySequence('Ctrl+q'))
        self.act_exit.triggered.connect(self.on_act_exit)

        self.menu_main_edit = self.menu_main.addMenu('&Edit')
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

        self.menu_main_view = self.menu_main.addMenu('&View')
        self.act_view_showtoolbar = self.menu_main_view.addAction('Show toolbar')
        self.act_view_showtoolbar.setCheckable(True)
        self.act_view_showtoolbar.setChecked(True)
        self.act_view_showtoolbar.setToolTip('Show / hide toolbar')
        self.act_view_showtoolbar.toggled.connect(self.on_act_view_showtoolbar)

        self.menu_main_gen = self.menu_main.addMenu('&Generate')
        self.menu_main_gen.addAction(self.act_gen)
        self.menu_main_gen.addAction(self.act_stop)
        self.menu_main_gen.addSeparator()
        self.menu_main_gen.addAction(self.act_wsrc)

        self.menu_main_help = self.menu_main.addMenu('&Help')
        self.menu_main_help.addAction(self.act_help)
        self.menu_main_help.addSeparator()
        self.menu_main_help.addAction(self.act_update)
    
    def UI_create_central_widget(self):
        # central widget
        self.splitter1 = QtWidgets.QSplitter()
        # cw layout container
        self.cw_widget = QtWidgets.QWidget()
        # cw layout
        self.layout_vcw = QtWidgets.QVBoxLayout()
        # cw grid
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
        
        # cw scale slider
        self.slider_cw_scale = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_cw_scale.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.slider_cw_scale.setMinimum(100)
        self.slider_cw_scale.setMaximum(300)
        self.slider_cw_scale.setSingleStep(10)
        self.slider_cw_scale.setPageStep(50)
        #self.slider_cw_scale.setTickPosition(QtWidgets.QSlider.TicksBelow)
        #self.slider_cw_scale.setTickInterval(10)
        self.slider_cw_scale.setValue(CWSettings.settings['grid_style']['scale'])
        self.l_cw_scale = QtWidgets.QLabel()
        self.l_cw_scale.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.slider_cw_scale.valueChanged.connect(self.on_slider_cw_scale)
        self.layout_cw_scale = QtWidgets.QHBoxLayout()
        self.layout_cw_scale.addWidget(self.slider_cw_scale)
        self.layout_cw_scale.addWidget(self.l_cw_scale)
        self.layout_vcw.addWidget(self.twCw)
        self.layout_vcw.addLayout(self.layout_cw_scale)
        # set layout to container
        self.cw_widget.setLayout(self.layout_vcw)        
        # add to splitter
        self.splitter1.addWidget(self.cw_widget)

        # clues panel
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
    
    def UI_create_statusbar(self):
        self.statusbar = QtWidgets.QStatusBar()        
        self.statusbar.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed) 
        self.statusbar_pbar = QtWidgets.QProgressBar(self.statusbar)
        self.statusbar_pbar.setTextVisible(True)
        self.statusbar_pbar.setRange(0, 100)
        self.statusbar_pbar.setValue(0)
        self.statusbar_pbar.setVisible(False)
        self.statusbar_l1 = QtWidgets.QLabel(self.statusbar)
        self.statusbar.addPermanentWidget(self.statusbar_l1)
        self.statusbar_l2 = ClickableLabel(self.statusbar)
        self.statusbar_l2.dblclicked.connect(self.on_statusbar_l2_dblclicked)
        color_to_stylesheet(QtGui.QColor(QtCore.Qt.darkGreen), self.statusbar_l2.styleSheet(), 'color')
        self.statusbar_l2.setStyleSheet('color: maroon;')
        self.statusbar_l2.setToolTip('Double-click to update')
        self.statusbar.addPermanentWidget(self.statusbar_l2)
        self.statusbar.addWidget(self.statusbar_pbar)
        #self.layout_hgrid3.addWidget(self.statusbar)
        self.setStatusBar(self.statusbar)
        
    def UI_create_context_menus(self):
        self.menu_crossword = CrosswordMenu(self, on_triggered=self.on_menu_crossword)
        
    def apply_config(self, save_settings=True):
        """
        Applies settings found in CWSettings.settings and updates the settings file.
        """
        # load cw
        self.autoload_cw()
        
        # gui
        if CWSettings.settings['gui']['theme'] and CWSettings.settings['gui']['theme'] != QtWidgets.QApplication.instance().style().objectName():
            QtWidgets.QApplication.instance().setStyle(CWSettings.settings['gui']['theme'])
        tb = CWSettings.settings['gui']['toolbar_pos']
        if tb < 4:
            TOOLBAR_AREAS = {0: QtCore.Qt.TopToolBarArea, 1: QtCore.Qt.BottomToolBarArea, 2: QtCore.Qt.LeftToolBarArea, 3: QtCore.Qt.RightToolBarArea}
            self.addToolBar(TOOLBAR_AREAS[tb], self.toolbar_main)
            self.toolbar_main.show()
            self.act_view_showtoolbar.setChecked(True)
        elif tb == 4:
            self.toolbar_main.hide()
            self.act_view_showtoolbar.setChecked(False)
            
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
        #style = 'QTableView {background-color: #ffa0a0a4; selection-background-color: #ffffff00; selection-color: #ff000000;} QTableView::item {border-style: solid; border-color: #ffa0a0a4; border-width: 7px; }'
        #print(style)
        self.twCw.setStyleSheet(style)
        # cell_format, numbers, cell size etc...
        self.update_cw(False)
        self.slider_cw_scale.setValue(CWSettings.settings['grid_style']['scale'])
        
        # save settings file
        if save_settings:
            sfile = os.path.abspath(SETTINGS_FILE)
            CWSettings.save_to_file(sfile)
        
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
                    
    def update_actions(self):
        b_cw = not self.cw is None
        gen_running = self.gen_thread.isRunning() if getattr(self, 'gen_thread', None) else False
        gen_interrupted = self.gen_thread.isInterruptionRequested() if getattr(self, 'gen_thread', None) else False
        self.act_new.setEnabled(not gen_running)
        self.act_open.setEnabled(not gen_running)
        self.act_save.setEnabled(b_cw and not gen_running and (self.cw_modified or not self.cw_file))
        self.act_saveas.setEnabled(b_cw and not gen_running)
        self.act_edit.setEnabled(b_cw and not gen_running)
        self.act_addcol.setEnabled(b_cw and not gen_running and self.act_edit.isChecked())
        self.act_addrow.setEnabled(b_cw and not gen_running and self.act_edit.isChecked())
        self.act_delcol.setEnabled(b_cw and not gen_running and self.act_edit.isChecked())
        self.act_delrow.setEnabled(b_cw and not gen_running and self.act_edit.isChecked())
        self.act_reflect.setEnabled(b_cw and not gen_running and self.act_edit.isChecked())
        self.act_gen.setEnabled(b_cw and not gen_running and bool(self.wordsrc))
        if not gen_running: self.act_stop.setChecked(False)
        self.act_stop.setEnabled(b_cw and gen_running and not gen_interrupted)        
        self.act_clear.setEnabled(b_cw and not gen_running)
        self.act_suggest.setEnabled(b_cw and not gen_running and bool(self.wordsrc) and (not self.current_word is None))
        self.act_lookup.setEnabled(b_cw and not gen_running and (not self.current_word is None) and not self.cw.words.is_word_blank(self.current_word))
        self.act_editclue.setEnabled(b_cw and not gen_running)
        self.act_info.setEnabled(b_cw and not gen_running)
        self.act_print.setEnabled(b_cw and not gen_running)
        self.act_config.setEnabled(not gen_running)
        self.act_help.setEnabled(not gen_running)
        self.twCw.setEnabled(b_cw and not gen_running)
        self.tvClues.setEnabled(b_cw and not gen_running)
        
    def update_wordsrc(self):
        """
        Updates self.wordsrc (of type MultiWordsource) from global settings
        in CWSettings.wordsrc.
        """
        self.wordsrc.clear()
        self.wordsrc.max_fetch = CWSettings.settings['wordsrc']['maxres']
        # MultiWordsource.order is by default 'prefer-last', so just append sources
        for src in CWSettings.settings['wordsrc']['sources']:
            if not src['active']: continue
            if src['type'] == 'db':
                if src['dbtype'].lower() == 'sqlite':
                    db = Sqlitedb()
                    if not db.setpath(src['file'], fullpath=(not src['file'].lower() in LANG), recreate=False, connect=True):
                        self._log(f"DB path {src['file']} unavailable!")
                        continue
                    self.wordsrc.add(DBWordsource(src['dbtables'], db))
                    
            elif src['type'] == 'file':
                self.wordsrc.add(TextfileWordsource(src['file'], enc=src['encoding'], delimiter=src['delim']))
                
            elif src['type'] == 'list' and src['words']:
                words = []
                if src['haspos']:                    
                    for w in src['words']:
                        w = w.split(src['delim'])
                        words.append((w[0], tuple(w[1:]) if len(w) > 1 else None))
                else:
                    words = src['words']
                self.wordsrc.add(TextWordsource(words))
        
    def update_cw(self, rescale=True):
        """
        Updates cw data and view.
        """
        # update grid
        self.update_cw_grid()
        # rescale grid
        if rescale:
            self.on_slider_cw_scale(CWSettings.settings['grid_style']['scale'])
            #self.scale_cw(CWSettings.settings['grid_style']['scale'])
            #self.slider_cw_scale.setValue(CWSettings.settings['grid_style']['scale'])
        # update window title
        self.setWindowTitle(f"{APP_NAME}{(' - ' + self.cw_file) if (self.cw_file and os.path.abspath(self.cw_file) != os.path.abspath(SAVEDCW_FILE)) else ''}")

    def grid_from_file(self, gridfile):
        """
        """
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
            print(err)
            
        return cwgrid
    
    def autosave_cw(self):
        if not self.cw:
            try:
                os.remove(SAVEDCW_FILE)
                return
            except:
                pass
        else:
            self.cw.words.to_file(SAVEDCW_FILE)
        
    def autoload_cw(self):
        if self.cw or not os.path.isfile(SAVEDCW_FILE): return
        try:
            self.cw = Crossword(data=os.path.abspath(SAVEDCW_FILE), data_type='file',
                                    wordsource=self.wordsrc, wordfilter=self.on_filter_word, pos=CWSettings.settings['cw_settings']['pos'],
                                    log=CWSettings.settings['cw_settings']['log'])
            self.cw_file = SAVEDCW_FILE
            self.update_cw()
            #print(str(self.cw.words.info))
        except Exception as err:
            print(err)
            self.cw = None
    
    def _item_in_word(self, cell_item: QtWidgets.QTableWidgetItem, word: Word):
        return word.does_cross((cell_item.column(), cell_item.row()))
    
    def update_current_word(self, on_intersect='current'):
        """
        on_intersect:
            * current = leave current direction
            * h = switch to across word
            * v = switch to down word
            * flip = toggle current from across to down or vice-versa
        """
        if not self.cw: return
        """
        selected = self.twCw.selectedItems()
        if len(selected) == 0: return
        sel_item = selected[0]
        """
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

    def update_clue_column_settings(self):
        model = self.tvClues.model()
        header = self.tvClues.header()
        cols = []
        for i in range(header.count()):
            model_index = header.logicalIndex(i)
            header_item = model.horizontalHeaderItem(model_index)
            if header_item:
                cols.append({'name': header_item.text(), 
                            'visible': not header.isSectionHidden(model_index), 
                            'width': header.sectionSize(model_index)})
        if cols: CWSettings.settings['clues']['columns'] = cols

    def _logical_col_by_name(self, colname):
        model = self.tvClues.model()
        if not model: return -1
        header = self.tvClues.header()
        for i in range(header.count()):
            model_index = header.logicalIndex(i)
            if model.horizontalHeaderItem(model_index).text() == colname:
                return model_index
        return -1

    def _col_setting_by_logical_index(self, index):
        model = self.tvClues.model()
        if not model: return None
        colitem = model.horizontalHeaderItem(index)
        if not colitem: return None
        colname = colitem.text()
        for col in CWSettings.settings['clues']['columns']:
            if col['name'] == colname:
                return col
        return None

    def _word_from_clue_item(self, item: QtGui.QStandardItem):
        """
        Returns Word object from self.cw corresponding to the
        given clue item ('item').
        """
        if not self.cw or item.rowCount(): return None
        root_item = item.parent()
        if not root_item: return None
        try:
            col = self._logical_col_by_name('No')
            if col < 0: return None
            num = int(root_item.child(item.row(), col).text())
            wdir = 'h' if root_item.text() == 'Across' else 'v'
            return self.cw.words.find_by_num_dir(num, wdir)
        except Exception as err:
            print(err)
            return None

    def _clue_items_from_word(self, word: Word):
        """
        Returns items from a single row in the clues table corresponding
        to the given Word object ('word'). Items are returned
        as a dict: {'num': num, 'text': 'word string', 'clue': 'clue string'}.
        """
        datamodel = self.tvClues.model()
        if not datamodel or word is None: return None
        dirs = {'h': 'Across', 'v': 'Down'}
        items = datamodel.findItems(dirs[word.dir])
        if not len(items): return None
        root_item = items[0]
        col = self._logical_col_by_name('No')
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

    def update_clue_replies(self, coord):
        """
        Updates the 'reply' values in clues table for given grid coordinate 'coord'.
        """
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
    
    def select_clue(self):
        if self.tvClues.hasFocus(): return
        sel_model = self.tvClues.selectionModel()
        if not sel_model: return
        sel_model.clear()
        try:
            if not self.current_word:
                raise Exception('No current word')
            datamodel = self.tvClues.model()
            root_item = datamodel.item(0 if self.current_word.dir == 'h' else 1)
            if not root_item:
                raise Exception('No root item')
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
                    print(err)
                    continue
        except:
            return
                
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
        
    def reformat_cells(self):
        rows = self.twCw.rowCount()
        cols = self.twCw.columnCount()
        for r in range(rows):
            for c in range(cols):
                cell_item = self.twCw.item(r, c)
                if cell_item:
                    self.set_cell_formatting(cell_item)
        self.twCw.show()
    
    def update_cw_grid(self):
        if not self.cw: return
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
        
    def update_cw_params(self):
        if not self.cw: return
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

    def update_clues_model(self):
        delegate = self.tvClues.itemDelegate()
        if delegate:
            delegate.commitData.disconnect()
        self.tvClues.setModel(None)
        self.cluesmodel = QtGui.QStandardItemModel(0, 5)
        col_labels = [col['name'] for col in CWSettings.settings['clues']['columns']]
        self.cluesmodel.setHorizontalHeaderLabels(col_labels)
        if not self.cw: 
            self.tvClues.setModel(self.cluesmodel)
            self.tvClues.show()
            return
        root_items = {'Across': 'h', 'Down': 'v'}
        for k in sorted(root_items):
            root_item = QtGui.QStandardItem(QtGui.QIcon(f"{ICONFOLDER}/crossword.png"), k)
            for w in self.cw.words.words:
                if w.dir != root_items[k]: continue
                item_dir = QtGui.QStandardItem(QtGui.QIcon(), '')
                item_dir.setFlags(QtCore.Qt.ItemIsEnabled)
                item_num = QtGui.QStandardItem(str(w.num))
                item_num.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                item_clue = QtGui.QStandardItem(w.clue)
                item_clue.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                item_letters = QtGui.QStandardItem(str(len(w)))
                item_letters.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                item_reply = QtGui.QStandardItem(self.cw.words.get_word_str(w).upper())
                item_reply.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                items = {'Direction': item_dir, 'No': item_num, 'Clue': item_clue, 'Letters': item_letters, 'Reply': item_reply}
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

    def clues_show_hide_cols(self):
        header = self.tvClues.header()
        header.setDropIndicatorShown(True)
        for icol in range(header.count()):
            index = header.logicalIndex(icol)
            col_setting = self._col_setting_by_logical_index(index)
            if col_setting:
                header.setSectionHidden(index, not col_setting['visible'])

    def reformat_clues(self):
        """
        Sets formatting in clues table according to word status (filled / empty).
        """
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
                    col_name = colitem.text()
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
                
    def on_filter_word(self, word: str):
        return True

    def on_generate_start(self):
        self.update_actions()
            
    def on_generate_finish(self):
        self.update_cw_grid()

    @QtCore.pyqtSlot(float)
    def on_gen_timeout(self, timeout_):
        MsgBox(f"Timeout occurred at {timeout_} seconds!", self, 'Timeout', QtWidgets.QMessageBox.Warning)

    @QtCore.pyqtSlot()
    def on_gen_stop(self):
        MsgBox("Generation stopped!", self, 'Stopped', QtWidgets.QMessageBox.Warning)

    @QtCore.pyqtSlot(QtCore.QThread, str)
    def on_gen_error(self, thread, err):
        MsgBox(f"Generation failed with error:{NEWLINE}{err}", self, 'Error', QtWidgets.QMessageBox.Critical)

    @QtCore.pyqtSlot('PyQt_PyObject')
    def on_gen_validate(self, bad_):
        MsgBox(f"Generation finished!{NEWLINE}{'Check OK' if not bad_ else 'The following words failed validation: ' + repr(bad_)}", 
                self, 'Generation finished', QtWidgets.QMessageBox.Information if not bad_ else QtWidgets.QMessageBox.Warning)

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
                         onerror=lambda err_: self.gen_thread.sig_error.emit(err_),
                         onvalidate=lambda bad_: self.gen_thread.sig_validate.emit(bad_))

    def _guess_filetype(self, filepath):
        if not filepath: return -1
        ext = os.path.splitext(filepath)[1][1:].lower()
        if ext in ('xpf', 'ipuz'): return 0
        if ext == 'pdf': return 1
        if ext in ('jpg', 'png', 'tif', 'tiff', 'bmp'): return 2
        if ext == 'svg': return 3
        return 4

    def _get_filetype(self, filtername):
        try:
            return CWSAVE_FILTERS.index(filtername)
        except:
            pass
        return -1
        
    def save_cw(self, filepath=None, file_type=None):
        if filepath is None:
            filepath = self.cw_file
            
        if file_type is None:
            file_type = self._guess_filetype(filepath)
        else:
            if isinstance(file_type, str):
                file_type = self._get_filetype(file_type)
            elif not isinstance(file_type, int):
                file_type = -1

        if not filepath or file_type == -1: return False

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
                raise Exception(f"Error saving crossword to '{filepath}'")

            if (file_type == 2 or file_type == 3) and CWSettings.settings['export']['openfile']:
                Popen(f'cmd.exe /c "{filepath}"')    

            self.cw_file = filepath
            self.cw_modified = False
            self.update_actions()
            return True

        except Exception as err:
            MsgBox(str(err), self, 'Error', QtWidgets.QMessageBox.Critical)
            return False

    def export_cw(self, filepath, scale=1.0):
        """
        Exports crossword grid to image file.
        """
        # settings
        export_settings = CWSettings.settings['export']

        # save current words
        self.cw.words.save()

        # clear grid if needed
        if export_settings['clear_cw']:
            self.cw.words.clear()  
            self.update_cw_grid()

        # deselect words
        self.twCw.clearSelection()
        self.current_word = None
        self.reformat_cells()  
       
        # todo: add settings for size        
        scale_factor = export_settings['img_resolution'] / 25.4 * export_settings['mm_per_cell']
        cw_size = QtCore.QSize(self.twCw.columnCount() * scale_factor, self.twCw.rowCount() * scale_factor)
        
        try:
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
                    self._paint_cwgrid(painter, svg_generator.viewBoxF())
                    painter.end()
            
            elif ext in ('jpg', 'png', 'tif', 'tiff', 'bmp'):
                # image                     
                img = QtGui.QImage(cw_size, QtGui.QImage.Format_ARGB32)
                painter = QtGui.QPainter()
                if painter.begin(img):
                    self._paint_cwgrid(painter, QtCore.QRectF(img.rect()))
                    painter.end()    
                    img.save(filepath, quality=export_settings['img_output_quality'])  

        finally:
            # restore crossword words
            if export_settings['clear_cw']:
                self.cw.words.restore()
                self.update_cw_grid()
        
    def print_cw(self, pdf_file=None, show_preview=True):
        """
        Prints CW (and optionally clues) to file or printer.     
        """
        settings = CWSettings.settings['printing']
        # the 2 settings below may be changed in the preview dialog, so we'll store them
        print_cw = settings['print_cw']
        clear_cw = settings['clear_cw']

        # save current words
        self.cw.words.save()

        # clear grid if needed
        if print_cw and clear_cw:
            self.cw.words.clear()  
            self.update_cw_grid()

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

                if not dia_print.exec(): 
                    if print_cw and clear_cw:
                        self.cw.words.restore()
                        self.update_cw_grid()
                    return

                printer = dia_print.printer()

            else:
                printer.setResolution(CWSettings.settings['export']['pdf_resolution'])
                printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.A4))

            try:
                if show_preview:
                    dia_preview = PrintPreviewDialog(printer, self)
                    dia_preview.ppreview.paintRequested.connect(self.on_preview_paint)
                    if dia_preview.exec():
                        dia_preview.write_settings()
                        dia_preview.ppreview.print()  
                else:
                    self.on_preview_paint(printer)

                if settings['openfile'] and printer.outputFormat() == QtPrintSupport.QPrinter.PdfFormat:
                    pdf_file = printer.outputFileName()
                    if os.path.isfile(pdf_file):
                        Popen(f'cmd.exe /c "{pdf_file}"')
                    
            finally:            
                if print_cw and clear_cw:
                    # restore grid
                    self.cw.words.restore()
                    self.update_cw_grid()

        except Exception as err:            
            MsgBox(str(err), self, 'Error', QtWidgets.QMessageBox.Critical)
            traceback.print_exc(limit=None) 
            return

    def _apply_macros(self, txt, grid):
        txt = txt.replace('<t>', grid.info.title).replace('<a>', grid.info.author)
        txt = txt.replace('<p>', grid.info.publisher).replace('<c>', grid.info.cpyright)
        txt = txt.replace('<d>', grid.info.date)
        txt = txt.replace('<rows>', str(grid.height)).replace('<cols>', str(grid.width))
        return txt

    @QtCore.pyqtSlot(QtPrintSupport.QPrinter)
    def on_preview_paint(self, printer):
        """
        Prints CW (and optionally clues) to print preview form.
        This slot is connected to print preview dialog's paintRequested() signal.
        """     
        if not printer or self.twCw.rowCount() < 1 or self.twCw.columnCount() < 1: return
        painter = QtGui.QPainter()        
        if not painter.begin(printer):
            MsgBox('Printing error', self, 'Error', QtWidgets.QMessageBox.Critical)
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
                    txt = f"by {self.cw.words.info.author}"                
                    text_rect = font_metrics.boundingRect(txt)
                    painter.drawStaticText(page_rect.width() - text_rect.width(), top_offset, QtGui.QStaticText(txt))
                    top_offset += text_rect.height() + 40

                if self.cw.words.info.publisher:
                    txt = f"Published by {self.cw.words.info.publisher}"
                    text_rect = font_metrics.boundingRect(txt)
                    painter.drawStaticText(page_rect.width() - text_rect.width(), top_offset, QtGui.QStaticText(txt))
                    top_offset += text_rect.height() + 40

                if self.cw.words.info.cpyright:
                    txt = f"© {self.cw.words.info.cpyright}"
                    text_rect = font_metrics.boundingRect(txt)
                    painter.drawStaticText(page_rect.width() - text_rect.width(), top_offset, QtGui.QStaticText(txt))
                    top_offset += text_rect.height() + 40

                if self.cw.words.info.date:
                    txt = f"{self.cw.words.info.date}"
                    text_rect = font_metrics.boundingRect(txt)
                    painter.drawStaticText(page_rect.width() - text_rect.width(), top_offset, QtGui.QStaticText(txt))
                    top_offset += text_rect.height() + 40
            
            # cw    
            if settings['print_cw']:   
                painter.translate(paper_rect.topLeft())
                cw_rect = page_rect.adjusted(-margins.left(), top_offset - margins.top(), -margins.right(), -top_offset - margins.bottom())
                self._paint_cwgrid(painter, cw_rect)

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
                raise Exception('Cannot make new page!')
                
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
                        raise Exception('Cannot make new page!')                    
                    painter.translate(paper_rect.topLeft())
                    top_offset = 0

                painter.setPen(QtGui.QPen(QtGui.QColor.fromRgba(settings['clue_number_font']['color'])))
                painter.setFont(make_font(settings['clue_number_font']['font_name'], 
                    settings['clue_number_font']['font_size'], settings['clue_number_font']['font_weight'], 
                    settings['clue_number_font']['font_italic']))
                font_metrics = QtGui.QFontMetrics(painter.font())

                if wdir != word.dir:
                    txt = 'Across:' if word.dir == 'h' else 'Down:'   
                    row_height = font_metrics.boundingRect(txt).height()
                    top_offset += 200
                    if (top_offset + row_height) > (page_rect.height() - margins.bottom()):
                        if not printer.newPage():
                            raise Exception('Cannot make new page!')                    
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
                        raise Exception('Cannot make new page!')                    
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
                    txt = f"[{len(word)} letters]"                    
                    text_rect3 = painter.drawText(left_offset, top_offset, 
                        page_rect.width() - left_offset, 
                        page_rect.height() - top_offset - margins.bottom(), 
                        (QtCore.Qt.AlignLeft | QtCore.Qt.TextWordWrap), txt)
                
                row_height = max(text_rect1.height(), text_rect2.height(), text_rect3.height())
                top_offset += row_height + 50  
            
        except Exception as err:
            MsgBox(str(err), self, 'Error', QtWidgets.QMessageBox.Critical)
            traceback.print_exc(limit=None) 

        finally:
            painter.end()

    def _paint_cwgrid(self, painter, cliprect=None):
        """
        Paints cw grid by painter, constrained by cliprect (QRectF).
        """
        # calculate cell size
        if not cliprect: cliprect = painter.viewport()

        num_settings = CWSettings.settings['grid_style']['numbers']
        gridline_width = CWSettings.settings['grid_style']['line_width']

        cols = self.twCw.columnCount()
        rows = self.twCw.rowCount()
        cell_w = int((cliprect.width() + gridline_width) / cols + 2 * gridline_width)
        cell_h = int((cliprect.height() + gridline_width) / rows + 2 * gridline_width)
        cell_sz = min(cell_w, cell_h)

        v_offset = cliprect.top()
        for r in range(rows):
            h_offset = cliprect.left()
            for c in range(cols):                
                #item = self.twCw.item(r, c)
                coord = (c, r)
                ch = self.cw.words.get_char(coord)
                if ch == FILLER2:
                    h_offset += cell_sz - 2 * gridline_width
                    continue

                words = self.cw.words.find_by_coord(coord)
                w = words['h'] or words['v']

                dic_format = CWSettings.settings['cell_format']['NORMAL']
                if ch == FILLER:
                    dic_format = CWSettings.settings['cell_format']['FILLER']
                elif ch == BLANK:
                    dic_format = CWSettings.settings['cell_format']['BLANK']

                brush_cell = QtGui.QBrush(QtGui.QColor.fromRgba(dic_format['bg_color']), dic_format['bg_pattern'])
                brush_cell_border = QtGui.QBrush(QtGui.QColor.fromRgba(CWSettings.settings['grid_style']['line_color']))
                pen_cell = QtGui.QPen(brush_cell_border, gridline_width,
                                      CWSettings.settings['grid_style']['line'])
                font_cell = make_font(dic_format['font_name'], dic_format['font_size'],
                                      dic_format['font_weight'], dic_format['font_italic'])
                pen_cell_font = QtGui.QPen(QtGui.QColor.fromRgba(dic_format['fg_color']))

                # draw cell rect
                cell_rect = QtCore.QRectF(h_offset + gridline_width, v_offset + gridline_width, cell_sz - 2 * gridline_width, cell_sz - 2 * gridline_width)
                painter.setPen(pen_cell)
                painter.setBrush(brush_cell)
                painter.drawRect(cell_rect)

                # draw number
                if num_settings['show'] and not w is None:                    
                    pen_num_font = QtGui.QPen(QtGui.QColor.fromRgba(num_settings['color']))
                    font_num = make_font(num_settings['font_name'], num_settings['font_size'],
                                         num_settings['font_weight'], num_settings['font_italic'])
                    painter.setPen(pen_num_font)
                    painter.setFont(font_num)
                    painter.drawText(cell_rect.x(), cell_rect.y(), cell_rect.width() // 2, cell_rect.height() // 2,
                                    QtCore.Qt.AlignCenter, str(w.num))

                # draw text
                if ch != BLANK and ch != FILLER:
                    ch = ch.upper() if CWSettings.settings['grid_style']['char_case'] == 'upper' else ch.lower()
                    painter.setPen(pen_cell_font)
                    painter.setFont(font_cell)
                    painter.drawText(cell_rect.toRect(), dic_format['align'], ch)

                # increment h_offset
                h_offset += cell_sz - 2 * gridline_width

            # increment v_offset
            v_offset += cell_sz - 2 * gridline_width
    
    def update_settings_before_quit(self):
        # window size and pos
        CWSettings.settings['gui']['win_pos'] = (self.pos().x(), self.pos().y())
        CWSettings.settings['gui']['win_size'] = (self.width(), self.height())
        # clues column widths
        self.update_clue_column_settings()

    def get_word_suggestion(self, wordstr):        
        self.update_wordsrc()     
        if (self.cw is None) or (not bool(self.wordsrc)) or (self.current_word is None): return None   
        dia_suggest = WordSuggestDialog(self, wordstr, False, self.cw.suggest)
        if not dia_suggest.exec(): return None
        return dia_suggest.selected or None

    def adjust_clues_header_columns(self):
        # apply clues header col widths from settings
        header = self.tvClues.header()
        if header and not header.isHidden():
            for i in range(header.count()):
                if not self.tvClues.isColumnHidden(i):
                    width = CWSettings.settings['clues']['columns'][i]['width']
                    if width > 0:
                        self.tvClues.setColumnWidth(i, width) 

    def on_get_recent(self, new_version):
        if 'version' in new_version:
            self.statusbar_l2.setText(f"Update ready: v. {new_version['version']}")
        return True

    def on_before_update(self, curr_version, new_version):
        option = QtWidgets.QMessageBox.question(self, 'Confirm update',
                f"APPLICATION UPDATE AVAILABLE:{NEWLINE}"
                f"{new_version['description']}{NEWLINE}"
                f"Do you wish to update your current version {curr_version} "
                f"to version {new_version['version']}{NEWLINE}"
                f"(release date: {new_version['date']})?")
        return option == QtWidgets.QMessageBox.Yes

    def on_noupdate_available(self):
        MsgBox('No updates are available', self)
        
    # ----- Overrides (events, etc) ----- #
    
    def showEvent(self, event):    
        # show 
        event.accept()

        # update status bar
        self.statusbar_l1.setText(f"v. {APP_VERSION}")
        if CWSettings.settings['update']['auto_update']:
            self.on_act_update(False)
        else:
            self.updater.check_update()
        
    def closeEvent(self, event):
        # save cw
        self.autosave_cw()
        # save settings file
        self.update_settings_before_quit()
        sfile = os.path.abspath(SETTINGS_FILE)
        CWSettings.save_to_file(sfile)
        # close
        event.accept()

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
                        
    # ----- Slots ----- #
    
    @QtCore.pyqtSlot(QtCore.Qt.Orientation) 
    def on_toolbar_orientationChanged(self, orientation):
        print('TB re-oriented to {orientation}')
    
    @QtCore.pyqtSlot(bool)        
    def on_act_new(self, checked):
        if not hasattr(self, 'dia_load'):
            self.dia_load = LoadCwDialog()
        if not self.dia_load.exec(): return
        if self.cw: self.cw.closelog()
        selected_path = self.dia_load.le_pattern.text().lower()
        self.cw_file = ''
        
        if self.dia_load.rb_grid.isChecked():
            self.cw = Crossword(data=self.grid_from_file(selected_path), data_type='grid',
                                wordsource=self.wordsrc, wordfilter=self.on_filter_word, pos=CWSettings.settings['cw_settings']['pos'],
                                log=CWSettings.settings['cw_settings']['log'])
            self.cw_file = selected_path
        
        elif self.dia_load.rb_file.isChecked():
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
        
        self.update_cw()
        
        if self.dia_load.rb_empty.isChecked():
            self.act_edit.setChecked(True)
            
    @QtCore.pyqtSlot(bool)
    def on_act_open(self, checked):
        selected_path = QtWidgets.QFileDialog.getOpenFileName(self, 'Select file', os.getcwd(), 'Crossword files (*.xpf *.ipuz);;All files (*.*)')
        if not selected_path[0]: return
        selected_path = selected_path[0].replace('/', os.sep).lower()
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
    
    @QtCore.pyqtSlot(bool)
    def on_act_save(self, checked):
        if not self.cw or not self.cw_modified: return
        if not self.cw_file:
            self.on_act_saveas(False)
        else:
            self.save_cw()   

    @QtCore.pyqtSlot(bool)
    def on_act_saveas(self, checked):
        if not self.cw: return
        
        fname = 'crossword.xpf'
        selected_path = QtWidgets.QFileDialog.getSaveFileName(self, 'Select file', os.path.join(os.getcwd(), fname), 
            ';;'.join(CWSAVE_FILTERS), CWSAVE_FILTERS[0])
        if not selected_path[0]: return
        self.save_cw(selected_path[0].replace('/', os.sep).lower(), selected_path[1])

    @QtCore.pyqtSlot(bool)
    def on_act_share(self, checked):
        """
        Share CW in social networks.
        """
        MsgBox('on_act_share', self)

    @QtCore.pyqtSlot(bool)
    def on_act_exit(self, checked):
        self.close()

    @QtCore.pyqtSlot(bool)
    def on_act_addrow(self, checked):
        if not self.cw or not self.act_edit.isChecked(): return 
        if self.twCw.currentRow() >= 0:
            self.cw.words.add_row(self.twCw.currentRow())
            self.update_cw()

    @QtCore.pyqtSlot(bool)
    def on_act_addcol(self, checked):
        if not self.cw or not self.act_edit.isChecked(): return 
        if self.twCw.currentColumn() >= 0:
            self.cw.words.add_column(self.twCw.currentColumn())
            self.update_cw()

    @QtCore.pyqtSlot(bool)
    def on_act_delrow(self, checked):
        if not self.cw or not self.act_edit.isChecked(): return 
        if self.twCw.currentRow() >= 0:
            self.cw.words.remove_row(self.twCw.currentRow())
            self.update_cw()

    @QtCore.pyqtSlot(bool)
    def on_act_delcol(self, checked):
        if not self.cw or not self.act_edit.isChecked(): return 
        if self.twCw.currentColumn() >= 0:
            self.cw.words.remove_column(self.twCw.currentColumn())
            self.update_cw()

    @QtCore.pyqtSlot(bool)
    def on_act_reflect(self, checked):
        if not self.cw or not self.act_edit.isChecked(): return 
        if not hasattr(self, 'dia_reflect'):
            self.dia_reflect = ReflectGridDialog()
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

    @QtCore.pyqtSlot(bool)
    def on_act_clear_wd(self, checked):
        if not self.cw or not self.current_word or self.cw.words.is_word_blank(self.current_word):
            return
        self.cw.clear_word(self.current_word, False)
        self.update_cw_grid()

    @QtCore.pyqtSlot(bool)
    def on_act_erase_wd(self, checked):
        if not self.cw or not self.current_word or self.cw.words.is_word_blank(self.current_word):
            return
        self.cw.clear_word(self.current_word, True)
        self.update_cw_grid()
    
    @QtCore.pyqtSlot(bool)        
    def on_act_gen(self, checked):
        if not self.cw: return     
        if not hasattr(self, 'gen_thread') or self.gen_thread is None:
            self.gen_thread = GenThread(on_gen_timeout=self.on_gen_timeout, on_gen_stopped=self.on_gen_stop, 
                                    on_gen_validate=self.on_gen_validate,
                                    on_start=self.on_generate_start, on_finish=self.on_generate_finish,
                                    on_run=self.generate_cw_worker, on_error=self.on_gen_error) 
        self.gen_thread.start()
        self.update_actions()
        
    @QtCore.pyqtSlot(bool)        
    def on_act_stop(self, checked):
        if not (checked and self.cw and self.gen_thread.isRunning() and self.gen_thread.isRunning()): return      
        self.gen_thread.requestInterruption()
        self.update_actions()
    
    @QtCore.pyqtSlot(bool)        
    def on_act_edit(self, checked):
        self.reformat_cells()
        self.update_actions()

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

    @QtCore.pyqtSlot(bool)        
    def on_act_editclue(self, checked):
        clue = self._clue_items_from_word(self.current_word)
        if not clue: return
        index = clue['clue'].index()
        if not self.tvClues.isIndexHidden(index):
            self.tvClues.setFocus()
            self.tvClues.edit(index)
    
    @QtCore.pyqtSlot(bool)        
    def on_act_clear(self, checked):
        if not self.cw: return
        self.cw.clear()
        self.update_cw_grid()

    @QtCore.pyqtSlot(bool)        
    def on_act_suggest(self, checked):
        if not self.cw: return
        wordstr = self.cw.words.get_word_str(self.current_word)
        sug = self.get_word_suggestion(wordstr)
        if not sug or sug.lower() == wordstr.lower(): return
        #print(f"Changing '{wordstr}' for '{sug}'...")
        self.cw.change_word(self.current_word, sug)
        self.update_cw_grid()

    @QtCore.pyqtSlot(bool)
    def on_act_lookup(self, checked):
        if not self.cw: return
                    
        if CWSettings.settings['lookup']['dics']['show'] or CWSettings.settings['lookup']['google']['show']:
            wordstr = self.cw.words.get_word_str(self.current_word)
            if not hasattr(self, 'dia_lookup'):
                self.dia_lookup = DefLookupDialog(wordstr)
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
            MsgBox('No lookup sources are active! Please go to Settings (F11) to verify your lookup source configuration.', 
                   self, 'No Lookup Sources', QtWidgets.QMessageBox.Warning)
        
    @QtCore.pyqtSlot(bool) 
    def on_act_wsrc(self, checked):
        if not hasattr(self, 'dia_settings'):
            self.dia_settings = SettingsDialog(self)
        self.dia_settings.tree.setCurrentItem(self.dia_settings.tree.topLevelItem(1).child(0))
        self.on_act_config(False)
    
    @QtCore.pyqtSlot(bool)        
    def on_act_info(self, checked):
        if not self.cw: return
        dia_info = CwInfoDialog(self)
        if dia_info.exec():
            self.cw.words.info = dia_info.to_info()
        
    @QtCore.pyqtSlot(bool)        
    def on_act_print(self, checked):
        """
        Prints current CW and/or clues to printer or PDF.
        """
        if not self.cw: return
        self.print_cw()
    
    @QtCore.pyqtSlot(bool)        
    def on_act_config(self, checked):
        if not hasattr(self, 'dia_settings'):
            self.dia_settings = SettingsDialog(self)
        if not self.dia_settings.exec(): return
        settings = self.dia_settings.to_settings()
        # apply settings only if they are different from current
        if json.dumps(settings, sort_keys=True) != json.dumps(CWSettings.settings, sort_keys=True):
            #print(json.dumps(CWSettings.settings, sort_keys=True))
            #print(json.dumps(settings, sort_keys=True))
            CWSettings.settings = settings
            self.apply_config()

    @QtCore.pyqtSlot(bool)        
    def on_act_update(self, checked):
        self.updater.update(True)
   
    @QtCore.pyqtSlot(bool)        
    def on_act_help(self, checked):
        MsgBox('on_act_help', self)

    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def on_statusbar_l2_dblclicked(self, event):
        if not self.statusbar_l2.text(): return
        self.on_act_update(False)
        
    @QtCore.pyqtSlot(int)
    def on_slider_cw_scale(self, value):
        self.scale_cw(value)        
        
    @QtCore.pyqtSlot(QtWidgets.QTableWidgetItem, QtWidgets.QTableWidgetItem)
    def on_cw_current_item_changed(self, current, previous):
        """
        When a new grid cell item is focused.
        """        
        self.update_current_word('flip' if self.last_pressed_item==current else 'current')            
        self.reformat_cells()
        self.last_pressed_item = current
        
    @QtCore.pyqtSlot(QtWidgets.QTableWidgetItem)
    def on_cw_item_clicked(self, item):
        """
        When a new grid cell item is clicked (pressed).
        """
        if self.twCw.currentItem() == item:
            self.update_current_word('flip' if self.last_pressed_item==item else 'current')            
            self.reformat_cells()
            self.last_pressed_item = item

    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_twCw_contextmenu(self, point):
        if not self.current_word: return
        cell_item = self.twCw.itemAt(point)
        if not cell_item: return
        self.menu_crossword.update_actions()
        self.menu_crossword.exec(self.twCw.mapToGlobal(point))
    
    @QtCore.pyqtSlot(QtWidgets.QAction)
    def on_menu_crossword(self, action):
        if not action.isEnabled(): return        
        if action == self.menu_crossword.act_cm_new:
            self.on_act_new(False)        
        elif action == self.menu_crossword.act_cm_open:
            self.on_act_open(False)          
        elif action == self.menu_crossword.act_cm_save:
            self.on_act_save(False) 
        elif action == self.menu_crossword.act_cm_saveas:
            self.on_act_saveas(False) 
        elif action == self.menu_crossword.act_cm_gen:
            self.on_act_gen(False) 
        elif action == self.menu_crossword.act_cm_stop:
            self.act_stop.setChecked(True)
            self.on_act_stop(True) 
        elif action == self.menu_crossword.act_cm_clear:
            self.on_act_clear(False)
        elif action == self.menu_crossword.act_cm_clear_wd and self.current_word:
            self.on_act_clear_wd(False)
        elif action == self.menu_crossword.act_cm_erase_wd and self.current_word:
            self.on_act_erase_wd(False)
        elif action == self.menu_crossword.act_cm_suggest and self.current_word:
            self.on_act_suggest(False)
        elif action == self.menu_crossword.act_cm_gotoclue and self.current_word:
            self.on_act_editclue(False)
        elif action == self.menu_crossword.act_cm_info:
            self.on_act_info(False)
        elif action == self.menu_crossword.act_cm_print:
            self.on_act_print(False)

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

    @QtCore.pyqtSlot(int, int, int)
    def on_tvClues_column_moved(self, logicalIndex, oldVisualIndex, newVisualIndex):
        """
        Fires when the clues table columns have been moved by dragging.
        """
        # save new column order to global settings
        self.update_clue_column_settings()

    @QtCore.pyqtSlot('QWidget*')
    def on_clues_editor_commit(self, editor):     
        """
        Fires every time a cell in clues table has been edited (manually) and
        is about to write data back to model. We implement this slot
        to validate the entered text, update the CW grid and the clues table.
        """   
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
                print(err)

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

        
