# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package pycross.forms
# Classes for all the GUI app's forms but the main window.
from PyQt5 import (QtGui, QtCore, QtWidgets, QtPrintSupport, 
                    QtWebEngineWidgets, QtWebEngineCore, QtWebEngine)
import os, copy, json
import numpy as np
from distutils import version

from utils.globalvars import *
from utils.utils import *
from utils.onlineservices import MWDict, YandexDict, GoogleSearch, Share
from crossword import BLANK, CWInfo
from guisettings import CWSettings

# ******************************************************************************** #
# *****          BrowseEdit
# ******************************************************************************** # 

## @brief Edit field with internal 'Browse' button to file or folder browsing.
# Inherited from `QtWidgets.QLineEdit`
class BrowseEdit(QtWidgets.QLineEdit):

    ## Constructor.
    # @param text `str` initial text in edit field (default = empty)
    # @param dialogtype `str` path and dialog type: 
    #   * 'fileopen' = open file browse dialog
    #   * 'filesave' = save file browse dialog
    #   * 'folder' = folder browse dialog
    # `None` = 'fileopen' (default)
    # @param btnicon `str` icon file name in 'assets/icons'
    # `None` = 'folder-2.png' (default)
    # @param btnposition `int` browse button position:
    #   * 0 (`QtWidgets.QLineEdit.LeadingPosition`) = left-aligned
    #   * 1 (`QtWidgets.QLineEdit.TrailingPosition`) = right-aligned
    # `None` = `QtWidgets.QLineEdit.TrailingPosition` (default)
    # @param opendialogtitle `str` dialog title (`None` will use a default title)
    # @param filefilters `str` file filters for file browse dialog, e.g.
    # `"Images (*.png *.xpm *.jpg);;Text files (*.txt);;XML files (*.xml)"`\n
    # `None` sets the default filter: `"All files (*.*)"`
    def __init__(self, text='', parent=None,
                dialogtype=None, btnicon=None, btnposition=None,
                opendialogtitle=None, filefilters=None, fullpath=True):
        super().__init__(text, parent)
        ## `str` path and dialog type ('file' or 'folder')
        self.dialogtype = dialogtype or 'fileopen'      
        ## `str` icon file name in 'assets/icons'
        self.btnicon = btnicon or 'folder-2.png'
        ## `int` browse button position (0 or 1)
        self.btnposition = btnposition or QtWidgets.QLineEdit.TrailingPosition
        ## `str` dialog title
        self.opendialogtitle = opendialogtitle or \
            (_('Select file') if self.dialogtype.startswith('file') else _('Select folder'))        
        ## `str` file filters for file browse dialog
        self.filefilters = filefilters or _('All files (*.*)')
        self.fullpath = fullpath
        self.delegate = None
        self.reset_action()

    ## Gets the start directory for the browse dialog.
    def _get_dir(self, text=None):
        if text is None: text = self.text()
        if text and not (os.path.isfile(text) or os.path.isdir(text)):
            text = os.path.join(os.getcwd(), text)
        if os.path.isfile(text) or os.path.isdir(text):
            return text #os.path.dirname(text)    
        else: 
            return os.getcwd()

    ## Clears previous actions from the underlying object.
    def _clear_actions(self):
        for act_ in self.actions():
            self.removeAction(act_)

    ## Resets the browse action (after setting options).
    def reset_action(self):
        self._clear_actions()
        self.btnaction = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/{self.btnicon}"), '')
        self.btnaction.setToolTip(self.opendialogtitle)
        self.btnaction.triggered.connect(self.on_btnaction)
        self.addAction(self.btnaction, self.btnposition)
        #self.show()

    ## Triggered slot for the browse action: opens dialog and sets the edit text.
    @QtCore.pyqtSlot()
    def on_btnaction(self):
        if self.delegate: self.delegate.blockSignals(True)
        opendialogdir = self._get_dir()
        if self.dialogtype == 'fileopen':
            selected_path = QtWidgets.QFileDialog.getOpenFileName(self.window(), self.opendialogtitle, opendialogdir, self.filefilters)
            selected_path = selected_path[0]
        elif self.dialogtype == 'filesave':
            selected_path = QtWidgets.QFileDialog.getSaveFileName(self.window(), self.opendialogtitle, opendialogdir, self.filefilters)
            selected_path = selected_path[0]
        elif self.dialogtype == 'folder':
            selected_path = QtWidgets.QFileDialog.getExistingDirectory(self.window(), self.opendialogtitle, opendialogdir)
        else:
            if self.delegate: self.delegate.blockSignals(False)
            return
        if not selected_path: 
            if self.delegate: self.delegate.blockSignals(False)
            return
        selected_path = selected_path.replace('/', os.sep)
        if not self.fullpath:
            selected_path = os.path.basename(selected_path)
        self.setText(selected_path)
        if self.delegate: self.delegate.blockSignals(False)

# ******************************************************************************** #
# *****          BrowseEditDelegate
# ******************************************************************************** #        

## Delegate class for table and tree-like widgets implementing an edit field with the browse button.
# @see BrowseEdit
class BrowseEditDelegate(QtWidgets.QStyledItemDelegate):

    ## Constructor.
    # @param model_indices `list` list of indices in underlying model that must contain the 
    # BrowseEdit fields
    # @param thisparent `QtWidgets.QWidget` parent widget for this instance
    # @param browse_edit_kwargs `keyword arguments` keyword arguments passed to BrowseEdit constructor
    def __init__(self, model_indices=None, thisparent=None, 
                **browse_edit_kwargs):
        super().__init__(thisparent)
        self.model_indices = model_indices
        self.browse_edit_kwargs = browse_edit_kwargs

    ## Overridden method of QtWidgets.QStyledItemDelegate:
    # creates the underlying delegate (editor widget).
    def createEditor(self, parent: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem,
                    index: QtCore.QModelIndex) -> QtWidgets.QWidget:
        try:
            if self.model_indices and index in self.model_indices:
                self.browse_edit_kwargs['parent'] = parent
                editor = BrowseEdit(**self.browse_edit_kwargs)
                editor.setFrame(False)
                editor.delegate = self
                return editor
            else:
                return super().createEditor(parent, option, index)
        except Exception as err:
            print(err)
            return None

    ## Overridden method of QtWidgets.QStyledItemDelegate:
    # updates the editor data (text) from the underlying model.
    def setEditorData(self, editor, index: QtCore.QModelIndex):
        if not index.isValid(): return
        if self.model_indices and index in self.model_indices:
            txt = index.model().data(index, QtCore.Qt.EditRole)
            if isinstance(txt, str):
                editor.setText(txt)
        else:
            super().setEditorData(editor, index)

    ## Overridden method of QtWidgets.QStyledItemDelegate:
    # updates the underlying model from the editor data (text).
    def setModelData(self, editor, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex):
        if self.model_indices and index in self.model_indices:
            model.setData(index, editor.text(), QtCore.Qt.EditRole)
        else:
            super().setModelData(editor, model, index)

    ## Overridden method of QtWidgets.QStyledItemDelegate:
    # updates the editor position and size for a given model index.
    def updateEditorGeometry(self, editor, option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex):
        editor.setGeometry(option.rect)        

# ******************************************************************************** #
# *****          BasicDialog
# ******************************************************************************** #

## @brief Base class for OK-Cancel type dialogs.
# Creates the basic layout for controls (leaving the central area free to add controls),
# and declares the validate() method to validate correctness of user input before accepting.
class BasicDialog(QtWidgets.QDialog):
    
    ## Constructor.
    # @param geometry `4-tuple` window geometry data: `(left, top, width, height)`.
    # If set to `None` (default), the position will be centered on the parent widget or screen
    # and the size will be automatically adjusted to fit the internal controls.
    # @param title `str` window title (`None` for no title)
    # @param icon `str` window icon file name (relative to utils::globalvars::ICONFOLDER), e.g. 'main.png'.
    # `None` means no icon.
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    # @param sizepolicy `QtWidgets.QSizePolicy` [QWidget size policy](https://doc.qt.io/qt-5/qsizepolicy.html).
    # Default is fixed size in both directions (non-resizable dialog).
    def __init__(self, geometry=None, title=None, icon=None, parent=None, 
                 flags=QtCore.Qt.WindowFlags(), 
                 sizepolicy=QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)):
        super().__init__(parent, flags)
        self.initUI(geometry, title, icon)
        self.setSizePolicy(sizepolicy)
        
    ## @brief Creates the main (central) layout for controls.
    # Must be overridden by child classes to change the layout type
    # (default = `QtWidgets.QFormLayout`) and add controls.
    def addMainLayout(self):
        ## `QtWidgets.QFormLayout` central layout for controls
        self.layout_controls = QtWidgets.QFormLayout()
        
    ## Creates the core controls: OK and Cancel buttons and layouts.
    # @param geometry `4-tuple` window geometry data: `(left, top, width, height)`.
    # If set to `None` (default), the position will be centered on the parent widget or screen
    # and the size will be automatically adjusted to fit the internal controls.
    # @param title `str` window title (`None` for no title)
    # @param icon `str` window icon file name (relative to utils::globalvars::ICONFOLDER), e.g. 'main.png'.
    # `None` means no icon.
    def initUI(self, geometry=None, title=None, icon=None):
        
        self.addMainLayout()
        
        ## `QtWidgets.QPushButton` OK button
        self.btn_OK = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/like.png"), _('OK'), None)
        self.btn_OK.setMaximumWidth(150)
        self.btn_OK.setDefault(True)
        self.btn_OK.clicked.connect(self.on_btn_OK_clicked)
        ## `QtWidgets.QPushButton` Cancel button
        self.btn_cancel = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/multiply-1.png"), _('Cancel'), None)
        self.btn_cancel.setMaximumWidth(150)
        self.btn_cancel.clicked.connect(self.on_btn_cancel_clicked)
        
        ## `QtWidgets.QHBoxLayout` bottom layout for OK and Cancel buttons
        self.layout_bottom = QtWidgets.QHBoxLayout()
        self.layout_bottom.setSpacing(10)
        self.layout_bottom.addWidget(self.btn_OK)
        self.layout_bottom.addWidget(self.btn_cancel)          
        
        ## `QtWidgets.QVBoxLayout` window layout
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.addLayout(self.layout_controls)
        self.layout_main.addLayout(self.layout_bottom)
        
        self.setLayout(self.layout_main)
        if geometry:
            self.setGeometry(*geometry) 
        else:
            self.adjustSize()
        if title:
            self.setWindowTitle(title)      
        if icon:
            self.setWindowIcon(QtGui.QIcon(f"{ICONFOLDER}/{icon}"))
        
    ## Validates user input (reimplemented in child classes).
    # @returns `bool` `True` if user input is valid, `False` otherwise
    # @see on_btn_OK_clicked()
    def validate(self):        
        return True
    
    ## @brief Fires when the OK button is clicked.
    # Calls validate() to check correctness of input and, if correct, 
    # accepts and closes window.
    @QtCore.pyqtSlot()
    def on_btn_OK_clicked(self): 
        if self.validate(): self.accept()
        
    ## Fires when the Cancel button is clicked: rejects input and closes window.
    @QtCore.pyqtSlot()
    def on_btn_cancel_clicked(self): 
        self.reject() 
        
# ******************************************************************************** #
# *****          LoadCwDialog
# ******************************************************************************** #  
        
## Crossword creation dialog providing options to populate the crossword grid.
class LoadCwDialog(BasicDialog):
        
    ## Constructor.
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, parent=None, flags=QtCore.Qt.WindowFlags()):
        super().__init__(None, _('New crossword'), 'crossword.png', 
              parent, flags)
        
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout()
        
        ## `QtWidgets.QRadioButton` 'load from pattern file' option
        self.rb_grid = QtWidgets.QRadioButton(_('Pattern'))
        self.rb_grid.setToolTip(_('Load pattern preset'))
        self.rb_grid.toggle()
        self.rb_grid.toggled.connect(self.rb_toggled)
        ## `QtWidgets.QRadioButton` 'load from file' option
        self.rb_file = QtWidgets.QRadioButton(_('File'))
        self.rb_file.setToolTip(_('Import crossword from file'))
        self.rb_file.toggled.connect(self.rb_toggled)
        ## `QtWidgets.QRadioButton` 'empty grid' option
        self.rb_empty = QtWidgets.QRadioButton(_('Empty grid'))
        self.rb_empty.setToolTip(_('Set grid dimensions and edit manually'))
        self.rb_empty.toggled.connect(self.rb_toggled)
        
        self.gb_pattern = QtWidgets.QGroupBox(_('Pattern file'))
        self.le_pattern = BrowseEdit()        
        self.le_pattern.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.layout_pattern = QtWidgets.QHBoxLayout()
        self.layout_pattern.addWidget(self.le_pattern)
        self.gb_pattern.setLayout(self.layout_pattern)
        
        self.gb_file = QtWidgets.QGroupBox(_('Crossword file'))
        self.le_file = BrowseEdit(filefilters=_('Crossword files (*.xpf *.xml *.puz *.ipuz);;All files (*.*)'))
        self.le_file.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.layout_file = QtWidgets.QHBoxLayout()
        self.layout_file.addWidget(self.le_file)
        self.gb_file.setLayout(self.layout_file)
        self.gb_file.setVisible(False)
        
        self.gb_manual = QtWidgets.QGroupBox(_('Grid dimensions'))
        self.le_rows = QtWidgets.QLineEdit('15')
        self.le_cols = QtWidgets.QLineEdit('15')
        self.combo_pattern = QtWidgets.QComboBox()
        for i in range(1, 5):
            icon = QtGui.QIcon(f"{ICONFOLDER}/grid{i}.png")
            self.combo_pattern.addItem(icon, _("Pattern {}").format(i))
        self.layout_manual = QtWidgets.QFormLayout()
        self.layout_manual.addRow(_('Rows:'), self.le_rows)
        self.layout_manual.addRow(_('Columns:'), self.le_cols)
        self.layout_manual.addRow(_('Pattern:'), self.combo_pattern)
        self.gb_manual.setLayout(self.layout_manual)
        self.gb_manual.setVisible(False)
        
        self.layout_controls.addWidget(self.rb_grid)
        self.layout_controls.addWidget(self.gb_pattern)
        self.layout_controls.addWidget(self.rb_file)
        self.layout_controls.addWidget(self.gb_file)
        self.layout_controls.addWidget(self.rb_empty)
        self.layout_controls.addWidget(self.gb_manual)
        #self.layout_controls.addStretch()

        self.setMinimumWidth(300)
        
    ## Checks that the text / pattern file is valid (if selected) or that the number of 
    # rows and columns is valid (if creating an empty cw grid).
    def validate(self):
        if self.rb_grid.isChecked() and not os.path.isfile(self.le_pattern.text()):
            MsgBox(_('Pattern file is unavailable, please check!'), self, _('Error'), 'error')
            return False
        if self.rb_file.isChecked() and not os.path.isfile(self.le_file.text()):
            MsgBox(_('Crossword file is unavailable, please check!'), self, _('Error'), 'error')
            return False 
        try:
            int(self.le_rows.text())
            int(self.le_cols.text())
        except ValueError:
            MsgBox(_('Rows and columns must be valid numbers (e.g. 10)!'), self, _('Error'), 'error')
            return False
        return True
        
    # ----- Slots ----- #
    
    ## Show / hide panels under radio buttons.
    @QtCore.pyqtSlot(bool)        
    def rb_toggled(self, toggled):
        self.gb_pattern.setVisible(self.rb_grid.isChecked())
        self.gb_file.setVisible(self.rb_file.isChecked())
        self.gb_manual.setVisible(self.rb_empty.isChecked())
        self.adjustSize()
            
# ******************************************************************************** #
# *****          WordSrcDialog
# ******************************************************************************** #  

## @brief Word source editor dialog: provides adding and editing word sources.
# The word sources are then combined in gui::MainWindow::wordsrc in their sequential order
# (as they are shown in the Settings dialog) to use for crossword generation.
#
# Currently 3 types of word sources are supported:
#   * SQLite database
#   * text file (with words and their parts of speech occupying one row each)
#   * in-memory list of words (optionally with part of speech data)
# 
# See @ref pycross.wordsrc for implementation of word source objects.
class WordSrcDialog(BasicDialog):
    ## Constructor.
    # @param src `dict` serialized word source data in the following format:
    # @code
    # src = {'active': True|False, 'name': '<name>', 'type': 'db|file|list', 'file': '<path>', 
    # 'dbtype': '<sqlite>', 'dblogin': '', 'dbpass': '', 'dbtables': SQL_TABLES, 
    # 'haspos': True|False, 'encoding': 'utf-8', 'shuffle': True|False, 
    # 'delim': ' ', 'words': []}
    # @endcode
    # Description of keys:
    #   * 'active' `bool` whether this source will be used in crossword generation
    #   * 'name' `str` unique name for this source, e.g. 'eng-db' or 'rus-text-1'
    #   * 'type' `str` any of the three source types:
    #       - 'db' SQLite database
    #       - 'file' text file
    #       - 'list' in-memory list of words
    #   * 'file' `str` full path to the DB or text file;
    # if 'type' == 'db', abbreviated paths can be used to point to the preinstalled DB files,
    # e.g. 'ru' = 'assets/dic/ru.db'
    #   * 'dbtype' `str` currently must be only 'sqlite' (no other DB types are supported)
    #   * 'dblogin' `str` optional DB user name
    #   * 'dbpass' `str` optional DB user password
    #   * 'dbtables' `dict` SQLite DB table and field names as given in utils::globalvars::SQL_TABLES
    #   * 'haspos' `bool` `True` to indicate that the text file or word list contains part of speech data
    # (appended to word strings after a delimiter character)
    #   * 'encoding' `str` text file encoding (default = 'utf-8')
    #   * 'shuffle' `bool` whether to shuffle the words in the source randomly when used for word suggestions
    #   * 'delim' `str` delimiter character used to delimit word strings and part of speech data
    # (default = whitespace)
    #   * 'words' `list` list of words (optionally with part of speech data) -- see wordsrc::TextWordsource::words
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, src=None, parent=None, flags=QtCore.Qt.WindowFlags()):
        ## `dict` serialized word source data (see \_\_init\_\_())
        self.src = src
        super().__init__(None, _('Word Source'), 'database-3.png', 
              parent, flags)
        if self.src: self.from_src(self.src)
                
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout()     
        
        self.gb_name = QtWidgets.QGroupBox(_('Name'))
        self.gb_name.setFlat(True)
        self.layout_gb_name = QtWidgets.QVBoxLayout() 
        self.le_name = QtWidgets.QLineEdit('')
        self.le_name.setStyleSheet('font-weight: bold;')
        self.layout_gb_name.addWidget(self.le_name)
        self.gb_name.setLayout(self.layout_gb_name)
        
        self.gb_type = QtWidgets.QGroupBox(_('Source type')) 
        self.layout_gb_type = QtWidgets.QHBoxLayout() 
        self.rb_type_db = QtWidgets.QRadioButton(_('Database'))
        self.rb_type_db.toggled.connect(self.rb_toggled)
        self.rb_type_file = QtWidgets.QRadioButton(_('File'))
        self.rb_type_file.toggled.connect(self.rb_toggled)
        self.rb_type_list = QtWidgets.QRadioButton(_('Simple list'))
        self.rb_type_list.toggled.connect(self.rb_toggled)
        self.layout_gb_type.addWidget(self.rb_type_db)
        self.layout_gb_type.addWidget(self.rb_type_file)
        self.layout_gb_type.addWidget(self.rb_type_list)  
        
        self.gb_type.setLayout(self.layout_gb_type)
        
        self.stacked = QtWidgets.QStackedWidget() 
        self.add_pages()
        self.rb_type_db.setChecked(True)
        self.stacked.setCurrentIndex(0)
        
        self.layout_controls.addWidget(self.gb_name)
        self.layout_controls.addWidget(self.gb_type)
        self.layout_controls.addWidget(self.stacked)
        
    ## Creates tabs for the 3 source types.
    def add_pages(self):
        # 1. DB
        self.page_db = QtWidgets.QWidget()
        self.layout_db = QtWidgets.QFormLayout()
        self.le_dbfile = BrowseEdit(filefilters=_('SQLite database files (*.db)'))
        self.combo_dbtype = QtWidgets.QComboBox()
        self.combo_dbtype.addItems(['SQLite'])
        self.combo_dbtype.setEditable(False)
        self.combo_dbtype.setCurrentIndex(0)
        self.le_dbuser = QtWidgets.QLineEdit('')
        self.le_dbpass = QtWidgets.QLineEdit('')
        self.te_dbtables = QtWidgets.QTextEdit('')
        font = make_font('Courier', 10)
        font_metrics = QtGui.QFontMetrics(font)
        self.te_dbtables.setFont(font)
        style = color_to_stylesheet(QtGui.QColor('#f2f2f2'), self.te_dbtables.styleSheet())
        self.te_dbtables.setStyleSheet(style)
        self.te_dbtables.setMinimumHeight(80)        
        self.te_dbtables.setTabStopDistance(font_metrics.horizontalAdvance('    '))
        self.te_dbtables.setAcceptRichText(False)
        self.te_dbtables.setPlaceholderText(_('Database table and field names'))
        self.te_dbtables_hiliter = JsonHiliter(self.te_dbtables.document(), True, 
            self.on_decode_error, self.on_decode_success)
        self.te_te_dbtables_error = QtWidgets.QPlainTextEdit('')
        self.te_te_dbtables_error.setMaximumHeight(80)
        self.te_te_dbtables_error.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.te_te_dbtables_error.setFont(font)
        self.te_te_dbtables_error.setReadOnly(True)
        style = color_to_stylesheet(QtGui.QColor('#262626'), self.te_te_dbtables_error.styleSheet())
        style = color_to_stylesheet(QtGui.QColor(QtCore.Qt.yellow), style, 'color')
        self.te_te_dbtables_error.setStyleSheet(style)
        self.te_te_dbtables_error.hide()
        self.layout_dbtables = QtWidgets.QVBoxLayout()
        self.layout_dbtables.addWidget(self.te_dbtables)
        self.layout_dbtables.addWidget(self.te_te_dbtables_error)
        self.te_dbtables.setPlainText(json.dumps(SQL_TABLES, indent=4))
        self.chb_db_shuffle = QtWidgets.QCheckBox()
        self.chb_db_shuffle.setChecked(True)
        self.btn_dbedit = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/edit.png"), _('Edit'), None)
        self.btn_dbedit.setToolTip(_('Edit database in external editor'))
        self.btn_dbedit.setEnabled(CWSettings.settings['plugins']['thirdparty']['dbbrowser']['active'] and os.path.isfile(CWSettings.settings['plugins']['thirdparty']['dbbrowser']['exepath']))
        self.btn_dbedit.clicked.connect(self.on_btn_dbedit)
        self.layout_db.addRow(_('Path'), self.le_dbfile)
        self.layout_db.addRow(_('Type'), self.combo_dbtype)
        self.layout_db.addRow(_('User'), self.le_dbuser)
        self.layout_db.addRow(_('Password'), self.le_dbpass)
        self.layout_db.addRow(_('Tables'), self.layout_dbtables)
        self.layout_db.addRow(_('Shuffle'), self.chb_db_shuffle)
        self.layout_db.addRow(self.btn_dbedit)
        self.page_db.setLayout(self.layout_db)
        self.stacked.addWidget(self.page_db)
        
        # 2. File
        self.page_file = QtWidgets.QWidget()
        self.layout_file = QtWidgets.QFormLayout()
        self.le_txtfile = BrowseEdit()
        self.combo_fileenc = QtWidgets.QComboBox()
        self.combo_fileenc.addItems(ENCODINGS)
        self.combo_fileenc.setEditable(False)
        self.combo_fileenc.setCurrentText('utf_8')
        self.combo_file_delim = QtWidgets.QComboBox()
        self.combo_file_delim.addItems([_('SPACE'), _('TAB'), ';', ',', ':'])
        self.combo_file_delim.setEditable(True)
        self.combo_file_delim.setCurrentIndex(0)
        self.chb_file_shuffle = QtWidgets.QCheckBox()
        self.chb_file_shuffle.setChecked(True)
        self.btn_fileedit = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/edit.png"), _('Edit'), None)
        self.btn_fileedit.setToolTip(_('Edit text file in external editor'))
        self.btn_fileedit.setEnabled(CWSettings.settings['plugins']['thirdparty']['text']['active'] and os.path.isfile(CWSettings.settings['plugins']['thirdparty']['text']['exepath']))
        self.btn_fileedit.clicked.connect(self.on_btn_fileedit)
        self.layout_file.addRow(_('Path'), self.le_txtfile)
        self.layout_file.addRow(_('Encoding'), self.combo_fileenc)
        self.layout_file.addRow(_('Delimiter'), self.combo_file_delim)
        self.layout_file.addRow(_('Shuffle'), self.chb_file_shuffle)
        self.layout_file.addRow(self.btn_fileedit)
        self.page_file.setLayout(self.layout_file)
        self.stacked.addWidget(self.page_file)
        
        # 3. List
        self.page_list = QtWidgets.QWidget()
        self.layout_list = QtWidgets.QFormLayout()
        self.chb_haspos = QtWidgets.QCheckBox()
        self.chb_haspos.setChecked(True)
        self.combo_list_delim = QtWidgets.QComboBox()
        self.combo_list_delim.addItems([_('SPACE'), _('TAB'), ';', ',', ':'])
        self.combo_list_delim.setEditable(True)
        self.combo_list_delim.setCurrentIndex(0)       
        self.chb_haspos.toggled.connect(self.combo_list_delim.setEnabled) 
        self.te_wlist = QtWidgets.QTextEdit('')
        self.te_wlist.setStyleSheet('font: 14pt "Courier";color: black')
        self.te_wlist.setAcceptRichText(False)
        self.te_wlist.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.chb_list_shuffle = QtWidgets.QCheckBox()
        self.chb_list_shuffle.setChecked(True)        
        self.layout_list.addRow(_('Has parts of speech'), self.chb_haspos)
        self.layout_list.addRow(_('Delimiter'), self.combo_list_delim)
        self.layout_list.addRow(_('Words'), self.te_wlist)
        self.layout_list.addRow(_('Shuffle'), self.chb_list_shuffle)
        self.page_list.setLayout(self.layout_list)
        self.stacked.addWidget(self.page_list)
                
    ## Initializes controls from word source data.
    # @param src `dict` serialized word source data (see \_\_init\_\_())
    # @see The reverse method: to_src()
    def from_src(self, src): 
        if not src: return
        
        self.le_name.setText(self.src['name'])
        
        if self.src['type'] == 'db':
            self.rb_type_db.setChecked(True)
            self.le_dbfile.setText(self.src['file'])
            self.combo_dbtype.setCurrentText(self.src['dbtype'])
            self.le_dbuser.setText(self.src['dblogin'])
            self.le_dbpass.setText(self.src['dbpass'])
            self.te_dbtables.setPlainText(json.dumps(self.src['dbtables'], indent=4))
            self.chb_db_shuffle.setChecked(self.src['shuffle'])
            
        elif self.src['type'] == 'file':
            self.rb_type_file.setChecked(True)
            self.le_txtfile.setText(self.src['file'])
            self.combo_fileenc.setCurrentText(self.src['encoding'])
            delim = self.src['delim']
            if delim == ' ':
                delim = _('SPACE')
            elif delim == '\t':
                delim = _('TAB')
            else:
                delim = delim[0]
            self.combo_file_delim.setCurrentText(delim)
            self.chb_file_shuffle.setChecked(self.src['shuffle'])
            
        elif self.src['type'] == 'list':
            self.rb_type_list.setChecked(True)
            delim = self.src['delim']
            if delim == ' ':
                delim = _('SPACE')
            elif delim == '\t':
                delim = _('TAB')
            else:
                delim = delim[0]
            self.combo_list_delim.setCurrentText(delim)
            self.chb_haspos.setChecked(self.src['haspos'])
            self.te_wlist.setPlainText('\n'.join(self.src['words']))
            self.chb_list_shuffle.setChecked(self.src['shuffle'])
            
        # activate page
        self.rb_toggled(True)
    
    ## Saves current control values to word source data dictionary (WordSrcDialog::src).
    # @see See word source data format in \_\_init\_\_()
    # @see The reverse method: from_src()
    def to_src(self):
        if not self.src: self.src = {}
        self.src['active'] = True
        self.src['name'] = self.le_name.text().strip()
        if self.rb_type_db.isChecked():
            self.src['type'] = 'db'
            self.src['file'] = self.le_dbfile.text()
            self.src['dbtype'] = self.combo_dbtype.currentText()
            self.src['dblogin'] = self.le_dbuser.text()
            self.src['dbpass'] = self.le_dbpass.text()
            self.src['dbtables'] = json.loads(self.te_dbtables.toPlainText())
            self.src['shuffle'] = self.chb_db_shuffle.isChecked()
                
        elif self.rb_type_file.isChecked():
            self.src['type'] = 'file'
            self.src['file'] = self.le_txtfile.text()
            self.src['encoding'] = self.combo_fileenc.currentText()
            delim = self.combo_file_delim.currentText()
            if delim == _('SPACE'):
                delim = ' '
            elif delim == _('TAB'):
                delim = '\t'
            else:
                delim = delim[0]
            self.src['delim'] = delim
            self.src['shuffle'] = self.chb_file_shuffle.isChecked()
            
        else:
            self.src['type'] = 'list'
            delim = self.combo_list_delim.currentText()
            if delim == _('SPACE'):
                delim = ' '
            elif delim == _('TAB'):
                delim = '\t'
            else:
                delim = delim[0]
            self.src['delim'] = delim
            self.src['haspos'] = self.chb_haspos.isChecked()
            self.src['words'] = self.te_wlist.toPlainText().strip().split('\n')
            self.src['shuffle'] = self.chb_list_shuffle.isChecked()
    
    ## Performs various checks of current control values.
    def validate(self):
        if not self.le_name.text().strip():
            MsgBox(_('Source must have a non-empty name!'), self, _('Error'), 'error')
            return False
        if self.rb_type_db.isChecked():
            if not self.le_dbfile.text() or not self.le_dbfile.text() in LANG:
                MsgBox(_('DB file path must be valid!'), self, _('Error'), 'error')
                return False
            try:
                d = json.loads(self.te_dbtables.toPlainText())
                if not isinstance(d, dict): 
                    raise Exception(_('DB tables field has incorrect value!'))
                # check presence of obligatory keys
                if not 'words' in d:
                    raise Exception(_("DB table structure must define the 'words' dictionary!"))
                if not 'table' in d['words']:
                    raise Exception(_("DB table 'words' object must define the 'table' key!"))
                if not 'fwords' in d['words']:
                    raise Exception(_("DB table 'words' object must define the 'fwords' key!"))
            except Exception as err:
                ex = f"Example table structure:{NEWLINE}{str(SQL_TABLES)}"
                MsgBox(str(err) + '\n' + ex, self, _('Error'), 'error')
                return False
            
        elif self.rb_type_file.isChecked():
            if not self.le_txtfile.text():
                MsgBox(_('Text file path must be valid!'), self, _('Error'), 'error')
                return False
            if not self.combo_fileenc.currentText():
                MsgBox(_('Text file encoding must not be empty!'), self, _('Error'), 'error')
                return False
            delim = self.combo_file_delim.currentText()
            if not delim:
                MsgBox(_('Text file delimiter must not be empty!'), self, _('Error'), 'error')
                return False
            if not delim in (_('SPACE'), _('TAB')) and len(delim) > 1:
                MsgBox(_('Text file delimiter must be either "SPACE" or "TAB" or a single character!'), self, _('Error'), 'error')
                return False
            
        elif self.rb_type_list.isChecked():
            if self.chb_haspos.isChecked():
                delim = self.combo_list_delim.currentText()
                if not delim:
                    MsgBox(_('Word list delimiter must not be empty if is has parts of speech!'), self, _('Error'), 'error')
                    return False
                if not delim in (_('SPACE'), _('TAB')) and len(delim) > 1:
                    MsgBox(_('Word list delimiter must be either "SPACE" or "TAB" or a single character!'), self, _('Error'), 'error')
                    return False
            if not self.te_wlist.toPlainText().strip():
                MsgBox(_('Word list is empty or invalid!'), self, _('Error'), 'error')
                return False
            
        self.to_src()
        return True
    
    ## @brief Fires when WordSrcDialog::rb_type_db is toggled on or off.
    # Switches to the corresponding tab.
    @QtCore.pyqtSlot(bool)        
    def rb_toggled(self, toggled):
        if self.rb_type_db.isChecked():
            self.stacked.setCurrentIndex(0)
        elif self.rb_type_file.isChecked():
            self.stacked.setCurrentIndex(1)
        elif self.rb_type_list.isChecked():
            self.stacked.setCurrentIndex(2)

    ## @brief Fired when WordSrcDialog::btn_dbedit is clicked.
    # Launches the external DB editor 
    # (if present in guisettings::CWSettings::settings['plugins']['thirdparty']['dbbrowser']['exepath'])
    @QtCore.pyqtSlot()
    def on_btn_dbedit(self):
        settings = CWSettings.settings['plugins']['thirdparty']['dbbrowser']
        if not settings['active'] or not os.path.isfile(settings['exepath']):
            return
        if not self.validate():
            return
        cmd = settings['command'].replace('<table>', self.src['dbtables']['words']['table'])
        cmd = cmd.replace('<file>', os.path.abspath(self.src['file'] if not self.src['file'].lower() in LANG else os.path.join(DICFOLDER, self.src['file'] + '.db')))
        run_exe(f"{settings['exepath']} {cmd}", False, False, shell=True) 

    ## @brief Fired when WordSrcDialog::btn_fileedit is clicked.
    # Launches the external text file editor 
    # (if present in guisettings::CWSettings::settings['plugins']['thirdparty']['text']['exepath'])
    @QtCore.pyqtSlot()
    def on_btn_fileedit(self):
        settings = CWSettings.settings['plugins']['thirdparty']['text']
        if not settings['active'] or not os.path.isfile(settings['exepath']):
            return
        if not self.validate():
            return
        cmd = settings['command'].replace('<file>', os.path.abspath(self.src['file']))
        run_exe(f"{settings['exepath']} {cmd}", False, False, shell=True)

    @QtCore.pyqtSlot(QtGui.QSyntaxHighlighter, str, str, int, int, int)
    def on_decode_error(self, hiliter, msg, doc, pos, lineno, colno):
        # report parse error
        self.te_te_dbtables_error.setPlainText(_('{}\nat line {}, column {}').format(msg, lineno, colno))
        self.te_te_dbtables_error.show()
        # set cursor to that position
        try:
            cursor = self.te_dbtables.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.movePosition(QtGui.QTextCursor.Right, QtGui.QTextCursor.MoveAnchor, pos)
            self.te_dbtables.setTextCursor(cursor)
            self.te_dbtables.setFocus()
        except:
            pass

    @QtCore.pyqtSlot(QtGui.QSyntaxHighlighter)
    def on_decode_success(self, hiliter):
        self.te_te_dbtables_error.hide()
        self.te_te_dbtables_error.clear()


# ******************************************************************************** #
# *****          ToolbarCustomizer
# ******************************************************************************** #  

## @brief Toolbar customizer widget (incorporated by SettingsDialog).
# This widget provides the user with a handy tool to tweak a toolbar (in this app
# only the main toolbar is customizable) by adding / removing buttons / separators and changing
# their order.
# @todo implement Drag And Drop from treeview to list / toolbar --
# see [example](https://doc.qt.io/qt-5/qtwidgets-draganddrop-fridgemagnets-example.html)
class ToolbarCustomizer(QtWidgets.QWidget):

    ## Constructor.
    # @param action_source `QtWidgets.QActionGroup` | `QtWidgets.QMenu` | `QtWidgets.QAction` source for actions
    # added as toolbar buttons -- either an action group or a menu, or a single action
    # @param toolbar `QtWidgets.QToolBar` the initial (source) toolbar that must be configured
    # (each of which may have child actions)
    # @param parent `QtWidgets.QWidget` parent widget
    def __init__(self, action_source, toolbar, parent=None):
        if not action_source or not toolbar:
            raise Exception(_('Null action source or toolbar pointers passed to ToolbarCustomizer!'))
        ## @brief `QtWidgets.QActionGroup` | `QtWidgets.QMenu` | `QtWidgets.QAction` source for actions
        # The source actions will be shown on the left-hand panel (ToolbarCustomizer::tw_actions)
        self.action_source = action_source
        ## @brief `QtWidgets.QToolBar` the initial (source) toolbar that must be configured
        # All buttons (actions) already present in the toolbar will be shown on the right-hand panel 
        # (ToolbarCustomizer::lw_added)
        self.src_toolbar = toolbar
        ## `list` of source actions
        self.src_actions = []
        super().__init__(parent)
        self.addMainLayout()
        self.add_src_action(self.action_source)
        self.update_src_actions()
        self.update_actions()
        #self.update_added(self.src_toolbar.actions(), False)
        
    ## Creates the main layout for controls.
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QHBoxLayout()    
        self.splitter1 = QtWidgets.QSplitter()
        self.splitter1.setChildrenCollapsible(False)

        ## `QtWidgets.QTreeWidget` source actions (buttons) that can be added to the toolbar
        self.tw_actions = QtWidgets.QTreeWidget()
        self.tw_actions.setColumnCount(1)
        self.tw_actions.setHeaderHidden(True)
        self.tw_actions.setMinimumWidth(100)
        self.tw_actions.setMaximumWidth(500)
        self.tw_actions.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tw_actions.itemSelectionChanged.connect(self.on_tw_actions_selected)
        self.splitter1.addWidget(self.tw_actions)
        
        self.layout_right = QtWidgets.QHBoxLayout()
        self.tb = QtWidgets.QToolBar()
        self.tb.setOrientation(QtCore.Qt.Vertical)
        self.act_add = self.tb.addAction(QtGui.QIcon(f"{ICONFOLDER}/fast-forward.png"), _('Add'), self.on_act_add)
        self.act_remove = self.tb.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind.png"), _('Remove'), self.on_act_remove)
        self.act_addsep = self.tb.addAction(QtGui.QIcon(f"{ICONFOLDER}/pipe.png"), _('Add separator'), self.on_act_addsep)
        self.tb.addSeparator()
        self.act_clear = self.tb.addAction(QtGui.QIcon(f"{ICONFOLDER}/garbage.png"), _('Clear'), self.on_act_clear)
        self.tb.addSeparator()
        self.act_up = self.tb.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-L.png"), _('Up'), self.on_act_up)
        self.act_down = self.tb.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-R.png"), 
                                        # NOTE: arrow button
                                        _('Down'), self.on_act_down)
        self.layout_right.addWidget(self.tb)
        self.layout_preview = QtWidgets.QVBoxLayout()
        self.l_added = QtWidgets.QLabel(_('Added items:'))
        ## `QtWidgets.QListWidget` target actions (buttons) and separators to be shown in the toolbar
        self.lw_added = QtWidgets.QListWidget()
        self.lw_added.itemSelectionChanged.connect(self.on_tw_actions_selected)
        self.layout_preview.addWidget(self.l_added)
        self.layout_preview.addWidget(self.lw_added)
        self.layout_right.addLayout(self.layout_preview)
        self.w_layout_right = QtWidgets.QWidget()
        self.w_layout_right.setLayout(self.layout_right)
        self.splitter1.addWidget(self.w_layout_right)

        self.layout_controls.addWidget(self.splitter1)
        self.setLayout(self.layout_controls)

    ## Enables or disables actions depending on the selection of source and target buttons.
    def update_actions(self):
        cur_treeitem = self.tw_actions.currentItem() 
        cur_lwitem = self.lw_added.currentItem()
        self.act_add.setEnabled(not cur_treeitem is None)
        self.act_remove.setEnabled(not cur_lwitem is None)
        self.act_clear.setEnabled(self.lw_added.count() > 0)
        self.act_up.setEnabled((not cur_lwitem is None) and self.lw_added.currentRow() > 0)
        self.act_down.setEnabled((not cur_lwitem is None) and self.lw_added.currentRow() < (self.lw_added.count() - 1))

    ## Disables elements in the source action treeview which are already added to the target list view.
    def update_src_actions(self):
        for src_action in self.src_actions:
            flags = QtCore.Qt.ItemIsEnabled
            if not src_action[0].isSeparator():
                flags |= QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
            src_action[1].setFlags(flags)
            for i in range(self.lw_added.count()):
                item = self.lw_added.item(i)
                if item.text() == '———': continue
                act_ = item.data(QtCore.Qt.UserRole)
                if src_action[0] is act_:
                    src_action[1].setFlags(QtCore.Qt.NoItemFlags)
                    break
        self.tw_actions.show() 

    ## Resets (reloads) source and target actions from the source toolbar.
    def reset(self):
        self.src_actions.clear()
        self.tw_actions.clear()
        self.add_src_action(self.action_source)
        self.update_added(self.src_toolbar.actions())
        self.update_src_actions()
        self.update_actions()

    ## Util function: adds a new item to a QListWidget control.
    def _lw_add(self, lw, item, row=-1):
        if row >= 0:
            lw.insertItem(row, item)
        else:
            lw.addItem(item)

    ## Reloads the right-hand actions (list view) from an action source.
    # @param actions `iterable` collection of source actions (each of type `QtWidgets.QAction`)
    # @param clear `bool` whether to clear the existing items (actions) before adding new ones
    def update_added(self, actions, clear=True):
        row = self.lw_added.currentRow()
        if clear:
            self.lw_added.clear()
        for act_ in actions:
            if act_.isSeparator():
                self._lw_add(self.lw_added, '———', row)
            else:
                item = QtWidgets.QListWidgetItem(act_.text())
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled)
                if act_.icon():
                    item.setIcon(act_.icon())
                item.setData(QtCore.Qt.UserRole, act_)
                self._lw_add(self.lw_added, item, row)
                #self.lw_added.addAction(act_)      
        self.update_actions()   

    ## @brief Adds a source action to the left-hand treeview.
    # @param action `QtWidgets.QActionGroup` | `QtWidgets.QMenu` | `QtWidgets.QAction` source for actions
    # added as toolbar buttons -- either an action group or a menu, or a single action
    # (each of which may have child actions)
    # @param tree_item `QtWidgets.QTreeWidgetItem` | `None` tree widget item to add the action(s) to:
    # if `None`, actions will be added as root nodes, otherwise they will be the children of 'tree_item'
    # @returns `QtWidgets.QTreeWidgetItem` the added tree widget item
    def add_src_action(self, action, tree_item=None):
        if is_iterable(action):
            item = None
            for act_ in action:
                item = self.add_src_action(act_, tree_item)
            return item
        
        if isinstance(action, QtWidgets.QActionGroup):
            return self.add_src_action(action.actions(), tree_item)          

        if isinstance(action, QtWidgets.QMenu):
            return self.add_src_action(action.actions(), self.add_src_action(action.menuAction(), tree_item) if action.isSeparator() else tree_item)
            
        if not isinstance(action, QtWidgets.QAction): return None

        txt = action.text()
        item = QtWidgets.QTreeWidgetItem([txt or _('<Unnamed>')])
        flags = QtCore.Qt.ItemIsEnabled
        if not action.isSeparator():
            flags |= QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
        item.setFlags(flags)
        item.setData(0, QtCore.Qt.UserRole, action)
        if action.icon():
            item.setIcon(0, action.icon())
        item.setToolTip(0, action.toolTip())
        if tree_item and isinstance(tree_item, QtWidgets.QTreeWidgetItem):
            tree_item.addChild(item)
        else:
            self.tw_actions.addTopLevelItem(item)
        self.src_actions.append((action, item))        
        return item

    ## Initializes added actions from a list of action names as in CWSettings['gui']['toolbar_actions'].
    # @param act_list `iterable` collection (e.g. list) of actions and 'SEP' (separators)
    # @see ToolbarCustomizer::to_list()
    def from_list(self, act_list):
        mainwin = self.src_toolbar.window()
        actions = []
        for act_ in act_list:
            action = None
            if act_ == 'SEP':
                action = QtWidgets.QAction()
                action.setSeparator(True)
            else:
                action = getattr(mainwin, act_, None)
            if action: actions.append(action)
        self.update_added(actions)
        self.update_src_actions()

    ## Serializes the added actions into a flat list of actions and 'SEP' (separators).
    # @returns `list` list of actions and 'SEP' (separators)
    # @see ToolbarCustomizer::from_list()
    def to_list(self):
        mainwin = self.src_toolbar.window()
        lst = []
        for i in range(self.lw_added.count()):
            item = self.lw_added.item(i)
            if item.text() == '———':
                lst.append('SEP')
            else:
                act_ = item.data(QtCore.Qt.UserRole)
                if isinstance(act_, QtWidgets.QAction):
                    for k, v in mainwin.__dict__.items():
                        if act_ == v:
                            lst.append(k)
                            break
        return lst

    ## Adds selected action(s) to the target list.
    @QtCore.pyqtSlot()
    def on_act_add(self):
        sel_treeitems = self.tw_actions.selectedItems()
        if len(sel_treeitems) == 0: return
        actions = [item.data(0, QtCore.Qt.UserRole) for item in sel_treeitems]
        self.update_added(actions, False)  
        self.update_src_actions()   

    ## Adds a separator after the selected action.
    @QtCore.pyqtSlot()
    def on_act_addsep(self):
        sepitem = '———'
        self._lw_add(self.lw_added, sepitem, self.lw_added.currentRow())
        self.update_actions()

    ## Removes the selected action from the target list.
    @QtCore.pyqtSlot()
    def on_act_remove(self):
        cur = self.lw_added.currentRow()
        if cur >= 0:
            self.lw_added.takeItem(cur)
        self.update_actions()
        self.update_src_actions()

    ## Clears all added actions.
    @QtCore.pyqtSlot()
    def on_act_clear(self):
        self.lw_added.clear()
        self.update_actions()
        self.update_src_actions()

    ## Moves selected action up.
    @QtCore.pyqtSlot()
    def on_act_up(self):
        item = self.lw_added.currentItem()
        if not item: return
        row = self.lw_added.row(item)
        if not row: return
        self.lw_added.insertItem(row - 1, self.lw_added.takeItem(row))
        self.lw_added.setCurrentRow(row - 1)
        self.update_actions()

    ## Moves selected action down.
    @QtCore.pyqtSlot()
    def on_act_down(self):
        item = self.lw_added.currentItem()
        if not item: return
        row = self.lw_added.row(item)
        if row == (self.lw_added.count() - 1): return
        self.lw_added.insertItem(row + 1, self.lw_added.takeItem(row))
        self.lw_added.setCurrentRow(row + 1)
        self.update_actions()

    ## Updates available actions when the selection changes.
    @QtCore.pyqtSlot()
    def on_tw_actions_selected(self):
        self.update_actions()

# ******************************************************************************** #
# *****          CustomPluginDialog
# ******************************************************************************** #        

## Dialog to add or edit custom plugins.
class CustomPluginDialog(BasicDialog):

    ## Constructor.
    # @param mainwindow `QtWidgets.QMainWindow` pointer to gui::MainWindow instance
    # @param title `str` dialog title
    # @param plugin_category `str` plugin category name (default = empty, user will choose)
    # @param plugin_name `str` plugin name (default = empty)
    # @param plugin_desc `str` plugin description (default = empty)
    # @param plugin_vers `str` plugin version (default = empty)
    # @param plugin_auth `str` plugin author (default = empty)
    # @param plugin_copyright `str` plugin copyright (default = empty)
    # @param plugin_website `str` plugin website (default = empty)
    # @param plugin_path `str` plugin module path (default = empty)
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, mainwindow, title, plugin_category='', plugin_name='', plugin_desc='',
            plugin_vers='', plugin_auth='', plugin_copyright='', plugin_website='', plugin_path='',
            parent=None, flags=QtCore.Qt.WindowFlags()):
        self.mainwindow = mainwindow
        self.presets = {'plugin_category': plugin_category, 'plugin_name': plugin_name,
                        'plugin_desc': plugin_desc, 'plugin_vers': plugin_vers,
                        'plugin_auth': plugin_auth, 'plugin_copyright': plugin_copyright,
                        'plugin_website': plugin_website, 'plugin_path': plugin_path}
        super().__init__(None, title, 'addon.png', parent, flags)

    def addMainLayout(self):
        self.layout_controls = QtWidgets.QFormLayout()

        self.le_name = QtWidgets.QLineEdit(self.presets['plugin_name'])
        self.combo_category = QtWidgets.QComboBox()
        self.combo_category.setEditable(False)
        self.combo_category.addItems([k for k in self.mainwindow.options()['plugins']['custom']])
        index = self.combo_category.findText(self.presets['plugin_category'])
        self.combo_category.setCurrentIndex(index if index >= 0 else 0)
        self.le_author = QtWidgets.QLineEdit(self.presets['plugin_auth'])
        self.le_version = QtWidgets.QLineEdit(self.presets['plugin_vers'])
        self.le_copyright = QtWidgets.QLineEdit(self.presets['plugin_copyright'])
        self.te_description = QtWidgets.QPlainTextEdit(self.presets['plugin_desc'])
        self.le_website = QtWidgets.QLineEdit(self.presets['plugin_website'])
        self.combo_source = QtWidgets.QComboBox()
        self.combo_source.setEditable(False)
        self.combo_source.addItems([_('From file'), _('Edit in Editor')])        
        self.le_sourcepath = BrowseEdit(self.presets['plugin_path'], filefilters=_('Python source files (*.py)'))
        self.combo_source.currentIndexChanged.connect(self.on_combo_source)
        self.combo_source.setCurrentIndex(0)

        self.layout_controls.addRow(_('Category'), self.combo_category)
        self.layout_controls.addRow(_('Name'), self.le_name)
        self.layout_controls.addRow(_('Author'), self.le_author)
        self.layout_controls.addRow(_('Version'), self.le_version)
        self.layout_controls.addRow(_('Description'), self.te_description)
        self.layout_controls.addRow(_('Copyright'), self.le_copyright)
        self.layout_controls.addRow(_('Website'), self.le_website)
        self.layout_controls.addRow(_('Plugin source'), self.combo_source)
        self.layout_controls.addRow(_('Source path'), self.le_sourcepath)

    def validate(self):
        catname = self.combo_category.currentText()
        if not catname:
            MsgBox(_('Plugin category must be assigned!'), title=_('Invalid input'), msgtype='error')
            return False
        plname = self.le_name.text().strip()        
        if len(plname) < 4:
            MsgBox(_('Plugin name must contain at least 4 letters!'), title=_('Invalid input'), msgtype='error')
            return False
        if not self.presets['plugin_name']:
            for pl in self.mainwindow.plugin_mgr.getPluginsOfCategory(catname):
                if pl.name == plname:
                    MsgBox(_('Plugin name "{}" is already occupied! Please choose another.').format(plname), title=_('Invalid input'), msgtype='error')
                    return False
        vers = self.le_version.text().strip()
        if vers:
            try:
                parsed_vers = version.StrictVersion(vers)
            except ValueError:
                MsgBox(_('Version string "{}" is incorrectly formatted!').format(vers), title=_('Invalid input'), msgtype='error')
                return False
        if self.combo_source.currentIndex() == 0 and not os.path.isfile(self.le_sourcepath.text()):
            MsgBox(_('Path to source file is invalid!'), title=_('Invalid input'), msgtype='error')
            return False
        return True

    ## Fires when an item in the 'Plugin source' combobox is selected.
    @QtCore.pyqtSlot(int)
    def on_combo_source(self, index):
        self.le_sourcepath.setVisible(index == 0)
        self.adjustSize()


# ******************************************************************************** #
# *****          CustomPluginManager
# ******************************************************************************** # 

## @brief Custom plugin manager widget to add, delete, (de)activate and move around plugins.
# This is basically a tree-like table with a toolbar for manipulating plugins. Each plugin
# is a single row in the table. Parent nodes in the tree represent plugin categories.
class CustomPluginManager(QtWidgets.QWidget):

    ## Constructor.
    # @param mainwindow `QtWidgets.QMainWindow` pointer to gui::MainWindow instance
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    def __init__(self, mainwindow, parent=None):
        super().__init__(parent)
        self.mainwindow = mainwindow
        self.addMainLayout()

    def addMainLayout(self):
        self.lo_main = QtWidgets.QVBoxLayout()
        self.tb_main = QtWidgets.QToolBar()
        self.lo_main.addWidget(self.tb_main)

        self.act_reload = self.tb_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/repeat.png"), _('Reload'))
        self.act_reload.setToolTip(_('Reload plugins from plugin folder'))
        self.act_reload.triggered.connect(self.on_act_reload)

        self.act_add = self.tb_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/plus.png"), _('New'))
        self.act_add.setToolTip(_('Create new plugin'))
        self.act_add.triggered.connect(self.on_act_add)

        self.act_remove = self.tb_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/minus.png"), _('Delete'))
        self.act_remove.setToolTip(_('Delete selected plugins'))
        self.act_remove.triggered.connect(self.on_act_remove)

        self.act_edit = self.tb_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/edit.png"), _('Edit'))
        self.act_edit.setToolTip(_('Edit selected plugin'))
        self.act_edit.triggered.connect(self.on_act_edit)

        self.act_clear = self.tb_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/garbage.png"), _('Clear'))
        self.act_clear.setToolTip(_('Delete all plugins'))
        self.act_clear.triggered.connect(self.on_act_clear)

        self.tb_main.addSeparator()

        self.act_up = self.tb_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-l.png"), _('Up'))
        self.act_up.setToolTip(_('Move plugin down (lower precedence)'))
        self.act_up.triggered.connect(self.on_act_up)

        self.act_down = self.tb_main.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-r.png"), _('Down'))
        self.act_down.setToolTip(_('Move plugin up (raise precendence)'))
        self.act_down.triggered.connect(self.on_act_down)

        self.tvPlugins = QtWidgets.QTreeView()
        self.tvPlugins.setSortingEnabled(False)   
        self.tvPlugins.setSelectionMode(3)      # extended selection (Ctrl, Shift)
        self.tvPlugins.setSelectionBehavior(1)  # select rows      
        self.tvPlugins.setContextMenuPolicy(QtCore.Qt.CustomContextMenu) 
        self.tvPlugins.doubleClicked.connect(QtCore.pyqtSlot(QtCore.QModelIndex)(lambda _: self.on_act_edit()))   
        self.plugin_model = None
        self.from_settings()
        self.lo_main.addWidget(self.tvPlugins)

        self.setLayout(self.lo_main)

    ## Shortcut method to create a non-editable, disabled QStandardItem.
    def _make_empty_item(self):
        item = QtGui.QStandardItem()
        item.setFlags(QtCore.Qt.NoItemFlags)
        return item

    ## Shortcut method to create a row of QStandardItem elements 
    # where the first element is given by 'item'
    # and the rest are dummy items created by CustomPluginManager::_make_empty_item().
    # @param item `QtGui.QStandardItem` first item in the row
    # @param empty_count `int` number of dummies that follow 'item'
    # @returns `list` list of `QtGui.QStandardItem` elements
    def _make_padded_row(self, item, empty_count):
        return ([item] + [self._make_empty_item() for _ in range(empty_count)])

    ## Updates the Enabled property of each action based on the current selection
    # in the plugin table.
    def update_actions(self):
        if self.plugin_model is None:
            self.act_remove.setEnabled(False)
            self.act_edit.setEnabled(False)
            self.act_clear.setEnabled(False)
            self.act_up.setEnabled(False)
            self.act_down.setEnabled(False)
        else:
            first_item = self.plugin_model.item(0)
            hasitems = first_item.hasChildren() if first_item else False
            sel_indices = self.tvPlugins.selectionModel().selectedRows(1)
            selrows = len(sel_indices) if sel_indices else 0
            sel_index = self.tvPlugins.selectionModel().currentIndex()
            sel_item = self.plugin_model.itemFromIndex(sel_index)
            if sel_index.isValid():
                sel_parent = self.plugin_model.parent(sel_index)
            else:
                sel_parent = None
            self.act_remove.setEnabled(selrows > 0)
            self.act_edit.setEnabled(selrows == 1)
            self.act_clear.setEnabled(hasitems)
            self.act_up.setEnabled((sel_item.row() > 0) if sel_parent else False)
            self.act_down.setEnabled((sel_item.row() < (self.plugin_model.rowCount(sel_parent) - 1)) if sel_parent else False)

    ## @brief Updates the plugin table (tree view) from the global settings.
    def from_settings(self):
        self.tvPlugins.setModel(None)
        self.plugin_model = QtGui.QStandardItemModel(0, 7)
        self.plugin_model.setHorizontalHeaderLabels([_('Name'), _('Description'), 
                                                    _('Version'), _('Author'), _('Copyright'), 
                                                    _('Website'), _('Path')])
        
        settings = self.mainwindow.options()['plugins']['custom']
        for category in settings:
            if not settings[category]: continue
            root_item = QtGui.QStandardItem(category)
            root_item.setFlags(QtCore.Qt.ItemIsEnabled)
            for pl in settings[category]:
                checked = pl['active']
                item_name = QtGui.QStandardItem(pl['name'])
                item_name.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                item_name.setCheckable(True)
                item_name.setUserTristate(False)
                item_name.setCheckState(QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)
                flags = QtCore.Qt.ItemIsSelectable
                if checked: flags |= QtCore.Qt.ItemIsEnabled
                item_desc = QtGui.QStandardItem(pl['description'])
                item_desc.setFlags(flags)
                item_vers = QtGui.QStandardItem(pl['version'])
                item_vers.setFlags(flags)
                item_author = QtGui.QStandardItem(pl['author'])
                item_author.setFlags(flags)
                item_copyright = QtGui.QStandardItem(pl['copyright'])
                item_copyright.setFlags(flags)
                item_website = QtGui.QStandardItem(pl['website'])
                item_website.setFlags(flags)
                item_path = QtGui.QStandardItem(pl['path'])
                flags = QtCore.Qt.ItemIsSelectable
                if checked: flags |= QtCore.Qt.ItemIsEnabled
                item_path.setFlags(flags)
                root_item.appendRow([item_name, item_desc, item_vers, item_author, 
                                    item_copyright, item_website, item_path])
            self.plugin_model.appendRow(self._make_padded_row(root_item, 6))

        self.plugin_model.itemChanged.connect(self.on_plugin_model_changed)
        self.tvPlugins.setModel(self.plugin_model)
        self.tvPlugins.selectionModel().selectionChanged.connect(self.on_tvPlugins_selected)
        self.tvPlugins.show()
        self.tvPlugins.expandAll()
        self.update_actions()

    ## Sets the 'active' property of custom plugins in the global settings
    # based on the state of the checkboxes in the plugin table.
    def update_active_states(self):
        settings = self.mainwindow.options()['plugins']['custom']
        for i in range(self.plugin_model.rowCount()):
            parent_item = self.plugin_model.item(i)
            if not parent_item.hasChildren(): continue
            catname = parent_item.text()
            if not catname in settings: continue
            for j in range(parent_item.rowCount()):
                item = parent_item.child(j, 0)
                for pl in settings[catname]:
                    if pl['name'] == item.text():
                        pl['active'] =  bool(item.checkState())
                        break

    ## Re-creates the plugin manager instance (gui::MainWindow::plugin_mgr)
    # and updates the plugins in the manager and the global settings.
    # @param forced_update `bool` if `True`, all current plugin settings will be cleared
    # and plugins will be added anew from the plugin folder (default = `False`)
    ## @see utils::pluginmanager::PxPluginManager::update_global_settings()
    def reload_plugins(self, forced_update=False):
        self.mainwindow.create_plugin_manager(False)
        self.mainwindow.plugin_mgr.collectPlugins()
        self.update_active_states()
        self.mainwindow.plugin_mgr.update_global_settings(forced_update)
        self.from_settings()

    ## Locates a plugin in the table by category and name and selects it.
    # @param plcat `str` plugin category name
    # @param plname `str` plugin name
    # @returns `QtGui.QStandardItem` found and selected plugin item or `None` on failure to locate
    def select_plugin(self, plcat, plname):
        self.tvPlugins.clearSelection()
        found = self.plugin_model.findItems(plcat)
        if found:
            found = found[0]
            for i in range(found.rowCount()):
                item = found.child(i)
                if item.text() == plname:
                    print(plname)                  
                    self.tvPlugins.selectionModel().setCurrentIndex(item.index(), 
                        QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
                    return item
        return None

    def _collect_main_methods(self):
        return collect_pluggables(self.mainwindow)

    def create_syneditor(self, source=None, show=True, modal=False):
        from utils.synteditor import PluginSynEditorWidget
        if not hasattr(self, 'syneditor'):
            ## `utils::synteditor::PluginSynEditorWidget` inbuilt python code editor
            self.syneditor = PluginSynEditorWidget(self._collect_main_methods(), source=source)
        else:
            self.syneditor.editor.setText(source or '')
        if show: 
            if modal:
                return self.syneditor.exec()
            else:
                return self.syneditor.show()
        return None

    ## Adds a new plugin or edits the given plugin.
    # @param plugin_item `QtGui.QStandardItem` the plugin item to edit; if `None` (default),
    # a new plugin will be added
    def add_or_edit_plugin(self, plugin_item=None):
        category = ''
        old_name = ''
        old_desc = ''
        old_vers = ''
        old_auth = ''
        old_copyright = ''
        old_website = ''
        old_path = ''
        plugin_active = plugin_item is None
        if plugin_item:          
            row = plugin_item.row()  
            parent_item = plugin_item.parent()
            if not parent_item: return
            category = parent_item.text()
            old_name = parent_item.child(row, 0).text()
            old_desc = parent_item.child(row, 1).text()
            old_vers = parent_item.child(row, 2).text()
            old_auth = parent_item.child(row, 3).text()
            old_copyright = parent_item.child(row, 4).text()
            old_website = parent_item.child(row, 5).text()
            old_path = parent_item.child(row, 6).text()
            plugin_active = bool(parent_item.child(row, 0).checkState())

        new_plugin_dlg = CustomPluginDialog(self.mainwindow, 
            _('New plugin') if not plugin_item else _('Editing: {}').format(old_name),
            category, old_name, old_desc, old_vers, old_auth,
            old_copyright, old_website, old_path + '.py' if old_path else '')
        if not new_plugin_dlg.exec(): return
        
        plname = new_plugin_dlg.le_name.text().strip()
        plcat = new_plugin_dlg.combo_category.currentText()
        plauthor = new_plugin_dlg.le_author.text().strip()
        plversion = new_plugin_dlg.le_version.text().strip()
        plwebsite = new_plugin_dlg.le_website.text().strip()
        plcopyright = new_plugin_dlg.le_copyright.text().strip()
        pldesc = new_plugin_dlg.te_description.toPlainText().strip()
        plmodule = plname.replace(' ', '_').replace('-', '_')
        plfile = os.path.join(PLUGINS_FOLDER, plmodule + '.py')

        # make plugin source file
        if new_plugin_dlg.combo_source.currentIndex() == 0:
            # from file path
            fpath = new_plugin_dlg.le_sourcepath.text()
            fdir = os.path.dirname(fpath)
            if fpath != plfile:
                if os.path.samefile(fdir, PLUGINS_FOLDER):
                    os.rename(fpath, plfile)
                else:
                    copy_file(fpath, plfile)
        
        # edit source
        if os.path.isfile(plfile):
            with open(plfile, 'r', encoding=ENCODING) as srcfile:
                srctext = srcfile.read()
        else:
            srctext = PLUGIN_TEMPLATE_GENERAL.format(plmodule[0].upper() + plmodule[1:])

        if self.create_syneditor(srctext, modal=True):
            with open(plfile, 'w', encoding=ENCODING) as srcfile:
                srcfile.write(self.syneditor.currenttext().replace('\r\n', '\n'))
        elif (not plugin_item) and (new_plugin_dlg.combo_source.currentIndex() == 1):
            return

        if plugin_item:
            # delete old plugin files
            try:
                if not os.path.samefile(plfile, old_path + '.py'):
                    os.remove(old_path + '.py')
            except:
                pass            

        # make plugin info file
        plinfofile = os.path.join(PLUGINS_FOLDER, plmodule + '.' + PLUGIN_EXTENSION)

        plinfo = ['[Core]', f'Name = {plname}', f'Module = {plmodule}', '[Documentation]']
        if plauthor:
            plinfo.append(f'Author = {plauthor}')
        if plversion:
            plinfo.append(f'Version = {plversion}')
        if pldesc:
            plinfo.append(f'Description = {pldesc}')
        if plcopyright:
            plinfo.append(f'Copyright = {plcopyright}')
        if plwebsite:
            plinfo.append(f'Website = {plwebsite}')
        with open(plinfofile, 'w', encoding=ENCODING) as infofile:
            infofile.write('\n'.join(plinfo))

        if plugin_item:
            # delete old plugin files            
            try:
                if not os.path.samefile(plinfofile, old_path + '.' + PLUGIN_EXTENSION):
                    os.remove(old_path + '.' + PLUGIN_EXTENSION)
            except:
                pass

        # re-collect plugins and update settings
        self.reload_plugins()

        # select added item
        self.tvPlugins.clearSelection()
        found = self.select_plugin(plcat, plname)
        if found:
            found.setCheckState(QtCore.Qt.Checked if plugin_active else QtCore.Qt.Unchecked)
        self.update_actions()

    ## @brief Fires when a plugin is checked or unchecked in the plugin table.
    # When checked, the corresponding plugin is enabled in the table, and vice-versa.
    @QtCore.pyqtSlot('QStandardItem*') 
    def on_plugin_model_changed(self, item):
        # enable / disable plugins when checked / unchecked 'Enabled'
        parent = item.parent()
        if not parent: return
        row = item.row()
        item_name = parent.child(row, 0)
        if not item_name or not item_name.isCheckable(): return
        checked = bool(item_name.checkState())       
        # iterate children
        self.plugin_model.itemChanged.disconnect()
        for i in range(parent.columnCount()):
            next_item = parent.child(row, i)
            if i == 0:
                next_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                next_item.setCheckable(True)
            else:
                next_item.setEnabled(checked)
        self.plugin_model.itemChanged.connect(self.on_plugin_model_changed)
        self.tvPlugins.show()

    ## Fires when an item (plugin) is selected in the table.
    @QtCore.pyqtSlot(QtCore.QItemSelection, QtCore.QItemSelection)
    def on_tvPlugins_selected(self, selected, deselected):
        self.update_actions()

    ## The Reload action handler: reloads plugins from the plugin manager.
    # @see CustomPluginManager::reload_plugins()
    @QtCore.pyqtSlot()
    def on_act_reload(self): 
        reply = MsgBox(_('Reload plugins from folder? Click YES to soft-update currently loaded plugins and add new ones, NO to hard-reload plugins (current plugin config will be lost!).'), 
                       self, _('Confirm Action'), 'ask', btn=['yes', 'no', 'cancel'])
        if not reply in ('yes', 'no'): return
        self.reload_plugins(reply == 'no')

    ## The Add action handler: adds a new plugin.
    # @see CustomPluginManager::add_or_edit_plugin()
    @QtCore.pyqtSlot()
    def on_act_add(self): 
        self.add_or_edit_plugin()
        
    ## The Delete action handler: deletes the selected plugins (>=1 plugins must be selected).
    # @warning This action will permanently delete the plugin files in 'plugins' directory!
    @QtCore.pyqtSlot()
    def on_act_remove(self): 
        reply = MsgBox(_('Are you sure you would like to PERMANENTLY delete the selected plugins?\nYou can deactivate a plugin by unchecking it.'), 
                       self, _('Confirm Action'), 'ask')
        if reply != 'yes': return
        settings = self.mainwindow.options()['plugins']['custom']
        for sel_index in self.tvPlugins.selectionModel().selectedRows(0):
            item = self.plugin_model.itemFromIndex(sel_index)
            parent = item.parent()
            if not parent: continue
            plpath = parent.child(item.row(), 6).text()
            try:
                os.remove(plpath + '.py')
            except:
                pass
            try:
                os.remove(plpath + '.' + PLUGIN_EXTENSION)
            except:
                pass
        self.reload_plugins()
        self.tvPlugins.clearSelection()
        self.update_actions()
        
    ## The Edit action handler: edits the selected plugin (only one must be selected).
    @QtCore.pyqtSlot()
    def on_act_edit(self): 
        sel_index = self.tvPlugins.selectionModel().currentIndex() 
        if len(self.tvPlugins.selectionModel().selectedRows()) != 1 or \
            not sel_index.isValid() or not sel_index.parent().isValid(): return
        self.add_or_edit_plugin(self.plugin_model.itemFromIndex(sel_index))
        
    ## The Clear action handler: clears (deletes) all plugins.
    # @warning This action will permanently delete the plugin files in 'plugins' directory!
    @QtCore.pyqtSlot()
    def on_act_clear(self): 
        reply = MsgBox(_('Are you sure you would like to PERMANENTLY delete ALL plugins?\nYou can deactivate plugins by unchecking them.'), 
                       self, _('Confirm Action'), 'ask')
        if reply != 'yes': return
        walk_dir(PLUGINS_FOLDER, recurse=False, file_process_function=os.remove, file_types=('py', PLUGIN_EXTENSION))
        self.tvPlugins.clearSelection()
        self.reload_plugins()
        
    ## @brief The Up actions handler: moves the selected plugin upwards.
    # This ultimately raises the priority (precedence) of the plugin within the category
    # since it will be handled _before_ the other ones which come after it in the table. 
    @QtCore.pyqtSlot()
    def on_act_up(self): 
        sel_index = self.tvPlugins.selectionModel().currentIndex()
        if not sel_index.isValid(): return
        sel_item = self.plugin_model.itemFromIndex(sel_index)
        sel_parent = sel_item.parent()
        if not sel_parent or (sel_item.row() == 0): return
        plname = sel_item.text()
        plcat = sel_parent.text()
        settings = self.mainwindow.options()['plugins']['custom'][plcat]
        for i, pl in enumerate(settings):
            if pl['name'] == sel_item.text():
                settings.insert(i - 1, settings.pop(i))
                break
        self.reload_plugins()
        self.select_plugin(plcat, plname)
        
    ## @brief The Down actions handler: moves the selected plugin downwards.
    # This ultimately lowers the priority (precedence) of the plugin within the category
    # since it will be handled _after_ the other ones which come before it in the table. 
    @QtCore.pyqtSlot()
    def on_act_down(self): 
        sel_index = self.tvPlugins.selectionModel().currentIndex()
        if not sel_index.isValid(): return
        sel_item = self.plugin_model.itemFromIndex(sel_index)
        sel_parent = sel_item.parent()
        if not sel_parent or (sel_item.row() >= (sel_parent.rowCount() - 1)): return
        plname = sel_item.text()
        plcat = sel_parent.text()
        settings = self.mainwindow.options()['plugins']['custom'][plcat]
        for i, pl in enumerate(settings):
            if pl['name'] == sel_item.text():
                settings.insert(i + 1, settings.pop(i))
                break
        self.reload_plugins()
        self.select_plugin(plcat, plname)
        
            
# ******************************************************************************** #
# *****          SettingsDialog
# ******************************************************************************** #  

## Global app settings configuration window.        
class SettingsDialog(BasicDialog):

    ## list of stacked pages corresponding to config categories
    PAGES = [_('Common'), _('Generation'), _('Source management'), _('Search rules'),
             _('Window'), _('Grid'), _('Clues'), _('Toolbar'), _('Definition lookup'), _('Import & Export'),
             _('Third-party'), _('Custom'), _('Printing'), _('Updating'), _('Sharing')]
    ## list of parent nodes that hold several pages
    PARENT_PAGES = [_('Sources'), _('User interface'), _('Plugins')]
    
    ## Constructor.
    # @param mainwindow `QtWidgets.QMainWindow` pointer to gui::MainWindow instance
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, mainwindow=None, parent=None, flags=QtCore.Qt.WindowFlags()):
        self.mainwindow = mainwindow
        self.default_settings = self.load_default_settings()
        super().__init__(None, _('Settings'), 'settings-5.png', 
              parent, flags)
        
    ## Gets the default settings from 'defsettings.pxjson'.
    # @returns `dict` dictionary of settings loaded from the default settings file ('defsettings.pxjson').
    def load_default_settings(self):
        defsettings = CWSettings.validate_file(DEFAULT_SETTINGS_FILE)
        if defsettings: return defsettings
        CWSettings.save_to_file(DEFAULT_SETTINGS_FILE) 
        return copy.deepcopy(CWSettings.settings)
                
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QHBoxLayout()   

        ## `QtWidgets.QTreeWidget` config categories tree
        self.tree = QtWidgets.QTreeWidget()         
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(100)
        self.tree.setMaximumWidth(500)
        
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem([_('Common')]))
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem([_('Generation')]))
        item = QtWidgets.QTreeWidgetItem([_('Sources')])
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        item.addChild(QtWidgets.QTreeWidgetItem([_('Source management')]))
        item.addChild(QtWidgets.QTreeWidgetItem([_('Search rules')]))
        self.tree.addTopLevelItem(item)
        
        item = QtWidgets.QTreeWidgetItem([_('User interface')])
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        item.addChild(QtWidgets.QTreeWidgetItem([_('Window')]))
        item.addChild(QtWidgets.QTreeWidgetItem([_('Grid')]))
        item.addChild(QtWidgets.QTreeWidgetItem([_('Clues')]))
        item.addChild(QtWidgets.QTreeWidgetItem([_('Toolbar')]))
        self.tree.addTopLevelItem(item)
        
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem([_('Definition lookup')]))
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem([_('Import & Export')]))
        item = QtWidgets.QTreeWidgetItem([_('Plugins')])
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        item.addChild(QtWidgets.QTreeWidgetItem([_('Third-party')]))
        item.addChild(QtWidgets.QTreeWidgetItem([_('Custom')]))
        self.tree.addTopLevelItem(item)
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem([_('Printing')]))
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem([_('Updating')]))
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem([_('Sharing')]))
        self.tree.itemSelectionChanged.connect(self.on_tree_select)
        
        self.central_widget = QtWidgets.QWidget()
        self.layout_central = QtWidgets.QVBoxLayout()
        ## `QtWidgets.QStackedWidget` container for config pages for each category
        self.stacked = QtWidgets.QStackedWidget() 
        self.add_pages()
        self.btn_defaults = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/cloud-computing.png"), _('Restore defaults'))
        self.btn_defaults.setToolTip(_('Restore default settings for selected page'))
        self.btn_defaults.clicked.connect(self.on_btn_defaults)
        self.btn_load = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/folder-15.png"), _('Load Settings'))
        self.btn_load.setToolTip(_('Load settings from file'))
        self.btn_load.clicked.connect(self.on_btn_load)
        self.btn_save = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/save.png"), _('Save Settings'))
        self.btn_save.setToolTip(_('Save settings to file'))
        self.btn_save.clicked.connect(self.on_btn_save)
        self.layout_buttons = QtWidgets.QHBoxLayout()
        self.layout_buttons.setSpacing(20)
        self.layout_buttons.addWidget(self.btn_defaults)
        self.layout_buttons.addWidget(self.btn_load)
        self.layout_buttons.addWidget(self.btn_save)
        self.layout_central.addWidget(self.stacked)
        self.layout_central.addLayout(self.layout_buttons)
        self.central_widget.setLayout(self.layout_central)
        
        self.splitter1 = QtWidgets.QSplitter()
        self.splitter1.setChildrenCollapsible(False)
        self.splitter1.addWidget(self.tree)
        self.splitter1.addWidget(self.central_widget)
        self.layout_controls.addWidget(self.splitter1)
        
        # activate first page unless selected
        if not self.tree.currentItem():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        
    ## Creates config pages in SettingsDialog::stacked.
    def add_pages(self):
        # Common
        self.page_common = QtWidgets.QWidget()
        self.layout_common = QtWidgets.QVBoxLayout()

        self.gb_commonsettings = QtWidgets.QGroupBox(_('Common settings'))
        self.layout_gb_commonsettings = QtWidgets.QFormLayout()
        self.layout_gb_commonsettings.setSpacing(10)

        self.le_tempdir = BrowseEdit(dialogtype='folder')
        self.le_tempdir.setToolTip(_('Temp directory (leave EMPTY for default)'))
        
        self.chb_autosave_cw = QtWidgets.QCheckBox('')
        self.chb_autosave_cw.setToolTip(_('Save crosswords on exit and load on startup'))

        self.act_register_associations = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/star.png"), _('Register file associations'), None)
        self.act_register_associations.setToolTip(_('Associate crossword files (*.xpf, *.ipuz) with {}').format(APP_NAME))
        self.act_register_associations.triggered.connect(self.on_act_register_associations)
        self.btn_register_associations = QtWidgets.QToolButton()
        self.btn_register_associations.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.btn_register_associations.setDefaultAction(self.act_register_associations)
        self.btn_register_associations.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        self.layout_gb_commonsettings.addRow(_('Temp directory'), self.le_tempdir)
        self.layout_gb_commonsettings.addRow(_('Auto save/load crossword'), self.chb_autosave_cw)
        self.layout_gb_commonsettings.addRow(_('Register file associations'), self.btn_register_associations)
        self.gb_commonsettings.setLayout(self.layout_gb_commonsettings)
        self.layout_common.addWidget(self.gb_commonsettings)

        self.gb_netsettings = QtWidgets.QGroupBox(_('Net settings'))
        self.layout_gb_netsettings = QtWidgets.QFormLayout()
        self.layout_gb_netsettings.setSpacing(10)

        self.spin_req_timeout = QtWidgets.QSpinBox()
        self.spin_req_timeout.setRange(0, 60)
        self.spin_req_timeout.setValue(5)

        self.layout_proxysettings = QtWidgets.QVBoxLayout()
        self.layout_proxysettings.setContentsMargins(0, 0, 0, 0)
        self.chb_system_proxy = QtWidgets.QCheckBox(_('Use system proxy settings'))
        self.layout_proxysettings.addWidget(self.chb_system_proxy)
        self.layout_proxysettings2 = QtWidgets.QFormLayout()
        self.layout_proxysettings2.setContentsMargins(0, 0, 0, 0)        
        self.le_http_proxy = QtWidgets.QLineEdit('')
        self.le_http_proxy.setToolTip(_('HTTP proxy and port, e.g. http://192.168.1.10:3333'))
        self.le_https_proxy = QtWidgets.QLineEdit('')
        self.le_https_proxy.setToolTip(_('HTTPS proxy and port, e.g. https://192.168.1.10:3333'))
        self.layout_proxysettings2.addRow(_('HTTP proxy'), self.le_http_proxy)
        self.layout_proxysettings2.addRow(_('HTTPS proxy'), self.le_https_proxy)
        self.layout_proxysettings.addLayout(self.layout_proxysettings2)
        self.chb_system_proxy.stateChanged.connect(self.on_chb_system_proxy)

        self.layout_gb_netsettings.addRow(_('Request timeout (sec):'), self.spin_req_timeout)
        self.layout_gb_netsettings.addRow(_('Proxy settings:'), self.layout_proxysettings)
        self.gb_netsettings.setLayout(self.layout_gb_netsettings)
        self.layout_common.addWidget(self.gb_netsettings)

        self.page_common.setLayout(self.layout_common)
        self.stacked.addWidget(self.page_common)

        # Generation
        self.page_generation = QtWidgets.QWidget()
        self.layout_generation = QtWidgets.QFormLayout()
        self.layout_generation.setSpacing(10)
        self.combo_gen_method = QtWidgets.QComboBox()
        self.combo_gen_method.addItems([_('Guess'), _('Iterative'), _('Recursive')])
        self.combo_gen_method.setEditable(False)
        self.combo_gen_method.setCurrentIndex(0)
        self.spin_gen_timeout = QtWidgets.QDoubleSpinBox()
        self.spin_gen_timeout.setRange(0.0, 10000.0)
        self.spin_gen_timeout.setValue(60.0)
        self.spin_gen_timeout.setSuffix(_(' sec.'))
        self.combo_log = QtWidgets.QComboBox()
        self.combo_log.addItems([_('No log'), _('Console'), _('File...')])
        self.combo_log.setEditable(True)
        self.combo_log.setCurrentIndex(0)
        self.combo_log.activated.connect(self.on_combo_log)
                
        self.layout_generation.addRow(_('Method'), self.combo_gen_method)
        self.layout_generation.addRow(_('Timeout'), self.spin_gen_timeout)
        self.layout_generation.addRow(_('Log'), self.combo_log)
        
        self.page_generation.setLayout(self.layout_generation)
        self.stacked.addWidget(self.page_generation)
        
        # Sources > Source management
        self.page_src_mgmt = QtWidgets.QWidget()
        self.layout_src_mgmt = QtWidgets.QVBoxLayout()
        
        self.gb_src = QtWidgets.QGroupBox(_('Manage sources'))        
        self.layout_gb_src = QtWidgets.QHBoxLayout()
        self.lw_sources = QtWidgets.QListWidget()
        self.lw_sources.setToolTip(_('Higher sources in this list take higher precedence (use UP and DOWN buttons to move items)'))
        self.lw_sources.itemDoubleClicked.connect(self.on_lw_sources_dblclick)
        self.layout_gb_src.addWidget(self.lw_sources)
        
        self.tb_src_mgmt = QtWidgets.QToolBar()
        self.tb_src_mgmt.setOrientation(QtCore.Qt.Vertical)
        self.act_src_up = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-l.png"), _('Up'))
        self.act_src_up.triggered.connect(self.on_act_src_up)
        self.act_src_down = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-r.png"), 
                                                        # NOTE: arrow button
                                                        _('Down'))
        self.act_src_down.triggered.connect(self.on_act_src_down)        
        self.tb_src_mgmt.addSeparator()
        self.act_src_add = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/plus.png"), _('Add'))
        self.act_src_add.triggered.connect(self.on_act_src_add)
        self.act_src_remove = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/minus.png"), _('Remove'))
        self.act_src_remove.triggered.connect(self.on_act_src_remove)
        self.act_src_edit = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/edit.png"), _('Edit'))
        self.act_src_edit.triggered.connect(self.on_act_src_edit)
        self.act_src_clear = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/garbage.png"), _('Clear'))
        self.act_src_clear.triggered.connect(self.on_act_src_clear)
        self.layout_gb_src.addWidget(self.tb_src_mgmt)
        self.gb_src.setLayout(self.layout_gb_src)
        
        self.gb_src_settings = QtWidgets.QGroupBox(_('Settings'))
        self.layout_src_settings = QtWidgets.QGridLayout()
        self.chb_maxfetch = QtWidgets.QCheckBox(_('Constrain max results:'))
        self.chb_maxfetch.setChecked(True)
        self.spin_maxfetch = QtWidgets.QSpinBox()
        self.spin_maxfetch.setRange(0, 1e6)
        self.spin_maxfetch.setValue(MAX_RESULTS)
        self.chb_maxfetch.stateChanged.connect(self.on_chb_maxfetch_checked)
        self.layout_src_settings.addWidget(self.chb_maxfetch, 0, 0)
        self.layout_src_settings.addWidget(self.spin_maxfetch, 0, 1)
        self.gb_src_settings.setLayout(self.layout_src_settings)
                
        self.layout_src_mgmt.addWidget(self.gb_src)
        self.layout_src_mgmt.addWidget(self.gb_src_settings)
        self.page_src_mgmt.setLayout(self.layout_src_mgmt)
        self.stacked.addWidget(self.page_src_mgmt)
                
        # Sources > Search rules
        self.page_src_rules = QtWidgets.QWidget()
        self.layout_src_rules = QtWidgets.QVBoxLayout()        
        self.gb_pos = QtWidgets.QGroupBox(_('Parts of speech'))
        self.layout_gb_pos = QtWidgets.QVBoxLayout()
        self.lw_pos = QtWidgets.QListWidget()
        self.lw_pos.setToolTip(_('Check / uncheck items to include in search (valid only for sources with POS data)'))
        for p in POS[:-1]:
            lwitem = QtWidgets.QListWidgetItem(p[1])
            lwitem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            #lwitem.setData(QtCore.Qt.EditRole, p[0])
            lwitem.setCheckState(QtCore.Qt.Checked if p[0] == 'N' else QtCore.Qt.Unchecked)
            self.lw_pos.addItem(lwitem)
        self.layout_gb_pos.addWidget(self.lw_pos)
        self.gb_pos.setLayout(self.layout_gb_pos)
        self.layout_src_rules.addWidget(self.gb_pos)
        
        self.gb_excluded = QtWidgets.QGroupBox(_('Excluded words'))
        self.layout_gb_excluded = QtWidgets.QVBoxLayout()
        self.te_excluded = QtWidgets.QTextEdit('')
        self.te_excluded.setStyleSheet('font: 14pt "Courier";color: maroon')
        self.te_excluded.setAcceptRichText(False)
        self.te_excluded.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.layout_gb_excluded.addWidget(self.te_excluded)
        self.chb_excl_regex = QtWidgets.QCheckBox(_('Use regular expressions'))
        self.chb_excl_regex.setChecked(False)
        self.layout_gb_excluded.addWidget(self.chb_excl_regex)
        self.gb_excluded.setLayout(self.layout_gb_excluded)
        self.layout_src_rules.addWidget(self.gb_excluded)
        
        self.page_src_rules.setLayout(self.layout_src_rules)
        self.stacked.addWidget(self.page_src_rules)
        
        # UI > Window
        self.page_window = QtWidgets.QWidget()
        self.layout_window = QtWidgets.QFormLayout()
                
        self.combo_apptheme = QtWidgets.QComboBox()
        self.combo_apptheme.addItems(QtWidgets.QStyleFactory.keys())
        self.combo_apptheme.setEditable(False)
        self.combo_apptheme.setCurrentText(QtWidgets.QApplication.instance().style().objectName())
        self.combo_toolbarpos = QtWidgets.QComboBox()
        self.combo_toolbarpos.addItems([_('Top'), _('Bottom'), _('Left'), _('Right'), _('Hidden')])
        self.combo_toolbarpos.setEditable(False)
        self.combo_toolbarpos.setCurrentIndex(0)
        
        self.layout_window.addRow(_('Theme'), self.combo_apptheme)
        self.layout_window.addRow(_('Toolbar position'), self.combo_toolbarpos)
        self.page_window.setLayout(self.layout_window)
        self.stacked.addWidget(self.page_window)
        
        # UI > Grid
        self.page_grid = QtWidgets.QScrollArea()
        self.page_grid.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.page_grid.setWidgetResizable(True)
        self.layout_grid = QtWidgets.QFormLayout()
        self.layout_grid.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        
        self.spin_cwscale = QtWidgets.QSpinBox()
        self.spin_cwscale.setRange(100, 300)
        self.spin_cwscale.setValue(100)        
        self.chb_showgrid = QtWidgets.QCheckBox('')
        self.chb_showgrid.setChecked(True)
        self.chb_showcoords = QtWidgets.QCheckBox('')
        self.chb_showcoords.setChecked(False)
        self.combo_gridlinestyle = QtWidgets.QComboBox()
        self.combo_gridlinestyle.addItems([_('Solid'), _('Dash'), _('Dot'), _('Dash-dot')])
        self.combo_gridlinestyle.setEditable(False)
        self.combo_gridlinestyle.setCurrentIndex(0)
        self.spin_gridlinesz = QtWidgets.QSpinBox()
        self.spin_gridlinesz.setRange(0, 10)
        self.spin_gridlinesz.setValue(1)
        self.btn_gridlinecolor = QtWidgets.QPushButton('')
        self.btn_gridlinecolor.setStyleSheet('background-color: gray;')
        self.btn_gridlinecolor.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_gridlinecolor.clicked.connect(self.on_color_btn_clicked)
        self.btn_activecellcolor = QtWidgets.QPushButton('')
        self.btn_activecellcolor.setStyleSheet('background-color: blue;')
        self.btn_activecellcolor.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_activecellcolor.clicked.connect(self.on_color_btn_clicked)
        self.spin_cellsz = QtWidgets.QSpinBox()
        self.spin_cellsz.setRange(20, 80)
        self.spin_cellsz.setValue(40)
        self.chb_shownumbers = QtWidgets.QCheckBox('')
        self.chb_shownumbers.setChecked(True)
        self.btn_numberscolor = QtWidgets.QPushButton('')
        self.btn_numberscolor.setStyleSheet('background-color: gray;')
        self.btn_numberscolor.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_numberscolor.clicked.connect(self.on_color_btn_clicked)
        self.btn_numbersfont = QtWidgets.QPushButton(_('Font...'))
        self.btn_numbersfont.setStyleSheet('font-family: "Arial"; font-size: 8pt; font-weight: bold;')
        self.btn_numbersfont.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_numbersfont.clicked.connect(self.on_font_btn_clicked)
        self.combo_charcase = QtWidgets.QComboBox()
        self.combo_charcase.addItems([_('UPPERCASE'), _('lowercase')])
        self.combo_charcase.setEditable(False)
        self.combo_charcase.setCurrentIndex(1)
        
        # cell formatting
        self.btn_cell_normal_bg_color = QtWidgets.QPushButton('')
        self.btn_cell_normal_bg_color.setStyleSheet('background-color: white;')
        self.btn_cell_normal_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_normal_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_cell_normal_style = QtWidgets.QComboBox()
        self.combo_cell_normal_style.addItems([_('Solid'), _('Dense'), _('Striped'), _('Lines'), _('Checkered'), _('Diag1'), _('Diag2'), _('Diag cross'), _('Gradient linear'), _('Gradient radial')])
        self.combo_cell_normal_style.setEditable(False)
        self.combo_cell_normal_style.setCurrentIndex(0)
        self.btn_cell_normal_fg_color = QtWidgets.QPushButton('')
        self.btn_cell_normal_fg_color.setStyleSheet('background-color: black;')
        self.btn_cell_normal_fg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_normal_fg_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_cell_normal_font = QtWidgets.QPushButton(_('Font...'))
        self.btn_cell_normal_font.setStyleSheet('font-family: "Arial"; font-size: 18pt; font-weight: bold;')
        self.btn_cell_normal_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_normal_font.clicked.connect(self.on_font_btn_clicked)
        
        self.btn_cell_hilite_bg_color = QtWidgets.QPushButton('')
        self.btn_cell_hilite_bg_color.setStyleSheet('background-color: yellow;')
        self.btn_cell_hilite_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_hilite_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_cell_hilite_style = QtWidgets.QComboBox()
        self.combo_cell_hilite_style.addItems([_('Solid'), _('Dense'), _('Striped'), _('Lines'), _('Checkered'), _('Diag1'), _('Diag2'), _('Diag cross'), _('Gradient linear'), _('Gradient radial')])
        self.combo_cell_hilite_style.setEditable(False)
        self.combo_cell_hilite_style.setCurrentIndex(0)
        self.btn_cell_hilite_fg_color = QtWidgets.QPushButton('')
        self.btn_cell_hilite_fg_color.setStyleSheet('background-color: black;')
        self.btn_cell_hilite_fg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_hilite_fg_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_cell_hilite_font = QtWidgets.QPushButton(_('Font...'))
        self.btn_cell_hilite_font.setStyleSheet('font-family: "Arial"; font-size: 18pt; font-weight: bold;')
        self.btn_cell_hilite_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_hilite_font.clicked.connect(self.on_font_btn_clicked)
        
        self.btn_cell_blank_bg_color = QtWidgets.QPushButton('')
        self.btn_cell_blank_bg_color.setStyleSheet('background-color: white;')
        self.btn_cell_blank_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_blank_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_cell_blank_style = QtWidgets.QComboBox()
        self.combo_cell_blank_style.addItems([_('Solid'), _('Dense'), _('Striped'), _('Lines'), _('Checkered'), _('Diag1'), _('Diag2'), _('Diag cross'), _('Gradient linear'), _('Gradient radial')])
        self.combo_cell_blank_style.setEditable(False)
        self.combo_cell_blank_style.setCurrentIndex(0)
        
        self.btn_cell_filler_bg_color = QtWidgets.QPushButton('')
        self.btn_cell_filler_bg_color.setStyleSheet('background-color: black;')
        self.btn_cell_filler_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_filler_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_cell_filler_style = QtWidgets.QComboBox()
        self.combo_cell_filler_style.addItems([_('Solid'), _('Dense'), _('Striped'), _('Lines'), _('Checkered'), _('Diag1'), _('Diag2'), _('Diag cross'), _('Gradient linear'), _('Gradient radial')])
        self.combo_cell_filler_style.setEditable(False)
        self.combo_cell_filler_style.setCurrentIndex(0)
        
        self.btn_cell_filler2_bg_color = QtWidgets.QPushButton('')
        self.btn_cell_filler2_bg_color.setStyleSheet('background-color: black;')
        self.btn_cell_filler2_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_filler2_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_cell_filler2_style = QtWidgets.QComboBox()
        self.combo_cell_filler2_style.addItems([_('Solid'), _('Dense'), _('Striped'), _('Lines'), _('Checkered'), _('Diag1'), _('Diag2'), _('Diag cross'), _('Gradient linear'), _('Gradient radial')])
        self.combo_cell_filler2_style.setEditable(False)
        self.combo_cell_filler2_style.setCurrentIndex(0)        
        
        self.layout_grid.addRow(_('Grid scale'), self.spin_cwscale)
        self.layout_grid.addRow(_('Show grid borders'), self.chb_showgrid)
        self.layout_grid.addRow(_('Show grid coords'), self.chb_showcoords)
        self.layout_grid.addRow(_('Grid border style'), self.combo_gridlinestyle)
        self.layout_grid.addRow(_('Grid border width'), self.spin_gridlinesz)
        self.layout_grid.addRow(_('Grid border color'), self.btn_gridlinecolor)
        self.layout_grid.addRow(_('Active cell color'), self.btn_activecellcolor)
        self.layout_grid.addRow(_('Grid cell size'), self.spin_cellsz)
        self.layout_grid.addRow(_('Character case'), self.combo_charcase)
        self.layout_wspacer1 = QtWidgets.QVBoxLayout()
        self.layout_wspacer1.addSpacing(20)        
        self.layout_grid.addRow(self.layout_wspacer1)
        self.layout_grid.addRow(_('Show word numbers'), self.chb_shownumbers)
        self.layout_grid.addRow(_('Word number color'), self.btn_numberscolor)
        self.layout_grid.addRow(_('Word number font'), self.btn_numbersfont)
        self.layout_wspacer2 = QtWidgets.QVBoxLayout()
        self.layout_wspacer2.addSpacing(20)
        self.layout_grid.addRow(self.layout_wspacer2)
        self.layout_grid.addRow(_('Normal cell color'), self.btn_cell_normal_bg_color)
        self.layout_grid.addRow(_('Normal cell style'), self.combo_cell_normal_style)
        self.layout_grid.addRow(_('Normal cell font color'), self.btn_cell_normal_fg_color)
        self.layout_grid.addRow(_('Normal cell font'), self.btn_cell_normal_font)
        self.layout_wspacer3 = QtWidgets.QVBoxLayout()
        self.layout_wspacer3.addSpacing(20)
        self.layout_grid.addRow(self.layout_wspacer3)
        self.layout_grid.addRow(_('Hilite cell color'), self.btn_cell_hilite_bg_color)
        self.layout_grid.addRow(_('Hilite cell style'), self.combo_cell_hilite_style)
        self.layout_grid.addRow(_('Hilite cell font color'), self.btn_cell_hilite_fg_color)
        self.layout_grid.addRow(_('Hilite cell font'), self.btn_cell_hilite_font)
        self.layout_wspacer4 = QtWidgets.QVBoxLayout()
        self.layout_wspacer4.addSpacing(20)
        self.layout_grid.addRow(self.layout_wspacer4)
        self.layout_grid.addRow(_('Blank cell color'), self.btn_cell_blank_bg_color)
        self.layout_grid.addRow(_('Blank cell style'), self.combo_cell_blank_style)
        self.layout_wspacer5 = QtWidgets.QVBoxLayout()
        self.layout_wspacer5.addSpacing(20)
        self.layout_grid.addRow(self.layout_wspacer5)
        self.layout_grid.addRow(_('Filler cell color'), self.btn_cell_filler_bg_color)
        self.layout_grid.addRow(_('Filler cell style'), self.combo_cell_filler_style)
        self.layout_wspacer6 = QtWidgets.QVBoxLayout()
        self.layout_wspacer6.addSpacing(20)
        self.layout_grid.addRow(self.layout_wspacer6)
        self.layout_grid.addRow(_('Surrounding color'), self.btn_cell_filler2_bg_color)
        self.layout_grid.addRow(_('Surrounding style'), self.combo_cell_filler2_style)  
        
        self.widget_layout_grid = QtWidgets.QWidget()
        self.widget_layout_grid.setLayout(self.layout_grid)
        self.page_grid.setWidget(self.widget_layout_grid)
        self.stacked.addWidget(self.page_grid)

        # UI > Clues
        self.page_clues = QtWidgets.QScrollArea()
        self.page_clues.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.page_clues.setWidgetResizable(True)
        self.layout_clues = QtWidgets.QFormLayout()
        self.layout_clues.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)

        self.btn_clue_normal_bg_color = QtWidgets.QPushButton('')
        self.btn_clue_normal_bg_color.setStyleSheet('background-color: white;')
        self.btn_clue_normal_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_normal_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_clue_normal_style = QtWidgets.QComboBox()
        self.combo_clue_normal_style.addItems([_('Solid'), _('Dense'), _('Striped'), _('Lines'), _('Checkered'), _('Diag1'), _('Diag2'), _('Diag cross'), _('Gradient linear'), _('Gradient radial')])
        self.combo_clue_normal_style.setEditable(False)
        self.combo_clue_normal_style.setCurrentIndex(0)
        self.btn_clue_normal_fg_color = QtWidgets.QPushButton('')
        self.btn_clue_normal_fg_color.setStyleSheet('background-color: black;')
        self.btn_clue_normal_fg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_normal_fg_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_clue_normal_font = QtWidgets.QPushButton(_('Font...'))
        self.btn_clue_normal_font.setStyleSheet('font-family: "Arial"; font-size: 12pt; font-weight: bold')
        self.btn_clue_normal_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_normal_font.clicked.connect(self.on_font_btn_clicked)
        self.combo_clue_normal_alignment = QtWidgets.QComboBox()
        self.combo_clue_normal_alignment.addItems([_('Left'), _('Center'), _('Right')])
        self.combo_clue_normal_alignment.setEditable(False)
        self.combo_clue_normal_alignment.setCurrentIndex(0)

        self.btn_clue_incomplete_bg_color = QtWidgets.QPushButton('')
        self.btn_clue_incomplete_bg_color.setStyleSheet('background-color: magenta;')
        self.btn_clue_incomplete_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_incomplete_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_clue_incomplete_style = QtWidgets.QComboBox()
        self.combo_clue_incomplete_style.addItems([_('Solid'), _('Dense'), _('Striped'), _('Lines'), _('Checkered'), _('Diag1'), _('Diag2'), _('Diag cross'), _('Gradient linear'), _('Gradient radial')])
        self.combo_clue_incomplete_style.setEditable(False)
        self.combo_clue_incomplete_style.setCurrentIndex(0)
        self.btn_clue_incomplete_fg_color = QtWidgets.QPushButton('')
        self.btn_clue_incomplete_fg_color.setStyleSheet('background-color: black;')
        self.btn_clue_incomplete_fg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_incomplete_fg_color.clicked.connect(self.on_color_btn_clicked)

        self.btn_clue_complete_bg_color = QtWidgets.QPushButton('')
        self.btn_clue_complete_bg_color.setStyleSheet('background-color: green;')
        self.btn_clue_complete_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_complete_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_clue_complete_style = QtWidgets.QComboBox()
        self.combo_clue_complete_style.addItems([_('Solid'), _('Dense'), _('Striped'), _('Lines'), _('Checkered'), _('Diag1'), _('Diag2'), _('Diag cross'), _('Gradient linear'), _('Gradient radial')])
        self.combo_clue_complete_style.setEditable(False)
        self.combo_clue_complete_style.setCurrentIndex(0)
        self.btn_clue_complete_fg_color = QtWidgets.QPushButton('')
        self.btn_clue_complete_fg_color.setStyleSheet('background-color: black;')
        self.btn_clue_complete_fg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_complete_fg_color.clicked.connect(self.on_color_btn_clicked)

        self.btn_clue_surrounding_color = QtWidgets.QPushButton('')
        self.btn_clue_surrounding_color.setStyleSheet('background-color: white;')
        self.btn_clue_surrounding_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_surrounding_color.clicked.connect(self.on_color_btn_clicked)

        self.layout_clues.addRow(_('Font'), self.btn_clue_normal_font)
        self.layout_clues.addRow(_('Text alignment'), self.combo_clue_normal_alignment)

        self.layout_clues_wspacer1 = QtWidgets.QVBoxLayout()
        self.layout_clues_wspacer1.addSpacing(20)
        self.layout_clues.addRow(self.layout_clues_wspacer1)

        self.layout_clues.addRow(_('Normal color'), self.btn_clue_normal_bg_color)
        self.layout_clues.addRow(_('Normal style'), self.combo_clue_normal_style)
        self.layout_clues.addRow(_('Normal font color'), self.btn_clue_normal_fg_color)        
        self.layout_clues_wspacer2 = QtWidgets.QVBoxLayout()
        self.layout_clues_wspacer2.addSpacing(20)
        self.layout_clues.addRow(self.layout_clues_wspacer2)
        self.layout_clues.addRow(_('Incomplete color'), self.btn_clue_incomplete_bg_color)
        self.layout_clues.addRow(_('Incomplete style'), self.combo_clue_incomplete_style)
        self.layout_clues.addRow(_('Incomplete font color'), self.btn_clue_incomplete_fg_color)        
        self.layout_clues_wspacer3 = QtWidgets.QVBoxLayout()
        self.layout_clues_wspacer3.addSpacing(20)
        self.layout_clues.addRow(self.layout_clues_wspacer3)
        self.layout_clues.addRow(_('Complete color'), self.btn_clue_complete_bg_color)
        self.layout_clues.addRow(_('Complete style'), self.combo_clue_complete_style)
        self.layout_clues.addRow(_('Complete font color'), self.btn_clue_complete_fg_color) 
        self.layout_clues_wspacer31 = QtWidgets.QVBoxLayout()
        self.layout_clues_wspacer31.addSpacing(20)
        self.layout_clues.addRow(self.layout_clues_wspacer31)   
        self.layout_clues.addRow(_('Surrounding color'), self.btn_clue_surrounding_color)    

        self.layout_clues_wspacer4 = QtWidgets.QVBoxLayout()
        self.layout_clues_wspacer4.addSpacing(20)
        self.layout_clues.addRow(self.layout_clues_wspacer4)

        self.layout_clues_all = QtWidgets.QVBoxLayout()
        self.layout_clues_all.addLayout(self.layout_clues)

        self.gb_clues_cols = QtWidgets.QGroupBox(_('Columns'))
        self.layout_gb_clues_cols = QtWidgets.QHBoxLayout()
        self.lw_clues_cols = QtWidgets.QListWidget()
        self.lw_clues_cols.setToolTip(_('Check / uncheck items to show or hide columns, drag to reorder'))
        self.lw_clues_cols.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        #self.lw_clues_cols.setDragEnabled(True)
        #self.lw_clues_cols.setAcceptDrops(True)
        #self.lw_clues_cols.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        #self.lw_clues_cols.setDefaultDropAction(QtCore.Qt.MoveAction)
        #self.lw_clues_cols.setDropIndicatorShown(True)  
        self._fill_clue_cols()
        self.layout_gb_clues_cols.addWidget(self.lw_clues_cols)

        self.tb_clues_cols = QtWidgets.QToolBar()
        self.tb_clues_cols.setOrientation(QtCore.Qt.Vertical)
        self.act_cluecol_up = self.tb_clues_cols.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-l.png"), _('Up'))
        self.act_cluecol_up.triggered.connect(self.on_act_cluecol_up)
        self.act_cluecol_down = self.tb_clues_cols.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-r.png"), 
                                                            # NOTE: arrow button
                                                            _('Down'))
        self.act_cluecol_down.triggered.connect(self.on_act_cluecol_down)
        self.layout_gb_clues_cols.addWidget(self.tb_clues_cols)

        self.gb_clues_cols.setLayout(self.layout_gb_clues_cols)
        self.layout_clues_all.addWidget(self.gb_clues_cols)

        self.widget_layout_clues = QtWidgets.QWidget()
        self.widget_layout_clues.setLayout(self.layout_clues_all)
        self.page_clues.setWidget(self.widget_layout_clues)
        self.stacked.addWidget(self.page_clues)

        # UI > Toolbar
        self.page_toolbar = ToolbarCustomizer([v for k, v in self.mainwindow.__dict__.items() if k.startswith('act_')], self.mainwindow.toolbar_main)
        self.stacked.addWidget(self.page_toolbar)

        # Definition lookup
        self.page_lookup = QtWidgets.QScrollArea()
        self.page_lookup.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.page_lookup.setWidgetResizable(True)
        self.layout_lookup = QtWidgets.QVBoxLayout()
        self.layout_lookup.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)

        # def language
        self.layout_lookup_top = QtWidgets.QFormLayout()
        self.combo_lookup_deflang = QtWidgets.QComboBox()
        for k, v in LANG.items():
            self.combo_lookup_deflang.addItem(v, QtCore.QVariant(k))
        self.combo_lookup_deflang.setEditable(False)
        self.combo_lookup_deflang.setCurrentIndex(0)
        
        self.layout_lookup_top.addRow(_('Default language:'), self.combo_lookup_deflang)
        self.layout_lookup.addLayout(self.layout_lookup_top)

        # dictionaries
        self.gb_dics = QtWidgets.QGroupBox(_('Dictionaries'))
        self.layout_gb_dics = QtWidgets.QFormLayout()
        self.chb_dics_show = QtWidgets.QCheckBox('')
        self.chb_dics_exact = QtWidgets.QCheckBox('')
        self.chb_dics_showpos = QtWidgets.QCheckBox('')
        self.le_dics_badpos = QtWidgets.QLineEdit(_('UNKNOWN'))
        self.le_dics_apikey_mw = QtWidgets.QLineEdit('')
        self.le_dics_apikey_mw.setToolTip(_('Merriam-Webster Dictionary API key (empty string to use default)'))
        self.le_dics_apikey_yandex = QtWidgets.QLineEdit('')
        self.le_dics_apikey_yandex.setToolTip(_('Yandex Dictionary API key (empty string to use default)'))
        self.layout_gb_dics.addRow(_('Show:'), self.chb_dics_show)
        self.layout_gb_dics.addRow(_('Exact word match:'), self.chb_dics_exact)
        self.layout_gb_dics.addRow(_('Show parts of speech:'), self.chb_dics_showpos)
        self.layout_gb_dics.addRow(_('Unknown parts of speech:'), self.le_dics_badpos)
        self.layout_gb_dics.addRow(_('Merriam-Webster Dictionary API key:'), self.le_dics_apikey_mw)
        self.layout_gb_dics.addRow(_('Yandex Dictionary API key:'), self.le_dics_apikey_yandex)
        self.gb_dics.setLayout(self.layout_gb_dics)
        self.layout_lookup.addWidget(self.gb_dics)

        # google
        self.gb_google = QtWidgets.QGroupBox(_('Google Search'))
        self.layout_gb_google = QtWidgets.QFormLayout()
        self.chb_google_show = QtWidgets.QCheckBox('')
        self.chb_google_exact = QtWidgets.QCheckBox('')
        self.chb_google_safe = QtWidgets.QCheckBox('')
        self.le_google_filetypes = QtWidgets.QLineEdit('')
        self.le_google_filetypes.setToolTip(_('Add file types delimited by SPACE, e.g. "txt doc pdf"'))
        self.chb_google_lang_all = QtWidgets.QCheckBox(_('ALL'))
        self.chb_google_lang_all.setTristate(True)
        self.chb_google_lang_all.setCheckState(QtCore.Qt.Unchecked)
        self.chb_google_lang_all.stateChanged.connect(self.on_chb_google_lang_all) #
        self.lw_google_lang = QtWidgets.QListWidget()
        self.lw_google_lang.setToolTip(_('Search documents restricted only to checked languages'))
        d = GoogleSearch.get_document_languages()
        for l in d:
            lwitem = QtWidgets.QListWidgetItem(d[l])
            lwitem.setData(QtCore.Qt.StatusTipRole, l)
            lwitem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)            
            lwitem.setCheckState(QtCore.Qt.Unchecked)
            self.lw_google_lang.addItem(lwitem)
        self.lw_google_lang.itemChanged.connect(self.on_lw_google_lang_changed) #
        self.chb_google_interface_lang_all = QtWidgets.QCheckBox(_('ALL'))
        self.chb_google_interface_lang_all.setTristate(True)
        self.chb_google_interface_lang_all.setCheckState(QtCore.Qt.Unchecked)
        self.chb_google_interface_lang_all.stateChanged.connect(self.on_chb_google_interface_lang_all) #
        self.lw_google_interface_lang = QtWidgets.QListWidget()
        self.lw_google_interface_lang.setToolTip(_('Search using only checked interface languages'))
        d = GoogleSearch.get_interface_languages()
        for l in d:
            lwitem = QtWidgets.QListWidgetItem(d[l])
            lwitem.setData(QtCore.Qt.StatusTipRole, l)
            lwitem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)            
            lwitem.setCheckState(QtCore.Qt.Unchecked)
            self.lw_google_interface_lang.addItem(lwitem)
        self.lw_google_interface_lang.itemChanged.connect(self.on_lw_google_interface_lang_changed) #
        self.chb_google_geo_all = QtWidgets.QCheckBox(_('ALL'))
        self.chb_google_geo_all.setTristate(True)
        self.chb_google_geo_all.setCheckState(QtCore.Qt.Unchecked)
        self.chb_google_geo_all.stateChanged.connect(self.on_chb_google_geo_all) #
        self.lw_google_geo = QtWidgets.QListWidget()
        self.lw_google_geo.setToolTip(_('Search in checked locations only'))
        d = GoogleSearch.get_user_countries()
        for l in d:
            lwitem = QtWidgets.QListWidgetItem(d[l])
            lwitem.setData(QtCore.Qt.StatusTipRole, l)
            lwitem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)            
            lwitem.setCheckState(QtCore.Qt.Unchecked)
            self.lw_google_geo.addItem(lwitem)
        self.lw_google_geo.itemChanged.connect(self.on_lw_google_geo_changed) #
        self.le_google_linksite = QtWidgets.QLineEdit('')
        self.le_google_relatedsite = QtWidgets.QLineEdit('')
        self.le_google_insite = QtWidgets.QLineEdit('')
        self.spin_google_nresults = QtWidgets.QSpinBox()
        self.spin_google_nresults.setToolTip(_('Limit returned results for page (-1 = no limit)'))
        self.spin_google_nresults.setRange(-1, 10)
        self.spin_google_nresults.setValue(-1)
        self.le_google_apikey = QtWidgets.QLineEdit('')
        self.le_google_apikey.setToolTip(_('Google Custom Search API key (empty string to use default)'))
        self.le_google_cseid = QtWidgets.QLineEdit('')
        self.le_google_cseid.setToolTip(_('Google Custom Search CSE ID (empty string to use default)'))

        self.layout_gb_google.addRow(_('Show:'), self.chb_google_show)
        self.layout_gb_google.addRow(_('Exact phrase:'), self.chb_google_exact)
        self.layout_gb_google.addRow(_('File types:'), self.le_google_filetypes)
        self.layout_gb_google.addRow('', self.chb_google_lang_all)
        self.layout_gb_google.addRow(_('Document languages:'), self.lw_google_lang)
        self.layout_gb_google.addRow('', self.chb_google_interface_lang_all)
        self.layout_gb_google.addRow(_('Interface languages:'), self.lw_google_interface_lang)
        self.layout_gb_google.addRow('', self.chb_google_geo_all)
        self.layout_gb_google.addRow(_('Locations:'), self.lw_google_geo)
        self.layout_gb_google.addRow(_('Link site:'), self.le_google_linksite)
        self.layout_gb_google.addRow(_('Related (parent) site:'), self.le_google_relatedsite)
        self.layout_gb_google.addRow(_('Search in site:'), self.le_google_insite)
        self.layout_gb_google.addRow(_('Results per page:'), self.spin_google_nresults)
        self.layout_gb_google.addRow(_('Safe filter:'), self.chb_google_safe)
        self.layout_gb_google.addRow(_('Google Custom Search API key:'), self.le_google_apikey)
        self.layout_gb_google.addRow(_('Google Custom Search CSE ID:'), self.le_google_cseid)

        self.gb_google.setLayout(self.layout_gb_google)
        self.layout_lookup.addWidget(self.gb_google)

        self.widget_layout_lookup = QtWidgets.QWidget()
        self.widget_layout_lookup.setLayout(self.layout_lookup)
        self.page_lookup.setWidget(self.widget_layout_lookup)
        self.stacked.addWidget(self.page_lookup)

        # Import & Export
        self.page_importexport = QtWidgets.QWidget()
        self.layout_importexport = QtWidgets.QVBoxLayout()
        self.layout_importexport.setSpacing(10)

        self.gb_export = QtWidgets.QGroupBox(_('Export'))
        self.layout_gb_export = QtWidgets.QFormLayout()
        self.chb_export_openfile = QtWidgets.QCheckBox('')
        self.chb_export_clearcw = QtWidgets.QCheckBox('')
        self.spin_export_resolution_img = QtWidgets.QSpinBox()
        self.spin_export_resolution_img.setRange(0, 2400)
        self.spin_export_resolution_img.setSuffix(_(' dpi'))
        self.spin_export_resolution_pdf = QtWidgets.QSpinBox()
        self.spin_export_resolution_pdf.setRange(0, 2400)
        self.spin_export_resolution_pdf.setSuffix(_(' dpi'))
        self.spin_export_cellsize = QtWidgets.QSpinBox()
        self.spin_export_cellsize.setRange(2, 100)
        self.spin_export_cellsize.setSuffix(_(' mm'))
        self.spin_export_quality = QtWidgets.QSpinBox()
        self.spin_export_quality.setRange(-1, 100)
        self.spin_export_quality.setSuffix(' %')
        self.spin_export_quality.setToolTip(_('Quality in percent (set to -1 for auto quality)'))
        self.btn_export_auto_resolution_img = QtWidgets.QPushButton(_('Auto'))
        self.btn_export_auto_resolution_img.clicked.connect(self.on_btn_export_auto_resolution_img)
        self.btn_export_auto_resolution_pdf = QtWidgets.QPushButton(_('Auto'))
        self.btn_export_auto_resolution_pdf.clicked.connect(self.on_btn_export_auto_resolution_pdf)
        self.layout_export_resolution_img = QtWidgets.QHBoxLayout()
        self.layout_export_resolution_img.addWidget(self.spin_export_resolution_img)
        self.layout_export_resolution_img.addWidget(self.btn_export_auto_resolution_img)
        self.layout_export_resolution_pdf = QtWidgets.QHBoxLayout()
        self.layout_export_resolution_pdf.addWidget(self.spin_export_resolution_pdf)
        self.layout_export_resolution_pdf.addWidget(self.btn_export_auto_resolution_pdf)
        self.le_svg_title = QtWidgets.QLineEdit()
        self.le_svg_description = QtWidgets.QLineEdit()
        self.layout_gb_export.addRow(_('Image resolution'), self.layout_export_resolution_img)
        self.layout_gb_export.addRow(_('PDF resolution'), self.layout_export_resolution_pdf)
        self.layout_gb_export.addRow(_('Image quality'), self.spin_export_quality)
        self.layout_gb_export.addRow(_('Output grid cell size'), self.spin_export_cellsize)
        self.layout_gb_export.addRow(_('SVG image title'), self.le_svg_title)
        self.layout_gb_export.addRow(_('SVG image description'), self.le_svg_description)
        self.layout_gb_export.addRow(_('Clear crossword before export'), self.chb_export_clearcw)
        self.layout_gb_export.addRow(_('Open exported file'), self.chb_export_openfile)
        self.gb_export.setLayout(self.layout_gb_export)
        self.layout_importexport.addWidget(self.gb_export)

        self.page_importexport.setLayout(self.layout_importexport)
        self.stacked.addWidget(self.page_importexport)

        # Plugins > Third-party
        self.page_plugins_3party = QtWidgets.QWidget()
        self.layout_plugins_3party = QtWidgets.QVBoxLayout()

        self.tv_plugins_3party = QtWidgets.QTreeView()

        self.model_plugins_3party = QtGui.QStandardItemModel(0, 2)
        self.model_plugins_3party.setHorizontalHeaderLabels([_('Plugin'), _('Value')])
        self.model_plugins_3party.itemChanged.connect(self.on_model_plugins_3party_changed)

        item_git = QtGui.QStandardItem(QtGui.QIcon(f"{ICONFOLDER}/git.png"), 'Git')
        item_git.setFlags(QtCore.Qt.ItemIsEnabled)
        item_1 = QtGui.QStandardItem(_('Enabled'))
        item_1.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2 = QtGui.QStandardItem('')
        item_2.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2.setCheckable(True)
        item_2.setUserTristate(False)
        item_2.setCheckState(QtCore.Qt.Checked)
        item_git.appendRow([item_1, item_2])
        item_1 = QtGui.QStandardItem(_('Path'))
        item_1.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2 = QtGui.QStandardItem('')
        item_2.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        item_git.appendRow([item_1, item_2])
        item_0 = QtGui.QStandardItem()
        item_0.setFlags(QtCore.Qt.NoItemFlags)
        self.model_plugins_3party.appendRow([item_git, item_0])
        
        item_sqlite = QtGui.QStandardItem(QtGui.QIcon(f"{ICONFOLDER}/sqlite.png"), _('SQLite Editor'))
        item_sqlite.setFlags(QtCore.Qt.ItemIsEnabled)
        item_1 = QtGui.QStandardItem(_('Enabled'))
        item_1.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2 = QtGui.QStandardItem('')
        item_2.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2.setCheckable(True)
        item_2.setUserTristate(False)
        item_2.setCheckState(QtCore.Qt.Checked)
        item_sqlite.appendRow([item_1, item_2])
        item_1 = QtGui.QStandardItem(_('Path'))
        item_1.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2 = QtGui.QStandardItem('')
        item_2.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        item_sqlite.appendRow([item_1, item_2])
        item_1 = QtGui.QStandardItem(_('Commands'))
        item_1.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2 = QtGui.QStandardItem('<file>')
        item_2.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        item_sqlite.appendRow([item_1, item_2])
        item_0 = QtGui.QStandardItem()
        item_0.setFlags(QtCore.Qt.NoItemFlags)
        self.model_plugins_3party.appendRow([item_sqlite, item_0])

        item_text = QtGui.QStandardItem(QtGui.QIcon(f"{ICONFOLDER}/file.png"), _('Text Editor'))
        item_text.setFlags(QtCore.Qt.ItemIsEnabled)
        item_1 = QtGui.QStandardItem(_('Enabled'))
        item_1.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2 = QtGui.QStandardItem('')
        item_2.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2.setCheckable(True)
        item_2.setUserTristate(False)
        item_2.setCheckState(QtCore.Qt.Checked)
        item_text.appendRow([item_1, item_2])
        item_1 = QtGui.QStandardItem(_('Path'))
        item_1.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2 = QtGui.QStandardItem('')
        item_2.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        item_text.appendRow([item_1, item_2])
        item_1 = QtGui.QStandardItem(_('Commands'))
        item_1.setFlags(QtCore.Qt.ItemIsEnabled)
        item_2 = QtGui.QStandardItem('<file>')
        item_2.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        item_text.appendRow([item_1, item_2])
        item_0 = QtGui.QStandardItem()
        item_0.setFlags(QtCore.Qt.NoItemFlags)
        self.model_plugins_3party.appendRow([item_text, item_0])

        self.tv_plugins_3party.setModel(self.model_plugins_3party)
        
        indices = []
        indices.append(self.model_plugins_3party.index(1, 1, 
                self.model_plugins_3party.indexFromItem(item_git)))
        indices.append(self.model_plugins_3party.index(1, 1, 
                self.model_plugins_3party.indexFromItem(item_sqlite)))
        indices.append(self.model_plugins_3party.index(1, 1, 
                self.model_plugins_3party.indexFromItem(item_text)))
        self.tv_plugins_3party.setItemDelegate(BrowseEditDelegate(indices))

        self.tv_plugins_3party.show()
        self.tv_plugins_3party.expandAll()
        self.layout_plugins_3party.addWidget(self.tv_plugins_3party)

        self.page_plugins_3party.setLayout(self.layout_plugins_3party)
        self.stacked.addWidget(self.page_plugins_3party)

        # Plugins > Custom
        self.page_plugins_custom = CustomPluginManager(self.mainwindow)
        self.stacked.addWidget(self.page_plugins_custom)

        # Printing
        self.page_printing = QtWidgets.QScrollArea()
        self.page_printing.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.page_printing.setWidgetResizable(True)
        self.layout_printing = QtWidgets.QVBoxLayout()
        self.layout_printing.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.layout_printing.setSpacing(10)

        self.layout_combo_print_layout = QtWidgets.QFormLayout()
        self.combo_print_layout = QtWidgets.QComboBox()
        self.combo_print_layout.addItems([_('Auto'), _('Portrait'), _('Landscape')])
        self.combo_print_layout.setEditable(False)
        self.le_print_title = QtWidgets.QLineEdit('<title>')
        self.le_print_clues_title = QtWidgets.QLineEdit(_('Clues'))

        self.layout_combo_print_layout.addRow(_('Page layout'), self.combo_print_layout)
        self.layout_combo_print_layout.addRow(_('Crossword title'), self.le_print_title)
        self.layout_combo_print_layout.addRow(_('Clues title (header)'), self.le_print_clues_title)

        self.gb_print_margins = QtWidgets.QGroupBox(_('Margins'))
        self.layout_gb_print_margins = QtWidgets.QFormLayout()
        self.spin_margin_left = QtWidgets.QSpinBox()
        self.spin_margin_left.setRange(0, 50)
        self.spin_margin_left.setSuffix(_(' mm'))
        self.spin_margin_right = QtWidgets.QSpinBox()
        self.spin_margin_right.setRange(0, 50)
        self.spin_margin_right.setSuffix(_(' mm'))
        self.spin_margin_top = QtWidgets.QSpinBox()
        self.spin_margin_top.setRange(0, 100)
        self.spin_margin_top.setSuffix(_(' mm'))
        self.spin_margin_bottom = QtWidgets.QSpinBox()
        self.spin_margin_bottom.setRange(0, 100)
        self.spin_margin_bottom.setSuffix(_(' mm'))
        self.layout_gb_print_margins.addRow(_('Left'), self.spin_margin_left)
        self.layout_gb_print_margins.addRow(_('Right'), self.spin_margin_right)
        self.layout_gb_print_margins.addRow(_('Top'), self.spin_margin_top)
        self.layout_gb_print_margins.addRow(_('Bottom'), self.spin_margin_bottom)
        self.gb_print_margins.setLayout(self.layout_gb_print_margins)
        self.chb_print_font_embed = QtWidgets.QCheckBox(_('Embed fonts'))
        self.chb_print_antialias = QtWidgets.QCheckBox(_('Antialiasing'))
        self.chb_print_print_cw = QtWidgets.QCheckBox(_('Print crossword grid'))
        self.chb_print_print_clues = QtWidgets.QCheckBox(_('Print clues'))
        self.chb_print_clear_cw = QtWidgets.QCheckBox(_('Empty grid'))
        self.chb_print_print_cw.toggled.connect(self.chb_print_clear_cw.setEnabled)
        self.chb_print_print_clue_letters = QtWidgets.QCheckBox(_('Include word size hint'))
        self.chb_print_print_clues.toggled.connect(self.chb_print_print_clue_letters.setEnabled)
        self.chb_print_print_info = QtWidgets.QCheckBox(_('Print crossword information'))
        self.chb_print_color_print = QtWidgets.QCheckBox(_('Colored output'))        
        self.chb_print_openfile = QtWidgets.QCheckBox(_('Open file (PDF) on print complete'))        

        self.gb_print_fonts = QtWidgets.QGroupBox(_('Fonts'))
        self.layout_gb_print_fonts = QtWidgets.QFormLayout()

        self.btn_print_header_color = QtWidgets.QPushButton('')
        self.btn_print_header_color.setStyleSheet('background-color: blue;')
        self.btn_print_header_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_header_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_print_header_font = QtWidgets.QPushButton(_('Font...'))
        self.btn_print_header_font.setStyleSheet('font-family: "Verdana"; font-size: 20pt; font-weight: bold;')
        self.btn_print_header_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_header_font.clicked.connect(self.on_font_btn_clicked)

        self.btn_print_info_color = QtWidgets.QPushButton('')
        self.btn_print_info_color.setStyleSheet('background-color: blue;')
        self.btn_print_info_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_info_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_print_info_font = QtWidgets.QPushButton(_('Font...'))
        self.btn_print_info_font.setStyleSheet('font-family: "Verdana"; font-size: 20pt; font-weight: bold;')
        self.btn_print_info_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_info_font.clicked.connect(self.on_font_btn_clicked)

        self.btn_print_clue_number_color = QtWidgets.QPushButton('')
        self.btn_print_clue_number_color.setStyleSheet('background-color: blue;')
        self.btn_print_clue_number_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_number_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_print_clue_number_font = QtWidgets.QPushButton(_('Font...'))
        self.btn_print_clue_number_font.setStyleSheet('font-family: "Verdana"; font-size: 20pt; font-weight: bold;')
        self.btn_print_clue_number_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_number_font.clicked.connect(self.on_font_btn_clicked)

        self.btn_print_clue_text_color = QtWidgets.QPushButton('')
        self.btn_print_clue_text_color.setStyleSheet('background-color: blue;')
        self.btn_print_clue_text_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_text_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_print_clue_text_font = QtWidgets.QPushButton(_('Font...'))
        self.btn_print_clue_text_font.setStyleSheet('font-family: "Verdana"; font-size: 20pt; font-weight: bold;')
        self.btn_print_clue_text_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_text_font.clicked.connect(self.on_font_btn_clicked)

        self.btn_print_clue_sizehint_color = QtWidgets.QPushButton('')
        self.btn_print_clue_sizehint_color.setStyleSheet('background-color: blue;')
        self.btn_print_clue_sizehint_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_sizehint_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_print_clue_sizehint_font = QtWidgets.QPushButton(_('Font...'))
        self.btn_print_clue_sizehint_font.setStyleSheet('font-family: "Verdana"; font-size: 20pt; font-weight: bold;')
        self.btn_print_clue_sizehint_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_sizehint_font.clicked.connect(self.on_font_btn_clicked)

        self.layout_gb_print_fonts.addRow(_('Title color'), self.btn_print_header_color)
        self.layout_gb_print_fonts.addRow(_('Title font'), self.btn_print_header_font)
        self.layout_gb_print_fonts.addRow(_('Info color'), self.btn_print_info_color)
        self.layout_gb_print_fonts.addRow(_('Info font'), self.btn_print_info_font)
        self.layout_gb_print_fonts.addRow(_('Clues color'), self.btn_print_clue_text_color)
        self.layout_gb_print_fonts.addRow(_('Clues font'), self.btn_print_clue_text_font)
        self.layout_gb_print_fonts.addRow(_('Word number color'), self.btn_print_clue_number_color)
        self.layout_gb_print_fonts.addRow(_('Word number font'), self.btn_print_clue_number_font)
        self.layout_gb_print_fonts.addRow(_('Word size hint color'), self.btn_print_clue_sizehint_color)
        self.layout_gb_print_fonts.addRow(_('Word size hint font'), self.btn_print_clue_sizehint_font)
        self.gb_print_fonts.setLayout(self.layout_gb_print_fonts)

        self.layout_printing.addLayout(self.layout_combo_print_layout)
        self.layout_printing.addWidget(self.gb_print_margins)
        self.layout_printing.addWidget(self.chb_print_print_cw)
        self.layout_printing.addWidget(self.chb_print_clear_cw)
        self.layout_printing.addWidget(self.chb_print_print_clues)
        self.layout_printing.addWidget(self.chb_print_print_clue_letters)
        self.layout_printing.addWidget(self.chb_print_print_info)
        self.layout_printing.addWidget(self.chb_print_color_print)
        self.layout_printing.addWidget(self.chb_print_font_embed)
        self.layout_printing.addWidget(self.chb_print_antialias)
        self.layout_printing.addWidget(self.chb_print_openfile)
        self.layout_printing.addWidget(self.gb_print_fonts)

        self.widget_layout_printing = QtWidgets.QWidget()
        self.widget_layout_printing.setLayout(self.layout_printing)
        self.page_printing.setWidget(self.widget_layout_printing)
        self.stacked.addWidget(self.page_printing)

        # Updating
        self.page_updating = QtWidgets.QWidget()
        self.layout_updating = QtWidgets.QFormLayout()
        self.layout_updating.setSpacing(10)

        self.spin_update_period = QtWidgets.QSpinBox()
        self.spin_update_period.setRange(-1, 365)
        self.spin_update_period.setSuffix(_(' days'))
        self.spin_update_period.setToolTip(_('Set to -1 to disable update checks'))
        self.chb_update_auto = QtWidgets.QCheckBox('')
        self.chb_update_major_only = QtWidgets.QCheckBox('')
        self.chb_update_restart = QtWidgets.QCheckBox('')       
        
        self.le_update_logfile = BrowseEdit(dialogtype='filesave', fullpath=False)
        self.le_update_logfile.setToolTip(_('Log file for update operations'))
        
        self.layout_updating.addRow(_('Check for updates every'), self.spin_update_period)
        self.layout_updating.addRow(_('Check / update major releases only'), self.chb_update_major_only)
        self.layout_updating.addRow(_('Auto update'), self.chb_update_auto)
        self.layout_updating.addRow(_('Restart on update'), self.chb_update_restart)
        self.layout_updating.addRow(_('Log file'), self.le_update_logfile)

        self.page_updating.setLayout(self.layout_updating)
        self.stacked.addWidget(self.page_updating)

        # Sharing
        self.page_sharing = QtWidgets.QWidget()
        self.layout_sharing = QtWidgets.QFormLayout()
        self.layout_sharing.setSpacing(10)

        self.le_sharing_account = QtWidgets.QLineEdit('')
        self.le_sharing_account.setToolTip(_('Kloudless account ID (leave EMPTY for default)'))
        self.le_sharing_token = QtWidgets.QLineEdit('')
        self.le_sharing_token.setToolTip(_('Kloudless Bearer Token (leave EMPTY for default)'))
        self.le_sharing_root = QtWidgets.QLineEdit('')
        self.le_sharing_root.setToolTip(_('Kloudless root folder (leave EMPTY for default)'))
        self.le_sharing_user = QtWidgets.QLineEdit('')
        self.le_sharing_user.setToolTip(_('Kloudless username (leave EMPTY to create new user automatically)'))
        self.chb_sharing_use_api_key = QtWidgets.QCheckBox('')
        self.chb_sharing_use_api_key.setToolTip(_('Check this to use one single API key for authentication (WARNING! NOT SAFE!)'))
        self.chb_sharing_ownbrowser = QtWidgets.QCheckBox('')
        self.chb_sharing_ownbrowser.setToolTip(_('Use app inbuilt browser to open share links (otherwise, use system browser)'))

        self.layout_sharing.addRow(_('Kloudless account ID'), self.le_sharing_account)
        self.layout_sharing.addRow(_('Kloudless Bearer Token'), self.le_sharing_token)
        self.layout_sharing.addRow(_('Kloudless root folder'), self.le_sharing_root)
        self.layout_sharing.addRow(_('Kloudless username'), self.le_sharing_user)
        self.layout_sharing.addRow(_('Use API key'), self.chb_sharing_use_api_key)
        self.layout_sharing.addRow(_('Use inbuilt browser'), self.chb_sharing_ownbrowser)

        self.page_sharing.setLayout(self.layout_sharing)
        self.stacked.addWidget(self.page_sharing)

    ## Shortcut method to update the list of Clues column names.
    def _fill_clue_cols(self):
        self.lw_clues_cols.clear()
        for col in CWSettings.settings['clues']['columns']:
            lwitem = QtWidgets.QListWidgetItem(col['name'])
            if col['name'] == _('Direction'):
                lwitem.setFlags(QtCore.Qt.NoItemFlags)
                lwitem.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.red), QtCore.Qt.SolidPattern))
            else:
                lwitem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled)                
            lwitem.setCheckState(QtCore.Qt.Checked if col['visible'] else QtCore.Qt.Unchecked)
            self.lw_clues_cols.addItem(lwitem)

    ## Outputs collected settings in CWSettings.settings format and returns the resulting dictionary.
    # @warning The method doesn't update guisettings::CWSettings::settings automatically!
    # @returns `dict` dictionary with global settings collected from the dialog
    def to_settings(self):
        settings = {key: {} for key in CWSettings.settings}

        # common
        settings['common']['temp_dir'] = self.le_tempdir.text()
        settings['common']['autosave_cw'] = self.chb_autosave_cw.isChecked()
        settings['common']['web'] = {}
        settings['common']['web']['req_timeout'] = self.spin_req_timeout.value()
        settings['common']['web']['proxy'] = {}
        settings['common']['web']['proxy']['use_system'] = self.chb_system_proxy.isChecked()
        settings['common']['web']['proxy']['http'] = self.le_http_proxy.text()
        settings['common']['web']['proxy']['https'] = self.le_https_proxy.text()
        settings['common']['lang'] = self.mainwindow.combo_lang.currentData()

        # user interface
        settings['gui']['theme'] = self.combo_apptheme.currentText()
        settings['gui']['toolbar_pos'] = self.combo_toolbarpos.currentIndex()
        settings['gui']['win_pos'] = (self.mainwindow.pos().x(), self.mainwindow.pos().y())
        settings['gui']['win_size'] = (self.mainwindow.width(), self.mainwindow.height())
        settings['gui']['toolbar_actions'] = self.page_toolbar.to_list()

        # timeout
        settings['cw_settings']['timeout'] = self.spin_gen_timeout.value()
        
        # method
        method = self.combo_gen_method.currentIndex()
        if method == 0:
            settings['cw_settings']['method'] = None
        elif method == 1:
            settings['cw_settings']['method'] = 'iter'
        else:
            settings['cw_settings']['method'] = 'recurse'
            
        # pos
        pos = []
        for row in range(self.lw_pos.count()):
            it = self.lw_pos.item(row)
            if not it.checkState(): continue
            for p in POS:
                if p[1] == it.text():
                    pos.append(p[0])
                    break
        if len(pos) == 1: pos = pos[0]
        settings['cw_settings']['pos'] = pos
        
        # log
        log = self.combo_log.currentText()
        if log == _('No log'):
            settings['cw_settings']['log'] = None
        elif log == _('Console'):
            settings['cw_settings']['log'] = 'stdout'
        else:
            settings['cw_settings']['log'] = log
            
        # wordsrc
        settings['wordsrc']['maxres'] = self.spin_maxfetch.value() if self.chb_maxfetch.isChecked() else None
        settings['wordsrc']['sources'] = []        
        for row in reversed(range(self.lw_sources.count())):
            item = self.lw_sources.item(row)
            src = json.loads(item.data(QtCore.Qt.UserRole))
            src['active'] = (item.checkState() == QtCore.Qt.Checked)
            if not src or not isinstance(src, dict):
                print(_('No user data in src!'))
                continue
            settings['wordsrc']['sources'].append(src)
            
        # excluded
        settings['wordsrc']['excluded'] = {}
        excl = self.te_excluded.toPlainText().strip().split('\n')
        settings['wordsrc']['excluded']['words'] = excl if excl and excl[0] else []
        settings['wordsrc']['excluded']['regex'] = self.chb_excl_regex.isChecked()
        
        # grid_style
        settings['grid_style']['scale'] = self.spin_cwscale.value()
        settings['grid_style']['show'] = self.chb_showgrid.isChecked()
        settings['grid_style']['line'] = QtCore.Qt.SolidLine
        color = color_from_stylesheet(self.btn_gridlinecolor.styleSheet(), 'background-color', 'gray')
        settings['grid_style']['line_color'] = color.rgba()        
        index = self.combo_gridlinestyle.currentIndex()
        if index == 1:
            settings['grid_style']['line'] = QtCore.Qt.DashLine
        elif index == 2:
            settings['grid_style']['line'] = QtCore.Qt.DotLine
        elif index == 3:
            settings['grid_style']['line'] = QtCore.Qt.DashDotLine
        settings['grid_style']['line_width'] = self.spin_gridlinesz.value()
        color = color_from_stylesheet(self.btn_activecellcolor.styleSheet(), 'background-color', 'blue')
        settings['grid_style']['active_cell_color'] = color.rgba()    
        settings['grid_style']['header'] = self.chb_showcoords.isChecked()
        settings['grid_style']['cell_size'] = self.spin_cellsz.value()
        settings['grid_style']['numbers'] = {}
        settings['grid_style']['numbers']['show'] = self.chb_shownumbers.isChecked()
        color = color_from_stylesheet(self.btn_numberscolor.styleSheet(), 'background-color', 'gray')
        settings['grid_style']['numbers']['color'] = color.rgba()
        font = make_font('Arial', 8, QtGui.QFont.DemiBold)
        font = font_from_stylesheet(self.btn_numbersfont.styleSheet(), 'pt', font)
        settings['grid_style']['numbers']['font_size'] = font.pointSize()
        settings['grid_style']['numbers']['font_name'] = font.family()
        settings['grid_style']['numbers']['font_weight'] = font.weight()
        settings['grid_style']['numbers']['font_italic'] = font.italic() 
        index = self.combo_charcase.currentIndex()
        if index == 0:
            settings['grid_style']['char_case'] = 'upper'
        else:
            settings['grid_style']['char_case'] = 'lower'
        # cell_format
        settings['cell_format']['NORMAL'] = {}
        color = color_from_stylesheet(self.btn_cell_normal_bg_color.styleSheet(), 'background-color', 'white')
        settings['cell_format']['NORMAL']['bg_color'] = color.rgba()
        settings['cell_format']['NORMAL']['bg_pattern'] = QtCore.Qt.SolidPattern
        index = self.combo_cell_normal_style.currentIndex()
        if index == 1:
            settings['cell_format']['NORMAL']['bg_pattern'] = QtCore.Qt.Dense6Pattern
        elif index == 2:
            settings['cell_format']['NORMAL']['bg_pattern'] = QtCore.Qt.HorPattern
        elif index == 3:
            settings['cell_format']['NORMAL']['bg_pattern'] = QtCore.Qt.VerPattern
        elif index == 4:
            settings['cell_format']['NORMAL']['bg_pattern'] = QtCore.Qt.CrossPattern
        elif index == 5:
            settings['cell_format']['NORMAL']['bg_pattern'] = QtCore.Qt.BDiagPattern
        elif index == 6:
            settings['cell_format']['NORMAL']['bg_pattern'] = QtCore.Qt.FDiagPattern
        elif index == 7:
            settings['cell_format']['NORMAL']['bg_pattern'] = QtCore.Qt.DiagCrossPattern
        elif index == 8:
            settings['cell_format']['NORMAL']['bg_pattern'] = QtCore.Qt.LinearGradientPattern
        elif index == 9:
            settings['cell_format']['NORMAL']['bg_pattern'] = QtCore.Qt.RadialGradientPattern
        color = color_from_stylesheet(self.btn_cell_normal_fg_color.styleSheet(), 'background-color', 'black')
        settings['cell_format']['NORMAL']['fg_color'] = color.rgba()
        settings['cell_format']['NORMAL']['fg_pattern'] = QtCore.Qt.SolidPattern
        settings['cell_format']['NORMAL']['flags'] = int(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        font = make_font('Arial', 18, QtGui.QFont.DemiBold)
        font = font_from_stylesheet(self.btn_cell_normal_font.styleSheet(), 'pt', font)
        settings['cell_format']['NORMAL']['font_size'] = font.pointSize()
        settings['cell_format']['NORMAL']['font_name'] = font.family()
        settings['cell_format']['NORMAL']['font_weight'] = font.weight()
        settings['cell_format']['NORMAL']['font_italic'] = font.italic()
        settings['cell_format']['NORMAL']['align'] = QtCore.Qt.AlignCenter
        
        settings['cell_format']['HILITE'] = {}
        color = color_from_stylesheet(self.btn_cell_hilite_bg_color.styleSheet(), 'background-color', 'yellow')
        settings['cell_format']['HILITE']['bg_color'] = color.rgba()
        settings['cell_format']['HILITE']['bg_pattern'] = QtCore.Qt.SolidPattern
        index = self.combo_cell_hilite_style.currentIndex()
        if index == 1:
            settings['cell_format']['HILITE']['bg_pattern'] = QtCore.Qt.Dense6Pattern
        elif index == 2:
            settings['cell_format']['HILITE']['bg_pattern'] = QtCore.Qt.HorPattern
        elif index == 3:
            settings['cell_format']['HILITE']['bg_pattern'] = QtCore.Qt.VerPattern
        elif index == 4:
            settings['cell_format']['HILITE']['bg_pattern'] = QtCore.Qt.CrossPattern
        elif index == 5:
            settings['cell_format']['HILITE']['bg_pattern'] = QtCore.Qt.BDiagPattern
        elif index == 6:
            settings['cell_format']['HILITE']['bg_pattern'] = QtCore.Qt.FDiagPattern
        elif index == 7:
            settings['cell_format']['HILITE']['bg_pattern'] = QtCore.Qt.DiagCrossPattern
        elif index == 8:
            settings['cell_format']['HILITE']['bg_pattern'] = QtCore.Qt.LinearGradientPattern
        elif index == 9:
            settings['cell_format']['HILITE']['bg_pattern'] = QtCore.Qt.RadialGradientPattern
        color = color_from_stylesheet(self.btn_cell_hilite_fg_color.styleSheet(), 'background-color', 'black')
        settings['cell_format']['HILITE']['fg_color'] = color.rgba()
        settings['cell_format']['HILITE']['fg_pattern'] = QtCore.Qt.SolidPattern
        settings['cell_format']['HILITE']['flags'] = int(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        font = make_font('Arial', 18, QtGui.QFont.DemiBold)
        font = font_from_stylesheet(self.btn_cell_hilite_font.styleSheet(), 'pt', font)
        settings['cell_format']['HILITE']['font_size'] = font.pointSize()
        settings['cell_format']['HILITE']['font_name'] = font.family()
        settings['cell_format']['HILITE']['font_weight'] = font.weight()
        settings['cell_format']['HILITE']['font_italic'] = font.italic()
        settings['cell_format']['HILITE']['align'] = settings['cell_format']['NORMAL']['align']
        
        settings['cell_format']['BLANK'] = {}
        color = color_from_stylesheet(self.btn_cell_blank_bg_color.styleSheet(), 'background-color', 'white')
        settings['cell_format']['BLANK']['bg_color'] = color.rgba()
        settings['cell_format']['BLANK']['bg_pattern'] = QtCore.Qt.SolidPattern
        index = self.combo_cell_blank_style.currentIndex()
        if index == 1:
            settings['cell_format']['BLANK']['bg_pattern'] = QtCore.Qt.Dense6Pattern
        elif index == 2:
            settings['cell_format']['BLANK']['bg_pattern'] = QtCore.Qt.HorPattern
        elif index == 3:
            settings['cell_format']['BLANK']['bg_pattern'] = QtCore.Qt.VerPattern
        elif index == 4:
            settings['cell_format']['BLANK']['bg_pattern'] = QtCore.Qt.CrossPattern
        elif index == 5:
            settings['cell_format']['BLANK']['bg_pattern'] = QtCore.Qt.BDiagPattern
        elif index == 6:
            settings['cell_format']['BLANK']['bg_pattern'] = QtCore.Qt.FDiagPattern
        elif index == 7:
            settings['cell_format']['BLANK']['bg_pattern'] = QtCore.Qt.DiagCrossPattern
        elif index == 8:
            settings['cell_format']['BLANK']['bg_pattern'] = QtCore.Qt.LinearGradientPattern
        elif index == 9:
            settings['cell_format']['BLANK']['bg_pattern'] = QtCore.Qt.RadialGradientPattern
        settings['cell_format']['BLANK']['fg_color'] = settings['cell_format']['NORMAL']['fg_color']
        settings['cell_format']['BLANK']['fg_pattern'] = settings['cell_format']['NORMAL']['fg_pattern']
        settings['cell_format']['BLANK']['flags'] = settings['cell_format']['NORMAL']['flags']
        settings['cell_format']['BLANK']['font_size'] = settings['cell_format']['NORMAL']['font_size']
        settings['cell_format']['BLANK']['font_name'] = settings['cell_format']['NORMAL']['font_name']
        settings['cell_format']['BLANK']['font_weight'] = settings['cell_format']['NORMAL']['font_weight']
        settings['cell_format']['BLANK']['font_italic'] = settings['cell_format']['NORMAL']['font_italic']
        settings['cell_format']['BLANK']['align'] = settings['cell_format']['NORMAL']['align']
        
        settings['cell_format']['FILLER'] = {}
        color = color_from_stylesheet(self.btn_cell_filler_bg_color.styleSheet(), 'background-color', 'black')
        settings['cell_format']['FILLER']['bg_color'] = color.rgba()
        settings['cell_format']['FILLER']['bg_pattern'] = QtCore.Qt.SolidPattern
        index = self.combo_cell_filler_style.currentIndex()
        if index == 1:
            settings['cell_format']['FILLER']['bg_pattern'] = QtCore.Qt.Dense6Pattern
        elif index == 2:
            settings['cell_format']['FILLER']['bg_pattern'] = QtCore.Qt.HorPattern
        elif index == 3:
            settings['cell_format']['FILLER']['bg_pattern'] = QtCore.Qt.VerPattern
        elif index == 4:
            settings['cell_format']['FILLER']['bg_pattern'] = QtCore.Qt.CrossPattern
        elif index == 5:
            settings['cell_format']['FILLER']['bg_pattern'] = QtCore.Qt.BDiagPattern
        elif index == 6:
            settings['cell_format']['FILLER']['bg_pattern'] = QtCore.Qt.FDiagPattern
        elif index == 7:
            settings['cell_format']['FILLER']['bg_pattern'] = QtCore.Qt.DiagCrossPattern
        elif index == 8:
            settings['cell_format']['FILLER']['bg_pattern'] = QtCore.Qt.LinearGradientPattern
        elif index == 9:
            settings['cell_format']['FILLER']['bg_pattern'] = QtCore.Qt.RadialGradientPattern
        settings['cell_format']['FILLER']['fg_color'] = QtGui.QColor(QtCore.Qt.transparent).rgba()
        settings['cell_format']['FILLER']['fg_pattern'] = QtCore.Qt.SolidPattern
        settings['cell_format']['FILLER']['flags'] = int(QtCore.Qt.NoItemFlags)
        settings['cell_format']['FILLER']['font_size'] = settings['cell_format']['NORMAL']['font_size']
        settings['cell_format']['FILLER']['font_name'] = settings['cell_format']['NORMAL']['font_name']
        settings['cell_format']['FILLER']['font_weight'] = settings['cell_format']['NORMAL']['font_weight']
        settings['cell_format']['FILLER']['font_italic'] = settings['cell_format']['NORMAL']['font_italic']
        settings['cell_format']['FILLER']['align'] = settings['cell_format']['NORMAL']['align']
        
        settings['cell_format']['FILLER2'] = {}
        color = color_from_stylesheet(self.btn_cell_filler2_bg_color.styleSheet(), 'background-color', 'gray')
        settings['cell_format']['FILLER2']['bg_color'] = color.rgba()
        settings['cell_format']['FILLER2']['bg_pattern'] = QtCore.Qt.SolidPattern
        index = self.combo_cell_filler2_style.currentIndex()
        if index == 1:
            settings['cell_format']['FILLER2']['bg_pattern'] = QtCore.Qt.Dense6Pattern
        elif index == 2:
            settings['cell_format']['FILLER2']['bg_pattern'] = QtCore.Qt.HorPattern
        elif index == 3:
            settings['cell_format']['FILLER2']['bg_pattern'] = QtCore.Qt.VerPattern
        elif index == 4:
            settings['cell_format']['FILLER2']['bg_pattern'] = QtCore.Qt.CrossPattern
        elif index == 5:
            settings['cell_format']['FILLER2']['bg_pattern'] = QtCore.Qt.BDiagPattern
        elif index == 6:
            settings['cell_format']['FILLER2']['bg_pattern'] = QtCore.Qt.FDiagPattern
        elif index == 7:
            settings['cell_format']['FILLER2']['bg_pattern'] = QtCore.Qt.DiagCrossPattern
        elif index == 8:
            settings['cell_format']['FILLER2']['bg_pattern'] = QtCore.Qt.LinearGradientPattern
        elif index == 9:
            settings['cell_format']['FILLER2']['bg_pattern'] = QtCore.Qt.RadialGradientPattern
        settings['cell_format']['FILLER2']['fg_color'] = QtGui.QColor(QtCore.Qt.transparent).rgba()
        settings['cell_format']['FILLER2']['fg_pattern'] = QtCore.Qt.SolidPattern
        settings['cell_format']['FILLER2']['flags'] = int(QtCore.Qt.NoItemFlags)
        settings['cell_format']['FILLER2']['font_size'] = settings['cell_format']['NORMAL']['font_size']
        settings['cell_format']['FILLER2']['font_name'] = settings['cell_format']['NORMAL']['font_name']
        settings['cell_format']['FILLER2']['font_weight'] = settings['cell_format']['NORMAL']['font_weight']
        settings['cell_format']['FILLER2']['font_italic'] = settings['cell_format']['NORMAL']['font_italic']
        settings['cell_format']['FILLER2']['align'] = settings['cell_format']['NORMAL']['align']

        # clues
        settings['clues']['NORMAL'] = {}
        color = color_from_stylesheet(self.btn_clue_normal_bg_color.styleSheet(), 'background-color', 'white')
        settings['clues']['NORMAL']['bg_color'] = color.rgba()
        settings['clues']['NORMAL']['bg_pattern'] = QtCore.Qt.SolidPattern
        index = self.combo_clue_normal_style.currentIndex()
        if index == 1:
            settings['clues']['NORMAL']['bg_pattern'] = QtCore.Qt.Dense6Pattern
        elif index == 2:
            settings['clues']['NORMAL']['bg_pattern'] = QtCore.Qt.HorPattern
        elif index == 3:
            settings['clues']['NORMAL']['bg_pattern'] = QtCore.Qt.VerPattern
        elif index == 4:
            settings['clues']['NORMAL']['bg_pattern'] = QtCore.Qt.CrossPattern
        elif index == 5:
            settings['clues']['NORMAL']['bg_pattern'] = QtCore.Qt.BDiagPattern
        elif index == 6:
            settings['clues']['NORMAL']['bg_pattern'] = QtCore.Qt.FDiagPattern
        elif index == 7:
            settings['clues']['NORMAL']['bg_pattern'] = QtCore.Qt.DiagCrossPattern
        elif index == 8:
            settings['clues']['NORMAL']['bg_pattern'] = QtCore.Qt.LinearGradientPattern
        elif index == 9:
            settings['clues']['NORMAL']['bg_pattern'] = QtCore.Qt.RadialGradientPattern
        color = color_from_stylesheet(self.btn_clue_normal_fg_color.styleSheet(), 'background-color', 'black')
        settings['clues']['NORMAL']['fg_color'] = color.rgba()
        font = make_font('Arial', 12, QtGui.QFont.DemiBold)
        font = font_from_stylesheet(self.btn_clue_normal_font.styleSheet(), 'pt', font)
        settings['clues']['NORMAL']['font_size'] = font.pointSize()
        settings['clues']['NORMAL']['font_name'] = font.family()
        settings['clues']['NORMAL']['font_weight'] = font.weight()
        settings['clues']['NORMAL']['font_italic'] = font.italic()
        settings['clues']['NORMAL']['align'] = QtCore.Qt.AlignLeft
        index = self.combo_clue_normal_alignment.currentIndex()
        if index == 1:
            settings['clues']['NORMAL']['align'] = QtCore.Qt.AlignHCenter
        elif index == 2:
            settings['clues']['NORMAL']['align'] = QtCore.Qt.AlignRight

        settings['clues']['INCOMPLETE'] = {}
        color = color_from_stylesheet(self.btn_clue_incomplete_bg_color.styleSheet(), 'background-color', 'white')
        settings['clues']['INCOMPLETE']['bg_color'] = color.rgba()
        settings['clues']['INCOMPLETE']['bg_pattern'] = QtCore.Qt.SolidPattern
        index = self.combo_clue_incomplete_style.currentIndex()
        if index == 1:
            settings['clues']['INCOMPLETE']['bg_pattern'] = QtCore.Qt.Dense6Pattern
        elif index == 2:
            settings['clues']['INCOMPLETE']['bg_pattern'] = QtCore.Qt.HorPattern
        elif index == 3:
            settings['clues']['INCOMPLETE']['bg_pattern'] = QtCore.Qt.VerPattern
        elif index == 4:
            settings['clues']['INCOMPLETE']['bg_pattern'] = QtCore.Qt.CrossPattern
        elif index == 5:
            settings['clues']['INCOMPLETE']['bg_pattern'] = QtCore.Qt.BDiagPattern
        elif index == 6:
            settings['clues']['INCOMPLETE']['bg_pattern'] = QtCore.Qt.FDiagPattern
        elif index == 7:
            settings['clues']['INCOMPLETE']['bg_pattern'] = QtCore.Qt.DiagCrossPattern
        elif index == 8:
            settings['clues']['INCOMPLETE']['bg_pattern'] = QtCore.Qt.LinearGradientPattern
        elif index == 9:
            settings['clues']['INCOMPLETE']['bg_pattern'] = QtCore.Qt.RadialGradientPattern
        color = color_from_stylesheet(self.btn_clue_incomplete_fg_color.styleSheet(), 'background-color', 'black')
        settings['clues']['INCOMPLETE']['fg_color'] = color.rgba()

        settings['clues']['COMPLETE'] = {}
        color = color_from_stylesheet(self.btn_clue_complete_bg_color.styleSheet(), 'background-color', 'white')
        settings['clues']['COMPLETE']['bg_color'] = color.rgba()
        settings['clues']['COMPLETE']['bg_pattern'] = QtCore.Qt.SolidPattern
        index = self.combo_clue_complete_style.currentIndex()
        if index == 1:
            settings['clues']['COMPLETE']['bg_pattern'] = QtCore.Qt.Dense6Pattern
        elif index == 2:
            settings['clues']['COMPLETE']['bg_pattern'] = QtCore.Qt.HorPattern
        elif index == 3:
            settings['clues']['COMPLETE']['bg_pattern'] = QtCore.Qt.VerPattern
        elif index == 4:
            settings['clues']['COMPLETE']['bg_pattern'] = QtCore.Qt.CrossPattern
        elif index == 5:
            settings['clues']['COMPLETE']['bg_pattern'] = QtCore.Qt.BDiagPattern
        elif index == 6:
            settings['clues']['COMPLETE']['bg_pattern'] = QtCore.Qt.FDiagPattern
        elif index == 7:
            settings['clues']['COMPLETE']['bg_pattern'] = QtCore.Qt.DiagCrossPattern
        elif index == 8:
            settings['clues']['COMPLETE']['bg_pattern'] = QtCore.Qt.LinearGradientPattern
        elif index == 9:
            settings['clues']['COMPLETE']['bg_pattern'] = QtCore.Qt.RadialGradientPattern
        color = color_from_stylesheet(self.btn_clue_complete_fg_color.styleSheet(), 'background-color', 'black')
        settings['clues']['COMPLETE']['fg_color'] = color.rgba()

        settings['clues']['SURROUNDING'] = {}
        color = color_from_stylesheet(self.btn_clue_surrounding_color.styleSheet(), 'background-color', 'white')
        settings['clues']['SURROUNDING']['bg_color'] = color.rgba()
        # columns
        settings['clues']['columns'] = []
        for i in range(self.lw_clues_cols.count()):
            item = self.lw_clues_cols.item(i)
            settings['clues']['columns'].append({'name': item.text(), 
                'visible': bool(item.checkState()), 'width': -1})
            
        # lookup
        settings['lookup']['default_lang'] = self.combo_lookup_deflang.currentData()

        settings['lookup']['dics'] = {}
        settings['lookup']['dics']['show'] = self.chb_dics_show.isChecked()
        settings['lookup']['dics']['exact_match'] = self.chb_dics_exact.isChecked()
        settings['lookup']['dics']['show_pos'] = self.chb_dics_showpos.isChecked()
        settings['lookup']['dics']['bad_pos'] = self.le_dics_badpos.text() or 'UNKNOWN'
        settings['lookup']['dics']['mw_apikey'] = self.le_dics_apikey_mw.text().strip()
        settings['lookup']['dics']['yandex_key'] = self.le_dics_apikey_yandex.text().strip()

        settings['lookup']['google'] = {}
        settings['lookup']['google']['show'] = self.chb_google_show.isChecked()
        settings['lookup']['google']['exact_match'] = self.chb_google_exact.isChecked()
        settings['lookup']['google']['safe_search'] = self.chb_google_safe.isChecked()
        settings['lookup']['google']['file_types'] = self.le_google_filetypes.text().lower().split()
        ls_lang = []
        for i in range(self.lw_google_lang.count()):
            item = self.lw_google_lang.item(i)
            if item.checkState():
                ls_lang.append(item.data(QtCore.Qt.StatusTipRole))
        settings['lookup']['google']['lang'] = ls_lang
        ls_int_lang = []
        for i in range(self.lw_google_interface_lang.count()):
            item = self.lw_google_interface_lang.item(i)
            if item.checkState():
                ls_int_lang.append(item.data(QtCore.Qt.StatusTipRole))
        settings['lookup']['google']['interface_lang'] = ls_int_lang
        ls_geo = []
        for i in range(self.lw_google_geo.count()):
            item = self.lw_google_geo.item(i)
            if item.checkState():
                ls_geo.append(item.data(QtCore.Qt.StatusTipRole))
        settings['lookup']['google']['country'] = ls_geo
        settings['lookup']['google']['link_site'] = self.le_google_linksite.text().strip()
        settings['lookup']['google']['related_site'] = self.le_google_relatedsite.text().strip()
        settings['lookup']['google']['in_site'] = self.le_google_insite.text().strip()
        settings['lookup']['google']['nresults'] = self.spin_google_nresults.value()
        settings['lookup']['google']['api_key'] = self.le_google_apikey.text().strip()
        settings['lookup']['google']['api_cse'] = self.le_google_cseid.text().strip()

        # export
        settings['export']['openfile'] = self.chb_export_openfile.isChecked()
        settings['export']['clear_cw'] = self.chb_export_clearcw.isChecked()
        settings['export']['img_resolution'] = self.spin_export_resolution_img.value()
        settings['export']['pdf_resolution'] = self.spin_export_resolution_pdf.value()
        settings['export']['mm_per_cell'] = self.spin_export_cellsize.value()
        settings['export']['img_output_quality'] = self.spin_export_quality.value()
        settings['export']['svg_title'] = self.le_svg_title.text()
        settings['export']['svg_description'] = self.le_svg_description.text()

        # plugins > third-party
        settings['plugins']['thirdparty'] = {}
        settings['plugins']['thirdparty']['git'] = {'active': bool(self.model_plugins_3party.item(0).child(0, 1).checkState()),
            'exepath': self.model_plugins_3party.item(0).child(1, 1).text()}
        settings['plugins']['thirdparty']['dbbrowser'] = {'active': bool(self.model_plugins_3party.item(1).child(0, 1).checkState()),
            'exepath': self.model_plugins_3party.item(1).child(1, 1).text(),
            'command': self.model_plugins_3party.item(1).child(2, 1).text()}
        settings['plugins']['thirdparty']['text'] = {'active': bool(self.model_plugins_3party.item(2).child(0, 1).checkState()),
            'exepath': self.model_plugins_3party.item(2).child(1, 1).text(),
            'command': self.model_plugins_3party.item(2).child(2, 1).text()}

        # plugins > custom
        settings['plugins']['custom'] = {}
        settings['plugins']['custom'].update(CWSettings.settings['plugins']['custom'])
        self.page_plugins_custom.reload_plugins()
        
        # printing
        settings['printing']['margins'] = [self.spin_margin_left.value(), self.spin_margin_right.value(),
                                           self.spin_margin_top.value(), self.spin_margin_bottom.value()]
        settings['printing']['layout'] = self.combo_print_layout.currentText().lower()
        settings['printing']['font_embed'] = self.chb_print_font_embed.isChecked()
        settings['printing']['antialias'] = self.chb_print_antialias.isChecked()
        settings['printing']['print_cw'] = self.chb_print_print_cw.isChecked()
        settings['printing']['print_clues'] = self.chb_print_print_clues.isChecked()
        settings['printing']['clear_cw'] = self.chb_print_clear_cw.isChecked()
        settings['printing']['print_clue_letters'] = self.chb_print_print_clue_letters.isChecked()
        settings['printing']['print_info'] = self.chb_print_print_info.isChecked()
        settings['printing']['color_print'] = self.chb_print_color_print.isChecked()
        settings['printing']['openfile'] = self.chb_print_openfile.isChecked()
        settings['printing']['cw_title'] = self.le_print_title.text()
        settings['printing']['clues_title'] = self.le_print_clues_title.text()
        settings['printing']['header_font'] = {}
        font = make_font('Verdana', 20, QtGui.QFont.Bold)
        font = font_from_stylesheet(self.btn_print_header_font.styleSheet(), 'pt', font)
        settings['printing']['header_font']['font_size'] = font.pointSize()
        settings['printing']['header_font']['font_name'] = font.family()
        settings['printing']['header_font']['font_weight'] = font.weight()
        settings['printing']['header_font']['font_italic'] = font.italic()
        color = color_from_stylesheet(self.btn_print_header_color.styleSheet(), 'background-color', 'blue')
        settings['printing']['header_font']['color'] = color.rgba()
        settings['printing']['info_font'] = {}
        font = make_font('Arial', 14, QtGui.QFont.Normal)
        font = font_from_stylesheet(self.btn_print_info_font.styleSheet(), 'pt', font)
        settings['printing']['info_font']['font_size'] = font.pointSize()
        settings['printing']['info_font']['font_name'] = font.family()
        settings['printing']['info_font']['font_weight'] = font.weight()
        settings['printing']['info_font']['font_italic'] = font.italic()
        color = color_from_stylesheet(self.btn_print_info_color.styleSheet(), 'background-color', 'black')
        settings['printing']['info_font']['color'] = color.rgba()
        settings['printing']['clue_number_font'] = {}
        font = make_font('Arial', 14, QtGui.QFont.Bold)
        font = font_from_stylesheet(self.btn_print_clue_number_font.styleSheet(), 'pt', font)
        settings['printing']['clue_number_font']['font_size'] = font.pointSize()
        settings['printing']['clue_number_font']['font_name'] = font.family()
        settings['printing']['clue_number_font']['font_weight'] = font.weight()
        settings['printing']['clue_number_font']['font_italic'] = font.italic()
        color = color_from_stylesheet(self.btn_print_clue_number_color.styleSheet(), 'background-color', 'black')
        settings['printing']['clue_number_font']['color'] = color.rgba()
        settings['printing']['clue_font'] = {}
        font = make_font('Arial', 14, QtGui.QFont.Normal)
        font = font_from_stylesheet(self.btn_print_clue_text_font.styleSheet(), 'pt', font)
        settings['printing']['clue_font']['font_size'] = font.pointSize()
        settings['printing']['clue_font']['font_name'] = font.family()
        settings['printing']['clue_font']['font_weight'] = font.weight()
        settings['printing']['clue_font']['font_italic'] = font.italic()
        color = color_from_stylesheet(self.btn_print_clue_text_color.styleSheet(), 'background-color', 'black')
        settings['printing']['clue_font']['color'] = color.rgba()
        settings['printing']['clue_letters_font'] = {}
        font = make_font('Arial', 14, QtGui.QFont.Normal, True)
        font = font_from_stylesheet(self.btn_print_clue_sizehint_font.styleSheet(), 'pt', font)
        settings['printing']['clue_letters_font']['font_size'] = font.pointSize()
        settings['printing']['clue_letters_font']['font_name'] = font.family()
        settings['printing']['clue_letters_font']['font_weight'] = font.weight()
        settings['printing']['clue_letters_font']['font_italic'] = font.italic()
        color = color_from_stylesheet(self.btn_print_clue_sizehint_color.styleSheet(), 'background-color', 'black')
        settings['printing']['clue_letters_font']['color'] = color.rgba()

        # update
        settings['update']['check_every'] = self.spin_update_period.value()
        settings['update']['only_major_versions'] = self.chb_update_major_only.isChecked()
        settings['update']['auto_update'] = self.chb_update_auto.isChecked()
        settings['update']['restart_on_update'] = self.chb_update_restart.isChecked()        
        settings['update']['logfile'] = os.path.relpath(self.le_update_logfile.text(), os.path.dirname(__file__)) if self.le_update_logfile.text() else ''

        # sharing
        settings['sharing']['account'] = self.le_sharing_account.text()
        settings['sharing']['bearer_token'] = self.le_sharing_token.text()
        settings['sharing']['use_api_key'] = self.chb_sharing_use_api_key.isChecked()
        settings['sharing']['root_folder'] = self.le_sharing_root.text()
        settings['sharing']['user'] = self.le_sharing_user.text()
        settings['sharing']['use_own_browser'] = self.chb_sharing_ownbrowser.isChecked()
        
        return settings

    ## Shortcut method to set the value of a QtWidgets.QSpinBox control with min/max threshold checks.
    def _set_spin_value_safe(self, spin, val):
        if val < spin.minimum():
            val = spin.minimum()
        elif val > spin.maximum():
            val = spin.maximum()
        spin.setValue(val)
    
    ## @brief Updates the GUI controls from a dict of global settings.
    # @param settings `dict` global setting dictionary in guisettings::CWSettings::settings format. 
    # If `None` (default), guisettings::CWSettings::settings is used (the app global settings).
    # @param page `str` name of page to update. GUI controls are updated only on this page. 
    # If `None` (default), GUI controls will be updated on all pages.
    def from_settings(self, settings=None, page=None):
        
        if settings is None:
            settings = CWSettings.settings

        # common
        if page is None or page == _('Common'):
            self.le_tempdir.setText(settings['common']['temp_dir'])
            self.chb_autosave_cw.setChecked(settings['common']['autosave_cw'])
            registered = file_types_registered()
            self.act_register_associations.setData(int(registered))
            self.act_register_associations.setText(_('Register file associations') if not registered else _('Unregister file associations'))
            self.btn_register_associations.setStyleSheet(f"background-color: {'#7FFFD4' if registered else '#DC143C'}; border: none;")
            self._set_spin_value_safe(self.spin_req_timeout, settings['common']['web']['req_timeout'])
            self.chb_system_proxy.setChecked(settings['common']['web']['proxy']['use_system'])
            self.le_http_proxy.setText(settings['common']['web']['proxy']['http'])
            self.le_https_proxy.setText(settings['common']['web']['proxy']['https'])

        # engine
        if page is None or page == _('Generation'):
            # timeout
            self._set_spin_value_safe(self.spin_gen_timeout, settings['cw_settings']['timeout'])
            # method
            meth = settings['cw_settings']['method']
            if not meth:
                self.combo_gen_method.setCurrentIndex(0)
            elif meth == 'iter':
                self.combo_gen_method.setCurrentIndex(1)
            elif meth == 'recurse':
                self.combo_gen_method.setCurrentIndex(2)
            # log
            log = settings['cw_settings']['log']
            if not log:
                self.combo_log.setCurrentIndex(0)
            elif log == 'stdout':
                self.combo_log.setCurrentIndex(1)
            else:
                self.combo_log.setCurrentText(log)
        
        # Sources > Source management
        if page is None or page == _('Source management'):
            # maxres
            val = settings['wordsrc']['maxres']
            if val is None:
                self.chb_maxfetch.setChecked(False)
            else:
                self.chb_maxfetch.setChecked(True)
                self._set_spin_value_safe(self.spin_maxfetch, val)
            # sources
            self.lw_sources.clear()
            for src in settings['wordsrc']['sources']:
                self.addoredit_wordsrc(src)
        
        # Sources > Search rules
        if page is None or page == _('Search rules'):
            # pos
            pos = settings['cw_settings']['pos']
            if isinstance(pos, str) and ',' in pos:
                pos = pos.split(',')
                
            for row in range(self.lw_pos.count()):
                it = self.lw_pos.item(row)
                for p in POS:
                    if p[1] == it.text():
                        it.setCheckState(QtCore.Qt.Checked if p[0] in pos else QtCore.Qt.Unchecked)
                        break
            # excluded
            exwords = settings['wordsrc']['excluded']['words']
            self.te_excluded.setPlainText('\n'.join(exwords) if exwords else '')
            self.chb_excl_regex.setChecked(settings['wordsrc']['excluded']['regex'])
        
        # UI > Window
        if page is None or page == _('Window'):
            index = self.combo_apptheme.findText(settings['gui']['theme'])
            if index >= 0:
                self.combo_apptheme.setCurrentIndex(index)
            index = settings['gui']['toolbar_pos']
            if index >=0 and index <5:
                self.combo_toolbarpos.setCurrentIndex(index)
        
        # UI > grid
        if page is None or page == _('Grid'):
            # scale
            self._set_spin_value_safe(self.spin_cwscale, settings['grid_style']['scale'])
            # show grid
            self.chb_showgrid.setChecked(settings['grid_style']['show'])
            # grid style
            gridline = settings['grid_style']['line']
            if gridline == QtCore.Qt.SolidLine:
                self.combo_gridlinestyle.setCurrentIndex(0)
            elif gridline == QtCore.Qt.DashLine:
                self.combo_gridlinestyle.setCurrentIndex(1)
            elif gridline == QtCore.Qt.DotLine:
                self.combo_gridlinestyle.setCurrentIndex(2)
            elif gridline == QtCore.Qt.DashDotLine:
                self.combo_gridlinestyle.setCurrentIndex(3)
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['grid_style']['line_color']), self.btn_gridlinecolor.styleSheet(), 'background-color')
            self.btn_gridlinecolor.setStyleSheet(style)     
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['grid_style']['active_cell_color']), self.btn_activecellcolor.styleSheet(), 'background-color')
            self.btn_activecellcolor.setStyleSheet(style) 
            self._set_spin_value_safe(self.spin_gridlinesz, settings['grid_style']['line_width'])
            # char case 
            charcase = settings['grid_style']['char_case']
            if charcase == 'upper':
                self.combo_charcase.setCurrentIndex(0)
            elif charcase == 'lower':
                self.combo_charcase.setCurrentIndex(1)
            # headers
            self.chb_showcoords.setChecked(settings['grid_style']['header'])
            # cell size
            self._set_spin_value_safe(self.spin_cellsz, settings['grid_style']['cell_size'])
            # numbers
            self.chb_shownumbers.setChecked(settings['grid_style']['numbers']['show'])
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['grid_style']['numbers']['color']), self.btn_numberscolor.styleSheet(), 'background-color')
            self.btn_numberscolor.setStyleSheet(style)
            font = make_font(settings['grid_style']['numbers']['font_name'], settings['grid_style']['numbers']['font_size'], 
                             settings['grid_style']['numbers']['font_weight'], settings['grid_style']['numbers']['font_italic'])
            style = font_to_stylesheet(font, self.btn_numbersfont.styleSheet())
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['grid_style']['numbers']['color']), style, 'color')
            self.btn_numbersfont.setStyleSheet(style)
            # cell format
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['cell_format']['NORMAL']['bg_color']), self.btn_cell_normal_bg_color.styleSheet(), 'background-color')
            self.btn_cell_normal_bg_color.setStyleSheet(style)
            patn = settings['cell_format']['NORMAL']['bg_pattern']
            if patn == QtCore.Qt.SolidPattern:
                self.combo_cell_normal_style.setCurrentIndex(0)
            elif patn == QtCore.Qt.Dense6Pattern:
                self.combo_cell_normal_style.setCurrentIndex(1)
            elif patn == QtCore.Qt.HorPattern:
                self.combo_cell_normal_style.setCurrentIndex(2)
            elif patn == QtCore.Qt.VerPattern:
                self.combo_cell_normal_style.setCurrentIndex(3)
            elif patn == QtCore.Qt.CrossPattern:
                self.combo_cell_normal_style.setCurrentIndex(4)
            elif patn == QtCore.Qt.BDiagPattern:
                self.combo_cell_normal_style.setCurrentIndex(5)
            elif patn == QtCore.Qt.FDiagPattern:
                self.combo_cell_normal_style.setCurrentIndex(6)
            elif patn == QtCore.Qt.DiagCrossPattern:
                self.combo_cell_normal_style.setCurrentIndex(7)
            elif patn == QtCore.Qt.LinearGradientPattern:
                self.combo_cell_normal_style.setCurrentIndex(8)
            elif patn == QtCore.Qt.RadialGradientPattern:
                self.combo_cell_normal_style.setCurrentIndex(9)
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['cell_format']['NORMAL']['fg_color']), self.btn_cell_normal_fg_color.styleSheet(), 'background-color')
            self.btn_cell_normal_fg_color.setStyleSheet(style)
            font = make_font(settings['cell_format']['NORMAL']['font_name'], settings['cell_format']['NORMAL']['font_size'], 
                             settings['cell_format']['NORMAL']['font_weight'], settings['cell_format']['NORMAL']['font_italic'])
            style = font_to_stylesheet(font, self.btn_cell_normal_font.styleSheet())
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['cell_format']['NORMAL']['fg_color']), style, 'color')
            self.btn_cell_normal_font.setStyleSheet(style)
            
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['cell_format']['HILITE']['bg_color']), self.btn_cell_hilite_bg_color.styleSheet(), 'background-color')
            self.btn_cell_hilite_bg_color.setStyleSheet(style)
            patn = settings['cell_format']['HILITE']['bg_pattern']
            if patn == QtCore.Qt.SolidPattern:
                self.combo_cell_hilite_style.setCurrentIndex(0)
            elif patn == QtCore.Qt.Dense6Pattern:
                self.combo_cell_hilite_style.setCurrentIndex(1)
            elif patn == QtCore.Qt.HorPattern:
                self.combo_cell_hilite_style.setCurrentIndex(2)
            elif patn == QtCore.Qt.VerPattern:
                self.combo_cell_hilite_style.setCurrentIndex(3)
            elif patn == QtCore.Qt.CrossPattern:
                self.combo_cell_hilite_style.setCurrentIndex(4)
            elif patn == QtCore.Qt.BDiagPattern:
                self.combo_cell_hilite_style.setCurrentIndex(5)
            elif patn == QtCore.Qt.FDiagPattern:
                self.combo_cell_hilite_style.setCurrentIndex(6)
            elif patn == QtCore.Qt.DiagCrossPattern:
                self.combo_cell_hilite_style.setCurrentIndex(7)
            elif patn == QtCore.Qt.LinearGradientPattern:
                self.combo_cell_hilite_style.setCurrentIndex(8)
            elif patn == QtCore.Qt.RadialGradientPattern:
                self.combo_cell_hilite_style.setCurrentIndex(9)
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['cell_format']['HILITE']['fg_color']), self.btn_cell_hilite_fg_color.styleSheet(), 'background-color')
            self.btn_cell_hilite_fg_color.setStyleSheet(style)
            font = make_font(settings['cell_format']['HILITE']['font_name'], settings['cell_format']['HILITE']['font_size'], 
                             settings['cell_format']['HILITE']['font_weight'], settings['cell_format']['HILITE']['font_italic'])
            style = font_to_stylesheet(font, self.btn_cell_hilite_font.styleSheet())
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['cell_format']['HILITE']['fg_color']), style, 'color')
            self.btn_cell_hilite_font.setStyleSheet(style)
            
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['cell_format']['BLANK']['bg_color']), self.btn_cell_blank_bg_color.styleSheet(), 'background-color')
            self.btn_cell_blank_bg_color.setStyleSheet(style)
            patn = settings['cell_format']['BLANK']['bg_pattern']
            if patn == QtCore.Qt.SolidPattern:
                self.combo_cell_blank_style.setCurrentIndex(0)
            elif patn == QtCore.Qt.Dense6Pattern:
                self.combo_cell_blank_style.setCurrentIndex(1)
            elif patn == QtCore.Qt.HorPattern:
                self.combo_cell_blank_style.setCurrentIndex(2)
            elif patn == QtCore.Qt.VerPattern:
                self.combo_cell_blank_style.setCurrentIndex(3)
            elif patn == QtCore.Qt.CrossPattern:
                self.combo_cell_blank_style.setCurrentIndex(4)
            elif patn == QtCore.Qt.BDiagPattern:
                self.combo_cell_blank_style.setCurrentIndex(5)
            elif patn == QtCore.Qt.FDiagPattern:
                self.combo_cell_blank_style.setCurrentIndex(6)
            elif patn == QtCore.Qt.DiagCrossPattern:
                self.combo_cell_blank_style.setCurrentIndex(7)
            elif patn == QtCore.Qt.LinearGradientPattern:
                self.combo_cell_blank_style.setCurrentIndex(8)
            elif patn == QtCore.Qt.RadialGradientPattern:
                self.combo_cell_blank_style.setCurrentIndex(9)
                
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['cell_format']['FILLER']['bg_color']), self.btn_cell_filler_bg_color.styleSheet(), 'background-color')
            self.btn_cell_filler_bg_color.setStyleSheet(style)
            patn = settings['cell_format']['FILLER']['bg_pattern']
            if patn == QtCore.Qt.SolidPattern:
                self.combo_cell_filler_style.setCurrentIndex(0)
            elif patn == QtCore.Qt.Dense6Pattern:
                self.combo_cell_filler_style.setCurrentIndex(1)
            elif patn == QtCore.Qt.HorPattern:
                self.combo_cell_filler_style.setCurrentIndex(2)
            elif patn == QtCore.Qt.VerPattern:
                self.combo_cell_filler_style.setCurrentIndex(3)
            elif patn == QtCore.Qt.CrossPattern:
                self.combo_cell_filler_style.setCurrentIndex(4)
            elif patn == QtCore.Qt.BDiagPattern:
                self.combo_cell_filler_style.setCurrentIndex(5)
            elif patn == QtCore.Qt.FDiagPattern:
                self.combo_cell_filler_style.setCurrentIndex(6)
            elif patn == QtCore.Qt.DiagCrossPattern:
                self.combo_cell_filler_style.setCurrentIndex(7)
            elif patn == QtCore.Qt.LinearGradientPattern:
                self.combo_cell_filler_style.setCurrentIndex(8)
            elif patn == QtCore.Qt.RadialGradientPattern:
                self.combo_cell_filler_style.setCurrentIndex(9)
                
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['cell_format']['FILLER2']['bg_color']), self.btn_cell_filler2_bg_color.styleSheet(), 'background-color')
            self.btn_cell_filler2_bg_color.setStyleSheet(style)
            patn = settings['cell_format']['FILLER2']['bg_pattern']
            if patn == QtCore.Qt.SolidPattern:
                self.combo_cell_filler2_style.setCurrentIndex(0)
            elif patn == QtCore.Qt.Dense6Pattern:
                self.combo_cell_filler2_style.setCurrentIndex(1)
            elif patn == QtCore.Qt.HorPattern:
                self.combo_cell_filler2_style.setCurrentIndex(2)
            elif patn == QtCore.Qt.VerPattern:
                self.combo_cell_filler2_style.setCurrentIndex(3)
            elif patn == QtCore.Qt.CrossPattern:
                self.combo_cell_filler2_style.setCurrentIndex(4)
            elif patn == QtCore.Qt.BDiagPattern:
                self.combo_cell_filler2_style.setCurrentIndex(5)
            elif patn == QtCore.Qt.FDiagPattern:
                self.combo_cell_filler2_style.setCurrentIndex(6)
            elif patn == QtCore.Qt.DiagCrossPattern:
                self.combo_cell_filler2_style.setCurrentIndex(7)
            elif patn == QtCore.Qt.LinearGradientPattern:
                self.combo_cell_filler2_style.setCurrentIndex(8)
            elif patn == QtCore.Qt.RadialGradientPattern:
                self.combo_cell_filler2_style.setCurrentIndex(9)
        
        # UI > clues
        if page is None or page == _('Clues'):
            # normal
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clues']['NORMAL']['bg_color']), self.btn_clue_normal_bg_color.styleSheet(), 'background-color')
            self.btn_clue_normal_bg_color.setStyleSheet(style)
            patn = settings['clues']['NORMAL']['bg_pattern']
            if patn == QtCore.Qt.SolidPattern:
                self.combo_clue_normal_style.setCurrentIndex(0)
            elif patn == QtCore.Qt.Dense6Pattern:
                self.combo_clue_normal_style.setCurrentIndex(1)
            elif patn == QtCore.Qt.HorPattern:
                self.combo_clue_normal_style.setCurrentIndex(2)
            elif patn == QtCore.Qt.VerPattern:
                self.combo_clue_normal_style.setCurrentIndex(3)
            elif patn == QtCore.Qt.CrossPattern:
                self.combo_clue_normal_style.setCurrentIndex(4)
            elif patn == QtCore.Qt.BDiagPattern:
                self.combo_clue_normal_style.setCurrentIndex(5)
            elif patn == QtCore.Qt.FDiagPattern:
                self.combo_clue_normal_style.setCurrentIndex(6)
            elif patn == QtCore.Qt.DiagCrossPattern:
                self.combo_clue_normal_style.setCurrentIndex(7)
            elif patn == QtCore.Qt.LinearGradientPattern:
                self.combo_clue_normal_style.setCurrentIndex(8)
            elif patn == QtCore.Qt.RadialGradientPattern:
                self.combo_clue_normal_style.setCurrentIndex(9)
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clues']['NORMAL']['fg_color']), self.btn_clue_normal_fg_color.styleSheet(), 'background-color')
            self.btn_clue_normal_fg_color.setStyleSheet(style)
            font = make_font(settings['clues']['NORMAL']['font_name'], settings['clues']['NORMAL']['font_size'], 
                             settings['clues']['NORMAL']['font_weight'], settings['clues']['NORMAL']['font_italic'])
            style = font_to_stylesheet(font, self.btn_clue_normal_font.styleSheet())
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clues']['NORMAL']['fg_color']), style, 'color')
            self.btn_clue_normal_font.setStyleSheet(style)
            align = settings['clues']['NORMAL']['align']
            if align == QtCore.Qt.AlignLeft:
                self.combo_clue_normal_alignment.setCurrentIndex(0)
            elif align == QtCore.Qt.AlignHCenter:
                self.combo_clue_normal_alignment.setCurrentIndex(1)
            elif align == QtCore.Qt.AlignRight:
                self.combo_clue_normal_alignment.setCurrentIndex(2)

            # incomplete
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clues']['INCOMPLETE']['bg_color']), self.btn_clue_incomplete_bg_color.styleSheet(), 'background-color')
            self.btn_clue_incomplete_bg_color.setStyleSheet(style)
            patn = settings['clues']['INCOMPLETE']['bg_pattern']
            if patn == QtCore.Qt.SolidPattern:
                self.combo_clue_incomplete_style.setCurrentIndex(0)
            elif patn == QtCore.Qt.Dense6Pattern:
                self.combo_clue_incomplete_style.setCurrentIndex(1)
            elif patn == QtCore.Qt.HorPattern:
                self.combo_clue_incomplete_style.setCurrentIndex(2)
            elif patn == QtCore.Qt.VerPattern:
                self.combo_clue_incomplete_style.setCurrentIndex(3)
            elif patn == QtCore.Qt.CrossPattern:
                self.combo_clue_incomplete_style.setCurrentIndex(4)
            elif patn == QtCore.Qt.BDiagPattern:
                self.combo_clue_incomplete_style.setCurrentIndex(5)
            elif patn == QtCore.Qt.FDiagPattern:
                self.combo_clue_incomplete_style.setCurrentIndex(6)
            elif patn == QtCore.Qt.DiagCrossPattern:
                self.combo_clue_incomplete_style.setCurrentIndex(7)
            elif patn == QtCore.Qt.LinearGradientPattern:
                self.combo_clue_incomplete_style.setCurrentIndex(8)
            elif patn == QtCore.Qt.RadialGradientPattern:
                self.combo_clue_incomplete_style.setCurrentIndex(9)
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clues']['INCOMPLETE']['fg_color']), self.btn_clue_incomplete_fg_color.styleSheet(), 'background-color')
            self.btn_clue_incomplete_fg_color.setStyleSheet(style)

            # complete
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clues']['COMPLETE']['bg_color']), self.btn_clue_complete_bg_color.styleSheet(), 'background-color')
            self.btn_clue_complete_bg_color.setStyleSheet(style)
            patn = settings['clues']['COMPLETE']['bg_pattern']
            if patn == QtCore.Qt.SolidPattern:
                self.combo_clue_complete_style.setCurrentIndex(0)
            elif patn == QtCore.Qt.Dense6Pattern:
                self.combo_clue_complete_style.setCurrentIndex(1)
            elif patn == QtCore.Qt.HorPattern:
                self.combo_clue_complete_style.setCurrentIndex(2)
            elif patn == QtCore.Qt.VerPattern:
                self.combo_clue_complete_style.setCurrentIndex(3)
            elif patn == QtCore.Qt.CrossPattern:
                self.combo_clue_complete_style.setCurrentIndex(4)
            elif patn == QtCore.Qt.BDiagPattern:
                self.combo_clue_complete_style.setCurrentIndex(5)
            elif patn == QtCore.Qt.FDiagPattern:
                self.combo_clue_complete_style.setCurrentIndex(6)
            elif patn == QtCore.Qt.DiagCrossPattern:
                self.combo_clue_complete_style.setCurrentIndex(7)
            elif patn == QtCore.Qt.LinearGradientPattern:
                self.combo_clue_complete_style.setCurrentIndex(8)
            elif patn == QtCore.Qt.RadialGradientPattern:
                self.combo_clue_complete_style.setCurrentIndex(9)
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clues']['COMPLETE']['fg_color']), self.btn_clue_complete_fg_color.styleSheet(), 'background-color')
            self.btn_clue_complete_fg_color.setStyleSheet(style)
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clues']['SURROUNDING']['bg_color']), self.btn_clue_surrounding_color.styleSheet(), 'background-color')
            self.btn_clue_surrounding_color.setStyleSheet(style)

            # columns
            self._fill_clue_cols()

        # UI > Toolbar
        if page is None or page == _('Toolbar'):
            self.page_toolbar.from_list(settings['gui']['toolbar_actions'])
        
        # Lookup
        if page is None or page == _('Definition lookup'):
            self.combo_lookup_deflang.setCurrentText(LANG[settings['lookup']['default_lang']])

            self.chb_dics_show.setChecked(settings['lookup']['dics']['show'])
            self.chb_dics_exact.setChecked(settings['lookup']['dics']['exact_match'])
            self.chb_dics_showpos.setChecked(settings['lookup']['dics']['show_pos'])
            self.le_dics_badpos.setText(settings['lookup']['dics']['bad_pos'] or 'UNKNOWN')
            self.le_dics_apikey_mw.setText(settings['lookup']['dics']['mw_apikey'] if settings['lookup']['dics']['mw_apikey'] != MW_DIC_KEY else '')
            self.le_dics_apikey_yandex.setText(settings['lookup']['dics']['yandex_key'] if settings['lookup']['dics']['yandex_key'] != YAN_DICT_KEY else '')

            self.chb_google_show.setChecked(settings['lookup']['google']['show'])
            self.chb_google_safe.setChecked(settings['lookup']['google']['safe_search'])
            self.chb_google_exact.setChecked(settings['lookup']['google']['exact_match'])
            self.le_google_filetypes.setText(' '.join(settings['lookup']['google']['file_types']).strip())
            for i in range(self.lw_google_lang.count()):
                item = self.lw_google_lang.item(i)
                if settings['lookup']['google']['lang']:
                    item.setCheckState(QtCore.Qt.Checked if item.data(QtCore.Qt.StatusTipRole) in settings['lookup']['google']['lang'] else QtCore.Qt.Unchecked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)
            for i in range(self.lw_google_interface_lang.count()):
                item = self.lw_google_interface_lang.item(i)
                if settings['lookup']['google']['interface_lang']:
                    item.setCheckState(QtCore.Qt.Checked if item.data(QtCore.Qt.StatusTipRole) in settings['lookup']['google']['interface_lang'] else QtCore.Qt.Unchecked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)
            for i in range(self.lw_google_geo.count()):
                item = self.lw_google_geo.item(i)
                if settings['lookup']['google']['country']:
                    item.setCheckState(QtCore.Qt.Checked if item.data(QtCore.Qt.StatusTipRole) in settings['lookup']['google']['country'] else QtCore.Qt.Unchecked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)
            self.le_google_linksite.setText(settings['lookup']['google']['link_site'] or '')
            self.le_google_relatedsite.setText(settings['lookup']['google']['related_site'] or '')
            self.le_google_insite.setText(settings['lookup']['google']['in_site'] or '')
            self.spin_google_nresults.setValue(settings['lookup']['google']['nresults'] or -1)
            self.on_lw_google_lang_changed(None)
            self.on_lw_google_interface_lang_changed(None)
            self.on_lw_google_geo_changed(None)
            self.le_google_apikey.setText(settings['lookup']['google']['api_key'] if settings['lookup']['google']['api_key'] != GOOGLE_KEY else '')
            self.le_google_cseid.setText(settings['lookup']['google']['api_cse'] if settings['lookup']['google']['api_cse'] != GOOGLE_CSE else '')

        # Import & Export
        if page is None or page == _('Import & Export'):

            settings = CWSettings.settings['export']

            self.chb_export_openfile.setChecked(settings['openfile'])
            self.chb_export_clearcw.setChecked(settings['clear_cw'])
            self._set_spin_value_safe(self.spin_export_resolution_img, settings['img_resolution'])
            self._set_spin_value_safe(self.spin_export_resolution_pdf, settings['pdf_resolution'])
            self._set_spin_value_safe(self.spin_export_cellsize, settings['mm_per_cell'])
            self._set_spin_value_safe(self.spin_export_quality, settings['img_output_quality'])
            self.le_svg_title.setText(settings['svg_title'])
            self.le_svg_description.setText(settings['svg_description'])
        
        # Plugins > Third-party
        if page is None or page == _('Third-party'):
            settings = CWSettings.settings['plugins']['thirdparty']
            if 'git' in settings:
                self.model_plugins_3party.item(0).child(0, 1).setCheckState(2 if settings['git'].get('active', False) else 0)
                self.model_plugins_3party.item(0).child(1, 1).setText(settings['git'].get('exepath', ''))
            else:
                self.model_plugins_3party.item(0).child(0, 1).setCheckState(0)
                self.model_plugins_3party.item(0).child(1, 1).setText('')

            if 'dbbrowser' in settings:
                self.model_plugins_3party.item(1).child(0, 1).setCheckState(2 if settings['dbbrowser'].get('active', False) else 0)
                self.model_plugins_3party.item(1).child(1, 1).setText(settings['dbbrowser'].get('exepath', ''))
                self.model_plugins_3party.item(1).child(2, 1).setText(settings['dbbrowser'].get('command', ''))
            else:
                self.model_plugins_3party.item(1).child(0, 1).setCheckState(0)
                self.model_plugins_3party.item(1).child(1, 1).setText('')
                self.model_plugins_3party.item(1).child(2, 1).setText('')

            if 'text' in settings:
                self.model_plugins_3party.item(2).child(0, 1).setCheckState(2 if settings['text'].get('active', False) else 0)
                self.model_plugins_3party.item(2).child(1, 1).setText(settings['text'].get('exepath', ''))
                self.model_plugins_3party.item(2).child(2, 1).setText(settings['text'].get('command', ''))
            else:
                self.model_plugins_3party.item(2).child(0, 1).setCheckState(0)
                self.model_plugins_3party.item(2).child(1, 1).setText('')
                self.model_plugins_3party.item(2).child(2, 1).setText('')

            self.tv_plugins_3party.setModel(self.model_plugins_3party)
            self.tv_plugins_3party.show()

        # Plugins > Custom
        if page is None or page == _('Custom'):
            self.page_plugins_custom.reload_plugins()
                    
        # Printing
        if page is None or page == _('Printing'):

            settings = CWSettings.settings['printing']

            index = self.combo_print_layout.findText(settings['layout'], QtCore.Qt.MatchFixedString)
            self.combo_print_layout.setCurrentIndex(index if index >= 0 else 0)

            margins = settings['margins']
            l = len(margins)
            if l < 4: margins += [0] * (4 - l)
            self.spin_margin_left.setValue(margins[0])
            self.spin_margin_right.setValue(margins[1])
            self.spin_margin_top.setValue(margins[2])
            self.spin_margin_bottom.setValue(margins[3])

            self.chb_print_font_embed.setChecked(settings['font_embed'])
            self.chb_print_antialias.setChecked(settings['antialias'])
            self.chb_print_print_cw.setChecked(settings['print_cw'])
            self.chb_print_print_clues.setChecked(settings['print_clues'])
            self.chb_print_clear_cw.setChecked(settings['clear_cw'])
            self.chb_print_print_clue_letters.setChecked(settings['print_clue_letters'])
            self.chb_print_print_info.setChecked(settings['print_info'])
            self.chb_print_color_print.setChecked(settings['color_print'])
            self.chb_print_openfile.setChecked(settings['openfile'])
            self.le_print_title.setText(settings['cw_title'])
            self.le_print_clues_title.setText(settings['clues_title'])

            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['header_font']['color']), self.btn_print_header_color.styleSheet(), 'background-color')
            self.btn_print_header_color.setStyleSheet(style)
            font = make_font(settings['header_font']['font_name'], settings['header_font']['font_size'], 
                             settings['header_font']['font_weight'], settings['header_font']['font_italic'])
            style = font_to_stylesheet(font, self.btn_print_header_font.styleSheet())
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['header_font']['color']), style, 'color')
            self.btn_print_header_font.setStyleSheet(style)

            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['info_font']['color']), self.btn_print_info_color.styleSheet(), 'background-color')
            self.btn_print_info_color.setStyleSheet(style)
            font = make_font(settings['info_font']['font_name'], settings['info_font']['font_size'], 
                             settings['info_font']['font_weight'], settings['info_font']['font_italic'])
            style = font_to_stylesheet(font, self.btn_print_info_font.styleSheet())
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['info_font']['color']), style, 'color')
            self.btn_print_info_font.setStyleSheet(style)

            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clue_number_font']['color']), self.btn_print_clue_number_color.styleSheet(), 'background-color')
            self.btn_print_clue_number_color.setStyleSheet(style)
            font = make_font(settings['clue_number_font']['font_name'], settings['clue_number_font']['font_size'], 
                             settings['clue_number_font']['font_weight'], settings['clue_number_font']['font_italic'])
            style = font_to_stylesheet(font, self.btn_print_clue_number_font.styleSheet())
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clue_number_font']['color']), style, 'color')
            self.btn_print_clue_number_font.setStyleSheet(style)

            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clue_font']['color']), self.btn_print_clue_text_color.styleSheet(), 'background-color')
            self.btn_print_clue_text_color.setStyleSheet(style)
            font = make_font(settings['clue_font']['font_name'], settings['clue_font']['font_size'], 
                             settings['clue_font']['font_weight'], settings['clue_font']['font_italic'])
            style = font_to_stylesheet(font, self.btn_print_clue_text_font.styleSheet())
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clue_font']['color']), style, 'color')
            self.btn_print_clue_text_font.setStyleSheet(style)

            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clue_letters_font']['color']), self.btn_print_clue_sizehint_color.styleSheet(), 'background-color')
            self.btn_print_clue_sizehint_color.setStyleSheet(style)
            font = make_font(settings['clue_letters_font']['font_name'], settings['clue_letters_font']['font_size'], 
                             settings['clue_letters_font']['font_weight'], settings['clue_letters_font']['font_italic'])
            style = font_to_stylesheet(font, self.btn_print_clue_sizehint_font.styleSheet())
            style = color_to_stylesheet(QtGui.QColor.fromRgba(settings['clue_letters_font']['color']), style, 'color')
            self.btn_print_clue_sizehint_font.setStyleSheet(style)

        # Updating
        if page is None or page == _('Updating'):
            
            settings = CWSettings.settings['update']
            self._set_spin_value_safe(self.spin_update_period, settings['check_every'])
            self.chb_update_auto.setChecked(settings['auto_update'])
            self.chb_update_major_only.setChecked(settings['only_major_versions'])
            self.chb_update_restart.setChecked(settings['restart_on_update'])
            self.le_update_logfile.setText(settings['logfile'])

        # Sharing
        if page is None or page == 'Sharing':
            
            settings = CWSettings.settings['sharing']
            self.le_sharing_account.setText(settings['account'])
            self.le_sharing_token.setText(settings['bearer_token'])
            self.le_sharing_root.setText(settings['root_folder'])
            self.le_sharing_user.setText(settings['user'])
            self.chb_sharing_use_api_key.setChecked(settings['use_api_key'])
            self.chb_sharing_ownbrowser.setChecked(settings['use_own_browser'])
    
    ## Adds a new word source from 'src' dict or assigns it to an existing item.
    # @param src `dict` dictionary describing a word source; 
    # see dict format in WordSrcDialog docs
    # @param src_item `QtWidgets.QListWidgetItem` source item in SettingsDialog::lw_sources
    # that must be updated; if `None` (default), a new source is added instead
    def addoredit_wordsrc(self, src, src_item=None):
        item = src_item if src_item else QtWidgets.QListWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        item.setText(src['name'])
        item.setData(QtCore.Qt.UserRole, json.dumps(src))
        if src['type'] == 'db':
            iconpic = 'database-3.png'
        elif src['type'] == 'file':
            iconpic = 'file.png'
        else:
            iconpic = 'compose.png'
        item.setIcon(QtGui.QIcon(f"{ICONFOLDER}/{iconpic}"))
        if not src_item:
            item.setCheckState(QtCore.Qt.Checked if src.get('active', False) else QtCore.Qt.Unchecked)
            self.lw_sources.insertItem(0, item)
    
    ## Fires when the dialog is shown: updates controls from current settings.
    def showEvent(self, event):        
        # read settings
        self.from_settings()
    
    ## Fires when a config category is selected in the category tree.
    @QtCore.pyqtSlot()        
    def on_tree_select(self):
        item = self.tree.currentItem()
        if not item: return
        txt = item.text(0)
        if txt in SettingsDialog.PARENT_PAGES:
            item.setExpanded(True)
            self.tree.setCurrentItem(item.child(0))
        else:
            self.stacked.setCurrentIndex(SettingsDialog.PAGES.index(txt))       
            
    ## Default button handler: Restores default settings for current page or all pages.
    @QtCore.pyqtSlot(bool) 
    def on_btn_defaults(self, checked):
        msbox = MsgBox(_('Press YES to restore defaults only for current page and YES TO ALL to restore all default settings'), self,
            _('Restore defaults'), 'ask', ['yes', 'yesall', 'cancel'], execnow=False)
        msbox.exec()
        clk = msbox.clickedButton()
        if clk and (clk.text() in (MSGBOX_BUTTONS['yes'][0], MSGBOX_BUTTONS['yesall'][0])):
            self.from_settings(self.default_settings, self.tree.currentItem().text(0) if clk.text() == MSGBOX_BUTTONS['yes'][0] else None)

    ## Load button handler: Loads settings from a file for current page or all pages.
    @QtCore.pyqtSlot(bool) 
    def on_btn_load(self, checked):
        msbox = MsgBox(_('Press YES to load settings only for current page and YES TO ALL to load all settings'), self,
            _('Load defaults'), 'ask', ['yes', 'yesall', 'cancel'], execnow=False)
        msbox.exec()
        clk = msbox.clickedButton()
        if not clk or (not clk.text() in (MSGBOX_BUTTONS['yes'][0], MSGBOX_BUTTONS['yesall'][0])): return

        selected_path = QtWidgets.QFileDialog.getOpenFileName(self, _('Select file'), os.getcwd(), _('Settings files (*.pxjson)'))
        if not selected_path[0]: return
        selected_path = selected_path[0].replace('/', os.sep)
        settings = CWSettings.validate_file(selected_path)
        if not settings: 
            MsgBox(_("File '{}' has a wrong format or incomplete settings!").format(selected_path), self, _('Error'), 'error')
            return
        self.from_settings(settings, self.tree.currentItem().text(0) if clk.text() == MSGBOX_BUTTONS['yes'][0] else None)

    ## Save button handler: Saves current settings to a file.
    @QtCore.pyqtSlot(bool) 
    def on_btn_save(self, checked):
        selected_path = QtWidgets.QFileDialog.getSaveFileName(self, _('Select file'), os.path.join(os.getcwd(), 'settings.pxjson'), _('Settings files (*.pxjson)'))
        if not selected_path[0]: return
        selected_path = selected_path[0].replace('/', os.sep)
        CWSettings.settings = self.to_settings()
        CWSettings.save_to_file(selected_path)

    ## When a log combo item is selected.
    @QtCore.pyqtSlot(int)
    def on_combo_log(self, index):
        if index == 2:
            selected_path = QtWidgets.QFileDialog.getSaveFileName(self, _('Select file'), os.getcwd(), _('All files (*.*)'))
            if selected_path[0]:
                self.combo_log.setCurrentText(selected_path[0].replace('/', os.sep))
       
    ## When a word source is double-clicked, edit it.
    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def on_lw_sources_dblclick(self, item):
        self.on_act_src_edit(False)
            
    ## When SettingsDialog::chb_maxfetch is checked or unchecked.
    @QtCore.pyqtSlot(int)
    def on_chb_maxfetch_checked(self, state):
        self.spin_maxfetch.setEnabled(bool(state))
        
    ## Moves selected word source up one position.
    @QtCore.pyqtSlot(bool)        
    def on_act_src_up(self, checked):
        item = self.lw_sources.currentItem()
        if not item: return
        row = self.lw_sources.row(item)
        if not row: return
        self.lw_sources.insertItem(row - 1, self.lw_sources.takeItem(row))
        self.lw_sources.setCurrentRow(row - 1)
    
    ## Moves selected word source down one position.
    @QtCore.pyqtSlot(bool)        
    def on_act_src_down(self, checked):
        item = self.lw_sources.currentItem()
        if not item: return
        row = self.lw_sources.row(item)
        if row == (self.lw_sources.count() - 1): return
        self.lw_sources.insertItem(row + 1, self.lw_sources.takeItem(row))
        self.lw_sources.setCurrentRow(row + 1)
    
    ## Adds a new word source.
    # @see WordSrcDialog, SettingsDialog::addoredit_wordsrc()
    @QtCore.pyqtSlot(bool)        
    def on_act_src_add(self, checked):
        dia_src = WordSrcDialog()
        if not dia_src.exec(): return
        self.addoredit_wordsrc(dia_src.src)
    
    ## Deletes the selected word source.
    @QtCore.pyqtSlot(bool)        
    def on_act_src_remove(self, checked):
        row = self.lw_sources.currentRow()
        if row < 0: return
        self.lw_sources.takeItem(row)
    
    ## Edits the selected word source.
    # @see WordSrcDialog, SettingsDialog::addoredit_wordsrc()
    @QtCore.pyqtSlot(bool)        
    def on_act_src_edit(self, checked):
        item = self.lw_sources.currentItem()
        if not item: return
        try:
            src = json.loads(item.data(QtCore.Qt.UserRole))
            if not src or not isinstance(src, dict):
                print(_('No user data in src!'))
                return
            b_active = src['active']
            dia_src = WordSrcDialog(src)
            if not dia_src.exec(): return
            dia_src.src['active'] = b_active
            self.addoredit_wordsrc(dia_src.src, item)
        except Exception as err:
            print(err)
            return
    
    ## Clears all current word sources.
    @QtCore.pyqtSlot(bool)        
    def on_act_src_clear(self, checked):
        self.lw_sources.clear()

    ## Moves selected clues column up one position.
    @QtCore.pyqtSlot(bool)        
    def on_act_cluecol_up(self, checked):
        item = self.lw_clues_cols.currentItem()
        if not item: return
        row = self.lw_clues_cols.row(item)
        if row < 2: return
        self.lw_clues_cols.insertItem(row - 1, self.lw_clues_cols.takeItem(row))
        self.lw_clues_cols.setCurrentRow(row - 1)
    
    ## Moves selected clues column down one position.
    @QtCore.pyqtSlot(bool)
    def on_act_cluecol_down(self, checked):
        item = self.lw_clues_cols.currentItem()
        if not item: return
        row = self.lw_clues_cols.row(item)
        if row == 0 or row == (self.lw_clues_cols.count() - 1): return
        self.lw_clues_cols.insertItem(row + 1, self.lw_clues_cols.takeItem(row))
        self.lw_clues_cols.setCurrentRow(row + 1)
        
    ## Fires when any of the color select buttons is clicked.
    @QtCore.pyqtSlot(bool)        
    def on_color_btn_clicked(self, checked):
        btn = self.sender()
        if not btn: return
        # get current color f button
        style = btn.styleSheet()
        #print(f"BTN '{btn.objectName()}': {style}")
        color = color_from_stylesheet(style, 'background-color')
        dia_colorpicker = QtWidgets.QColorDialog(QtGui.QColor(color))
        if dia_colorpicker.exec():
            btn.setStyleSheet(color_to_stylesheet(dia_colorpicker.selectedColor(), style, 'background-color'))
            # set font btn color
            font_btn = None
            if btn == self.btn_numberscolor:
                font_btn = self.btn_numbersfont
            elif btn == self.btn_cell_normal_fg_color:
                font_btn = self.btn_cell_normal_font
            elif btn == self.btn_cell_hilite_fg_color:
                font_btn = self.btn_cell_hilite_font
            elif btn == self.btn_print_header_color:
                font_btn = self.btn_print_header_font
            elif btn == self.btn_print_info_color:
                font_btn = self.btn_print_info_font
            elif btn == self.btn_print_clue_number_color:
                font_btn = self.btn_print_clue_number_font
            elif btn == self.btn_print_clue_text_color:
                font_btn = self.btn_print_clue_text_font
            elif btn == self.btn_print_clue_sizehint_color:
                font_btn = self.btn_print_clue_sizehint_font
            if font_btn:
                font_btn.setStyleSheet(color_to_stylesheet(dia_colorpicker.selectedColor(), font_btn.styleSheet(), 'color'))
            
    ## Fires when any of the font select buttons is clicked.
    @QtCore.pyqtSlot(bool)        
    def on_font_btn_clicked(self, checked):
        btn = self.sender()
        if not btn: return
        # get btn font
        style = btn.styleSheet()
        #print(f"BTN '{btn.objectName()}': {style}")
        font = font_from_stylesheet(style)        
        # show font dialog
        new_font = QtWidgets.QFontDialog.getFont(font, self, _('Choose font'))
        if new_font[1]:
            btn.setStyleSheet(font_to_stylesheet(new_font[0], style))

    ## Checks / unchecks all checkboxes for Google languages.
    @QtCore.pyqtSlot(int)        
    def on_chb_google_lang_all(self, state):
        if state == QtCore.Qt.Checked or state == QtCore.Qt.Unchecked:
            self.chb_google_lang_all.stateChanged.disconnect()
            self.lw_google_lang.itemChanged.disconnect()
            for i in range(self.lw_google_lang.count()):
                self.lw_google_lang.item(i).setCheckState(state)
            self.chb_google_lang_all.stateChanged.connect(self.on_chb_google_lang_all)
            self.lw_google_lang.itemChanged.connect(self.on_lw_google_lang_changed)

    ## Checks / unchecks all checkboxes for Google interface languages.
    @QtCore.pyqtSlot(int)        
    def on_chb_google_interface_lang_all(self, state):
        if state == QtCore.Qt.Checked or state == QtCore.Qt.Unchecked:
            self.chb_google_interface_lang_all.stateChanged.disconnect()
            self.lw_google_interface_lang.itemChanged.disconnect()
            for i in range(self.lw_google_interface_lang.count()):
                self.lw_google_interface_lang.item(i).setCheckState(state)
            self.chb_google_interface_lang_all.stateChanged.connect(self.on_chb_google_interface_lang_all)
            self.lw_google_interface_lang.itemChanged.connect(self.on_lw_google_interface_lang_changed)

    ## Checks / unchecks all checkboxes for Google locations.
    @QtCore.pyqtSlot(int)        
    def on_chb_google_geo_all(self, state):
        if state == QtCore.Qt.Checked or state == QtCore.Qt.Unchecked:
            self.chb_google_geo_all.stateChanged.disconnect()
            self.lw_google_geo.itemChanged.disconnect()
            for i in range(self.lw_google_geo.count()):
                self.lw_google_geo.item(i).setCheckState(state)
            self.chb_google_geo_all.stateChanged.connect(self.on_chb_google_geo_all)
            self.lw_google_geo.itemChanged.connect(self.on_lw_google_geo_changed)

    ## Sets the tristate for the ALL checkbox when a Google language is checked / unchecked.
    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)        
    def on_lw_google_lang_changed(self, item):
        self.chb_google_lang_all.stateChanged.disconnect()
        ch = 0
        unch = 0
        for i in range(self.lw_google_lang.count()):
            item = self.lw_google_lang.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                ch += 1
            else:
                unch += 1
        if ch == 0:
            self.chb_google_lang_all.setCheckState(QtCore.Qt.Unchecked)
        elif unch == 0:
            self.chb_google_lang_all.setCheckState(QtCore.Qt.Checked)
        else:
            self.chb_google_lang_all.setCheckState(QtCore.Qt.PartiallyChecked)
        self.chb_google_lang_all.stateChanged.connect(self.on_chb_google_lang_all)

    ## Sets the tristate for the ALL checkbox when a Google interface language is checked / unchecked.
    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)        
    def on_lw_google_interface_lang_changed(self, item):
        self.chb_google_interface_lang_all.stateChanged.disconnect()
        ch = 0
        unch = 0
        for i in range(self.lw_google_interface_lang.count()):
            item = self.lw_google_interface_lang.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                ch += 1
            else:
                unch += 1
        if ch == 0:
            self.chb_google_interface_lang_all.setCheckState(QtCore.Qt.Unchecked)
        elif unch == 0:
            self.chb_google_interface_lang_all.setCheckState(QtCore.Qt.Checked)
        else:
            self.chb_google_interface_lang_all.setCheckState(QtCore.Qt.PartiallyChecked)
        self.chb_google_interface_lang_all.stateChanged.connect(self.on_chb_google_interface_lang_all)

    ## Sets the tristate for the ALL checkbox when a Google location is checked / unchecked.
    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)        
    def on_lw_google_geo_changed(self, item):
        self.chb_google_geo_all.stateChanged.disconnect()
        ch = 0
        unch = 0
        for i in range(self.lw_google_geo.count()):
            item = self.lw_google_geo.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                ch += 1
            else:
                unch += 1
        if ch == 0:
            self.chb_google_geo_all.setCheckState(QtCore.Qt.Unchecked)
        elif unch == 0:
            self.chb_google_geo_all.setCheckState(QtCore.Qt.Checked)
        else:
            self.chb_google_geo_all.setCheckState(QtCore.Qt.PartiallyChecked)
        self.chb_google_geo_all.stateChanged.connect(self.on_chb_google_geo_all)

    ## Sets the default resolution value ('Export' page).
    @QtCore.pyqtSlot() 
    def on_btn_export_auto_resolution_img(self):
        self.spin_export_resolution_img.setValue(72)

    ## Sets the default PDF resolution value ('Export' page).
    @QtCore.pyqtSlot() 
    def on_btn_export_auto_resolution_pdf(self):
        self.spin_export_resolution_pdf.setValue(1200)

    ## Registers / unregisters file associations.
    # @see utils::register_file_types()
    @QtCore.pyqtSlot(bool)
    def on_act_register_associations(self, checked):
        state = self.act_register_associations.data()
        ok = register_file_types(register=(state==0))
        if ok:
            self.act_register_associations.setData(1 if state==0 else 0)
            self.act_register_associations.setText(_('Register file associations') if state==1 else _('Unregister file associations'))
            self.btn_register_associations.setStyleSheet(f"background-color: {'#7FFFD4' if state==0 else '#DC143C'}; border: none;")
        else:
            MsgBox(_('Could not assign file associations!'), self, _('Error'), 'error')

    ## Enables / disables proxy related controls when the checkbox is checked / unchecked.
    @QtCore.pyqtSlot(int)        
    def on_chb_system_proxy(self, state):
        self.le_http_proxy.setEnabled(state==QtCore.Qt.Unchecked)
        self.le_https_proxy.setEnabled(state==QtCore.Qt.Unchecked)

    ## Enables / disables a 3d-party plugin when checked / unchecked.
    @QtCore.pyqtSlot('QStandardItem*') 
    def on_model_plugins_3party_changed(self, item):
        parent = item.parent()
        if not item.isCheckable() or not parent: return
        checked = bool(item.checkState())       
        # iterate children
        for i in range(parent.rowCount()):
            if i != item.row():
                parent.child(i, 1).setEnabled(checked)
        
# ******************************************************************************** #
# *****          CwTable
# ******************************************************************************** # 

## @brief Crossword grid class (based on `QtWidgets.QTableWidget`).
# Custom implementation handles key events (like Del, Backspace, etc.) 
class CwTable(QtWidgets.QTableWidget):

    ## Constructor.
    # @param on_key `callable` callback for key release event
    # @param parent `QtWidgets.QWidget` parent widget
    def __init__(self, on_key=None, parent: QtWidgets.QWidget=None):
        ## Stored callback for key release event
        self.on_key = on_key
        super().__init__(parent)
        
    ## Key release event handler: call the stored callback.
    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        #super().keyReleaseEvent(event)
        if self.on_key: self.on_key(event)

# ******************************************************************************** #
# *****          ClickableLabel
# ******************************************************************************** # 

## Label with mouse click event handler. Used in gui::MainWindow::statusbar_l2.
class ClickableLabel(QtWidgets.QLabel):

    ## single click signal
    clicked = QtCore.pyqtSignal(QtGui.QMouseEvent)
    ## double click signal
    dblclicked = QtCore.pyqtSignal(QtGui.QMouseEvent)

    ## Constructor.
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, parent: QtWidgets.QWidget=None, flags: QtCore.Qt.WindowFlags=QtCore.Qt.WindowFlags()):
        super().__init__(parent)

    ## Mouse press (click) event handler: emit `clicked` signal.
    def mousePressEvent(self, event):
        self.clicked.emit(event)

    ## Mouse double-click event handler: emit `dblclicked` signal.
    def mouseDoubleClickEvent(self, event):
        self.dblclicked.emit(event)
        
        
# ******************************************************************************** #
# *****          CrosswordMenu
# ******************************************************************************** #    

## Context menu for crossword grid: contains core actions for ease of use.        
class CrosswordMenu(QtWidgets.QMenu):
    
    ## Constructor.
    # @param mainwindow `QtWidgets.QMainWindow` pointer to gui::MainWindow instance
    # @param on_triggered `callable` callback for the `triggered` signal (when an action is triggered)
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    def __init__(self, mainwindow, on_triggered=None, parent=None):
        self.mainwindow = mainwindow
        super().__init__(parent=parent)
        self.initActions()
        if on_triggered: self.triggered.connect(on_triggered)
        
    ## Adds actions to context menu.
    def initActions(self):
        self.addAction(self.mainwindow.act_edit)
        self.addSeparator()
        self.addAction(self.mainwindow.act_clear)
        self.addAction(self.mainwindow.act_clear_wd)
        self.addAction(self.mainwindow.act_erase_wd)
        self.addSeparator()
        self.addAction(self.mainwindow.act_suggest)
        self.addAction(self.mainwindow.act_lookup)
        self.addAction(self.mainwindow.act_editclue)
        self.addSeparator()
        self.addAction(self.mainwindow.act_addrow)
        self.addAction(self.mainwindow.act_delrow)
        self.addSeparator()
        self.addAction(self.mainwindow.act_addcol)        
        self.addAction(self.mainwindow.act_delcol)
        self.addSeparator()
        self.addAction(self.mainwindow.act_reflect)
   

# ******************************************************************************** #
# *****          WordSuggestDialog
# ******************************************************************************** #  
    
## Small dialog window to look for words matching a given pattern among the word sources.
class WordSuggestDialog(BasicDialog):
    
    ## Constructor.
    # @param mainwindow `QtWidgets.QMainWindow` pointer to gui::MainWindow instance
    # @param word `str` the word pattern to look up in suggestions, e.g. 'f_th__'
    # @param word_editable `bool` whether the word string can be edited directly in the dialog
    # (default = False)
    # @param getresults `callable` pointer to function that retrieves word suggestions.
    # This function takes one argument (the word pattern string) and returns suggestions 
    # as a list of strings.
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, mainwindow, word='', word_editable=False, getresults=None, 
                parent=None, flags=QtCore.Qt.WindowFlags()):
        ## `QtWidgets.QMainWindow` pointer to gui::MainWindow instance 
        self.mainwindow = mainwindow
        ## `str` suggestions sort order: 'A' = ascending, 'D' = descending
        self.sortdir = ''     
        ## `str` word pattern to find suggestions for  
        self.word = word
        ## `bool` whether the word string can be edited directly in the dialog
        self.word_editable = word_editable
        ## `callable` pointer to function that retrieves word suggestions
        self.getresults = getresults 
        ## `list` list of retrieved suggestions (word strings)
        self.results = []
        ## `str` the selected word (from the suggested list)
        self.selected = ''
        super().__init__(None, _('Word Lookup'), 'magic-wand.png', 
              parent, flags)

    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout()

        self.layout_top = QtWidgets.QHBoxLayout()
        self.l_word = QtWidgets.QLabel(_('Suggestions for:'))
        self.le_word = QtWidgets.QLineEdit('')
        self.le_word.setToolTip(_("Use '{}' as blank symbol").format(BLANK))
        self.le_word.textEdited.connect(self.on_word_edited)
        self.layout_top.addWidget(self.l_word)
        self.layout_top.addWidget(self.le_word)
        self.layout_center = QtWidgets.QHBoxLayout()
        self.lw_words = QtWidgets.QListWidget()
        self.lw_words.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.lw_words.itemDoubleClicked.connect(self.on_word_dblclick)
        self.tb_actions = QtWidgets.QToolBar()
        self.tb_actions.setOrientation(QtCore.Qt.Vertical)
        self.act_refresh = self.tb_actions.addAction(QtGui.QIcon(f"{ICONFOLDER}/repeat.png"), _('Refresh'))
        self.act_refresh.triggered.connect(self.on_act_refresh)
        self.act_sort = self.tb_actions.addAction(QtGui.QIcon(f"{ICONFOLDER}/sort.png"), _('Sort'))
        self.act_sort.triggered.connect(self.on_act_sort)
        self.act_shuffle = self.tb_actions.addAction(QtGui.QIcon(f"{ICONFOLDER}/shuffle.png"), _('Shuffle'))
        self.act_shuffle.triggered.connect(self.on_act_shuffle)
        self.act_source_config = self.tb_actions.addAction(QtGui.QIcon(f"{ICONFOLDER}/database-3.png"), _('Sources...'))
        self.act_source_config.triggered.connect(self.on_act_source_config)
        self.layout_center.addWidget(self.lw_words)
        self.layout_center.addWidget(self.tb_actions)
        self.l_count = QtWidgets.QLabel('')
        self.ch_truncate = QtWidgets.QCheckBox(_('Truncate'))
        self.ch_truncate.setToolTip(_('Uncheck to retrieve all results with no truncation'))
        self.ch_truncate.setChecked(True)
        self.ch_truncate.toggled.connect(self.on_ch_truncate)
        self.layout_lower = QtWidgets.QHBoxLayout()
        self.layout_lower.addWidget(self.l_count)
        self.layout_lower.addWidget(self.ch_truncate)

        self.layout_controls.addLayout(self.layout_top)
        self.layout_controls.addLayout(self.layout_center)
        self.layout_controls.addLayout(self.layout_lower)
        self.init(self.word, self.word_editable)

    ## Fires when the dialog shows up.
    def showEvent(self, event):     
        self.selected = ''
        self.old_truncate = self.mainwindow.cw.wordsource.max_fetch
        super().showEvent(event) 

    ## Fires when the dialog closes.
    def closeEvent(self, event):
        self.mainwindow.cw.wordsource.max_fetch = self.old_truncate
        super().closeEvent(event)

    ## Creates and initializes members.
    def init(self, word='', word_editable=False):
        self.selected = ''        
        self.word = word
        self.word_editable = word_editable
        self.le_word.setText(self.word)
        self.le_word.setEnabled(self.word_editable)
        self.fill_words()

    ## Checks that a suggestion is selected before quitting.
    def validate(self): 
        self.selected = ''
        if self.lw_words.currentItem() is None:
            MsgBox(_('No word selected!'), self, _('Error'), 'error')
            return False
        self.selected = self.lw_words.currentItem().text()
        return True

    ## Retrieves suggestions and fills them into the list box.
    def fill_words(self):
        self.lw_words.clear()
        cnt = 0
        if self.getresults:
            self.results = self.getresults(self.word)
            if self.results:
                cnt = len(self.results)
                self.lw_words.addItems(self.results)
                self.sort_words()
        self.l_count.setText(_("{} result{}").format(cnt, ('s' if cnt and cnt > 1 else '')))
        self.update_actions()

    ## Enables / disables actions depending on the number of returned suggestions.
    def update_actions(self):
        b_words = bool(self.results)
        self.act_sort.setEnabled(b_words)
        self.act_shuffle.setEnabled(b_words)
        self.act_source_config.setEnabled(not self.mainwindow is None)

    ## Sorts the suggestions in the list box.
    # @param order `str` sort order: 'A' = ascending, 'D' = descending, 
    # 'toggle' = toggle order, empty = use WordSuggestDialog::sortdir
    def sort_words(self, order=''):
        if not self.lw_words.count(): return
        if not self.sortdir:
            self.lw_words.sortItems(QtCore.Qt.DescendingOrder if order == 'D' else QtCore.Qt.AscendingOrder)
            self.sortdir = 'D' if order == 'D' else 'A'
        else:
            if order == 'A' or (self.sortdir == 'A' and not order) or (self.sortdir == 'D' and order=='toggle'):
                self.lw_words.sortItems(QtCore.Qt.AscendingOrder)
                self.sortdir = 'A'
            else:
                self.lw_words.sortItems(QtCore.Qt.DescendingOrder)
                self.sortdir = 'D'

    ## When the 'Truncate' checkbox is (un)checked.
    @QtCore.pyqtSlot(bool) 
    def on_ch_truncate(self, checked):
        self.mainwindow.cw.wordsource.max_fetch = CWSettings.settings['wordsrc']['maxres'] if checked else None
        self.fill_words()

    ## When the word pattern is edited: store the new pattern.
    @QtCore.pyqtSlot(str) 
    def on_word_edited(self, text):
        self.word = text  

    ## When a suggestion is double-clicked: select it and quit.
    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)         
    def on_word_dblclick(self, item):
        self.on_btn_OK_clicked()

    ## Refresh action handler: update suggestions.
    @QtCore.pyqtSlot(bool)        
    def on_act_refresh(self, checked):
        self.fill_words()

    ## Sort action handler: sort suggestions.
    @QtCore.pyqtSlot(bool)        
    def on_act_sort(self, checked):
        self.sort_words('toggle')

    ## Shuffle action handler: shuffle suggestions randomly.
    @QtCore.pyqtSlot(bool)        
    def on_act_shuffle(self, checked):
        if not self.results: return
        np.random.seed()
        np.random.shuffle(self.results)
        self.lw_words.clear()
        self.lw_words.addItems(self.results)

    ## Word source settings action: show word source management page in settings dialog.
    @QtCore.pyqtSlot(bool)        
    def on_act_source_config(self, checked):
        self.mainwindow.on_act_wsrc(False)


# ******************************************************************************** #
# *****          PrintPreviewDialog
# ******************************************************************************** #  
    
## Print preview window to preview crossword / clues and configure printing.
class PrintPreviewDialog(BasicDialog):
    
    ## Constructor.
    # @param printer `QtPrintSupport.QPrinter` selected printer
    # @param mainwindow `QtWidgets.QMainWindow` pointer to gui::MainWindow instance
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, printer, mainwindow, parent=None, flags=QtCore.Qt.WindowFlags()):
        # printer must be valid
        if not printer.isValid():
            raise Exception(_('No valid printer!'))
        # crossword instance must be valid
        if getattr(mainwindow, 'cw', None) is None:
            raise Exception(_('Crossword not available!'))
        ## `QtPrintSupport.QPrinter` selected printer
        self.printer = printer
        ## `QtWidgets.QMainWindow` pointer to gui::MainWindow instance
        self.mainwindow = mainwindow
        super().__init__(None, _("Printing to: {}").format(self.printer.printerName()), 'binoculars.png', 
              parent, flags)

    ## Update preview on dialog show.
    def showEvent(self, event):      
        event.accept()
        self.ppreview.updatePreview()

    ## Shortcut method to create a 'tab' (layout) with a caption and widgets.
    ## @param name `str` name of caption label
    ## @param caption `str` caption string
    ## @param widgets `iterable` list of widgets to add to layout
    ## @returns `QtWidgets.QVBoxLayout` layout with widgets and caption label
    def _make_labelled_widgets(self, name, caption, widgets):
        layout = QtWidgets.QVBoxLayout()
        self.__dict__[f"l_{name}"] = QtWidgets.QLabel(caption)
        label = self.__dict__[f"l_{name}"]
        label.setAlignment(QtCore.Qt.AlignHCenter)
        label.setStyleSheet('font-size: 9pt; font-weight: bold')
        layout.addWidget(label)
        layout_bottom = QtWidgets.QHBoxLayout()
        for w in widgets:
            layout_bottom.addWidget(w)
        layout.addLayout(layout_bottom)
        return layout
        
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout()       

        # top 'toolbar'
        self.tb_main = QtWidgets.QWidget()
        self.layout_tb_main = QtWidgets.QHBoxLayout()

        self.combo_page_size = QtWidgets.QComboBox()
        printer_info = QtPrintSupport.QPrinterInfo(self.printer)
        pagesz_ids = list(sorted(set(pgsz.id() for pgsz in printer_info.supportedPageSizes() if pgsz.isValid())))
        for szid in pagesz_ids:  
            pgsz = QtGui.QPageSize(szid)
            if pgsz.isValid():
                self.combo_page_size.addItem(pgsz.name(), int(szid))
        self.combo_page_size.setEditable(False)
        self.combo_page_size.setCurrentIndex(0)
        self.combo_page_size.activated.connect(self.on_combo_page_size)
        self.layout_pagesize = self._make_labelled_widgets('pagesize', _('Page Size'), [self.combo_page_size])
        self.layout_tb_main.addLayout(self.layout_pagesize)

        self.combo_view = QtWidgets.QComboBox()
        self.combo_view.addItems([_('Single'), _('Two'), _('All')])
        self.combo_view.setEditable(False)
        self.combo_view.setCurrentIndex(0)
        self.combo_view.activated.connect(self.on_combo_view)
        self.layout_view = self._make_labelled_widgets('view', _('View'), [self.combo_view])
        self.layout_tb_main.addLayout(self.layout_view)

        self.combo_layout = QtWidgets.QComboBox()
        self.combo_layout.addItems([_('Auto'), _('Portrait'), _('Landscape')])
        self.combo_layout.setEditable(False)
        self.combo_layout.setCurrentIndex(0)
        self.combo_layout.activated.connect(self.on_combo_layout)
        self.layout_layout = self._make_labelled_widgets('layout', _('Layout'), [self.combo_layout])
        self.layout_tb_main.addLayout(self.layout_layout)

        self.btn_fit_width = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/width.png"), _('Zoom to width'), None)
        self.btn_fit_width.setToolTip(_('Zoom to window width'))
        self.btn_fit_width.clicked.connect(self.on_btn_fit_width)
        self.btn_fit_all = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/fitsize.png"), _('Fit in window'), None)
        self.btn_fit_all.setToolTip(_('Zoom to window size'))
        self.btn_fit_all.clicked.connect(self.on_btn_fit_all)
        self.slider_zoom = QtWidgets.QSlider()
        self.slider_zoom.setOrientation(QtCore.Qt.Horizontal)
        self.slider_zoom.setRange(10, 500)
        self.slider_zoom.setSingleStep(1)
        self.slider_zoom.setPageStep(10)
        self.slider_zoom.setToolTip(_('Zoom %'))
        self.slider_zoom.valueChanged.connect(self.on_zoom_changed)
        self.layout_fit = self._make_labelled_widgets('fit', _('Fit & Zoom'), [self.btn_fit_width, self.btn_fit_all, self.slider_zoom])
        self.layout_tb_main.addLayout(self.layout_fit)

        self.combo_color = QtWidgets.QComboBox()
        self.combo_color.addItems([_('Greyscale'), _('Color')])
        self.combo_color.setEditable(False)
        self.combo_color.setCurrentIndex(1)
        self.combo_color.activated.connect(self.on_combo_color)
        self.layout_color = self._make_labelled_widgets('color', _('Color Print'), [self.combo_color])
        self.layout_tb_main.addLayout(self.layout_color)

        self.le_margin_l = QtWidgets.QLineEdit('0')
        self.le_margin_l.setMaximumWidth(20)
        self.le_margin_l.setToolTip(_('Left, mm'))
        self.le_margin_l.textChanged.connect(self.on_margins_changed)
        self.le_margin_r = QtWidgets.QLineEdit('0')
        self.le_margin_r.setMaximumWidth(20)
        self.le_margin_r.setToolTip(_('Right, mm'))
        self.le_margin_r.textChanged.connect(self.on_margins_changed)
        self.le_margin_t = QtWidgets.QLineEdit('0')
        self.le_margin_t.setMaximumWidth(20)
        self.le_margin_t.setToolTip(_('Top, mm'))
        self.le_margin_t.textChanged.connect(self.on_margins_changed)
        self.le_margin_b = QtWidgets.QLineEdit('0')
        self.le_margin_b.setMaximumWidth(20)
        self.le_margin_b.setToolTip(_('Bottom, mm'))
        self.le_margin_b.textChanged.connect(self.on_margins_changed)
        self.layout_margins = self._make_labelled_widgets('margins', _('Margins'), [self.le_margin_l, self.le_margin_r, self.le_margin_t, self.le_margin_b])
        self.layout_tb_main.addLayout(self.layout_margins)

        self.layout_tb_main.addSpacing(20) 

        self.btn_settings = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/settings-5.png"), _('Settings'), None)
        self.btn_settings.setToolTip(_('Configure additional printing settings'))
        self.btn_settings.clicked.connect(self.on_btn_settings)
        self.layout_tb_main.addWidget(self.btn_settings)

        self.layout_controls.addLayout(self.layout_tb_main)
        
        # central preview widget
        self.layout_center = QtWidgets.QHBoxLayout()
        self.ppreview = QtPrintSupport.QPrintPreviewWidget(self.printer)        
        self.layout_center.addWidget(self.ppreview)
        self.layout_controls.addLayout(self.layout_center)

        self.update_controls()

    ## Updates the printer settings from guisettings::CWSettings::settings and 
    # updates the controls in toolbar and preview according to current
    # printer settings.
    def update_controls(self):
        # page size
        self.update_page_size()
        # view mode
        self.combo_view.activated.disconnect()
        self.combo_view.setCurrentIndex(int(self.ppreview.viewMode()))
        self.combo_view.activated.connect(self.on_combo_view)
        # layout
        index = self.combo_layout.findText(CWSettings.settings['printing']['layout'], QtCore.Qt.MatchFixedString)
        self.combo_layout.setCurrentIndex(index if index >= 0 else 0)
        self.on_combo_layout(self.combo_layout.currentIndex())
        # fit
        self.slider_zoom.valueChanged.disconnect()
        self.slider_zoom.setValue(self.ppreview.zoomFactor() * 100.0)
        self.slider_zoom.valueChanged.connect(self.on_zoom_changed)
        # color
        self.combo_color.setCurrentIndex(int(CWSettings.settings['printing']['color_print']))
        self.on_combo_color(self.combo_color.currentIndex())
        # margins
        margins = CWSettings.settings['printing']['margins']
        self.printer.setPageMargins(margins[0], margins[2], margins[1], margins[3], QtPrintSupport.QPrinter.Millimeter)
        self.update_margins()
        
        self.ppreview.updatePreview()

    ## Updates the page size from the one selected in the page size combo.
    def update_page_size(self):
        old_index = self.combo_page_size.currentIndex()
        pgsize = int(self.printer.pageLayout().pageSize().id())
        self.combo_page_size.activated.disconnect()
        item_count = self.combo_page_size.count()
        for i in range(item_count):
            if self.combo_page_size.itemData(i) == pgsize:         
                self.combo_page_size.setCurrentIndex(i)                
                break
        else:
            if old_index < 0 and item_count > 0:
                self.combo_page_size.setCurrentIndex(0)
        self.combo_page_size.activated.connect(self.on_combo_page_size)

    ## Sets the page margins according to the values in the margin edit fields.
    def update_margins(self):
        # update margin values in fields                                       
        self.le_margin_l.textChanged.disconnect()
        self.le_margin_r.textChanged.disconnect()
        self.le_margin_t.textChanged.disconnect()
        self.le_margin_b.textChanged.disconnect()
        margins = self.printer.pageLayout().margins(QtGui.QPageLayout.Millimeter)
        self.le_margin_l.setText(str(int(margins.left())))
        self.le_margin_r.setText(str(int(margins.right())))
        self.le_margin_t.setText(str(int(margins.top())))
        self.le_margin_b.setText(str(int(margins.bottom())))
        self.le_margin_l.textChanged.connect(self.on_margins_changed)
        self.le_margin_r.textChanged.connect(self.on_margins_changed)
        self.le_margin_t.textChanged.connect(self.on_margins_changed)
        self.le_margin_b.textChanged.connect(self.on_margins_changed)

    ## Saves the current page config to the global settings.
    def write_settings(self):
        settings = CWSettings.settings['printing']

        margins = self.printer.pageLayout().margins(QtGui.QPageLayout.Millimeter)
        settings['margins'][0] = int(margins.left())
        settings['margins'][1] = int(margins.right())
        settings['margins'][2] = int(margins.top())
        settings['margins'][3] = int(margins.bottom())
        settings['layout'] = self.combo_layout.currentText().lower()
        settings['color_print'] = bool(self.combo_color.currentIndex())

        CWSettings.save_to_file()

    ## When a new page size is selected in the combo box.
    @QtCore.pyqtSlot(int)
    def on_combo_page_size(self, index):
        if self.printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId(self.combo_page_size.itemData(index)))):
            self.ppreview.updatePreview()
        else:
            self.update_page_size()

    ## When a view mode is selected in the view combo box.
    @QtCore.pyqtSlot(int)
    def on_combo_view(self, index):
        self.ppreview.setViewMode(QtPrintSupport.QPrintPreviewWidget.ViewMode(index))

    ## When a layout is selected in the layout combo box.
    @QtCore.pyqtSlot(int)
    def on_combo_layout(self, index):
        if index == 0:
            # auto rotate
            self.ppreview.setOrientation(QtPrintSupport.QPrinter.Portrait if self.mainwindow.cw.words.height > self.mainwindow.cw.words.width else QtPrintSupport.QPrinter.Landscape)
        elif index == 1:
            # portrait
            self.ppreview.setOrientation(QtPrintSupport.QPrinter.Portrait)
        else:
            # landscape
            self.ppreview.setOrientation(QtPrintSupport.QPrinter.Landscape)

    ## Scale page to width.
    @QtCore.pyqtSlot()
    def on_btn_fit_width(self):
        self.ppreview.setZoomMode(QtPrintSupport.QPrintPreviewWidget.FitToWidth)
        self.slider_zoom.valueChanged.disconnect()
        self.slider_zoom.setValue(self.ppreview.zoomFactor() * 100.0)
        self.slider_zoom.valueChanged.connect(self.on_zoom_changed)

    ## Scale page to fit in window.
    @QtCore.pyqtSlot()
    def on_btn_fit_all(self):
        self.ppreview.setZoomMode(QtPrintSupport.QPrintPreviewWidget.FitInView)
        self.slider_zoom.valueChanged.disconnect()
        self.slider_zoom.setValue(self.ppreview.zoomFactor() * 100.0)
        self.slider_zoom.valueChanged.connect(self.on_zoom_changed)

    ## Set print color mode.
    @QtCore.pyqtSlot(int)
    def on_combo_color(self, index):
        self.printer.setColorMode(QtPrintSupport.QPrinter.ColorMode(index))
        self.ppreview.updatePreview()

    ## Set scale factor.
    @QtCore.pyqtSlot(int)
    def on_zoom_changed(self, value):
        if not self.slider_zoom.hasFocus(): return
        self.ppreview.setZoomMode(QtPrintSupport.QPrintPreviewWidget.CustomZoom)
        self.ppreview.setZoomFactor(value / 100.0)

    ## Set page margins.
    # @see PrintPreviewDialog::update_margins()
    @QtCore.pyqtSlot(str)
    def on_margins_changed(self, text):
        self.printer.setPageMargins(float(self.le_margin_l.text() or 0), 
                                       float(self.le_margin_t.text() or 0), 
                                       float(self.le_margin_r.text() or 0), 
                                       float(self.le_margin_b.text() or 0),
                                       QtPrintSupport.QPrinter.Millimeter)
        # update margin values in fields                                       
        self.update_margins()
        self.ppreview.updatePreview()

    ## Shows global settings dialog.
    @QtCore.pyqtSlot()
    def on_btn_settings(self):        
        self.mainwindow.dia_settings.tree.setCurrentItem(self.mainwindow.dia_settings.tree.topLevelItem(7))
        if not self.mainwindow.dia_settings.exec(): return
        settings = self.mainwindow.dia_settings.to_settings()
        if json.dumps(settings, sort_keys=True) != json.dumps(CWSettings.settings, sort_keys=True):
            CWSettings.settings = settings
            self.update_controls()
            self.ppreview.paintRequested.emit(self.printer)            

# ******************************************************************************** #
# *****          CwInfoDialog
# ******************************************************************************** #  
        
## Crossword information editor window.
class CwInfoDialog(BasicDialog):
    
    ## Constructor.
    # @param mainwindow `QtWidgets.QMainWindow` pointer to gui::MainWindow instance
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, mainwindow, parent=None, flags=QtCore.Qt.WindowFlags()):
        ## `QtWidgets.QMainWindow` pointer to gui::MainWindow instance
        self.mainwindow = mainwindow
        super().__init__(None, _('Crossword Info'), 'info1.png', 
              parent, flags)
                
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QFormLayout()  

        self.le_title = QtWidgets.QLineEdit('')
        self.le_title.setMinimumWidth(300)
        self.le_author = QtWidgets.QLineEdit('')
        self.le_editor = QtWidgets.QLineEdit('')
        self.le_publisher = QtWidgets.QLineEdit('')
        self.le_copyright = QtWidgets.QLineEdit('')
        self.de_date = QtWidgets.QDateEdit()
        self.de_date.setCalendarPopup(True)
        self.btn_stats = QtWidgets.QToolButton()
        self.btn_stats.setDefaultAction(self.mainwindow.act_stats)

        self.layout_controls.addRow(_('Title:'), self.le_title)
        self.layout_controls.addRow(_('Author:'), self.le_author)
        self.layout_controls.addRow(_('Editor:'), self.le_editor)
        self.layout_controls.addRow(_('Publisher:'), self.le_publisher)
        self.layout_controls.addRow(_('Copyright:'), self.le_copyright)
        self.layout_controls.addRow(_('Date:'), self.de_date)
        self.layout_controls.addRow(self.btn_stats)

        self.init()

    ## Initializes controls from crossword info.
    def init(self):
        cw_info = self.mainwindow.cw.words.info if self.mainwindow.cw else CWInfo()
        self.le_title.setText(cw_info.title)
        self.le_author.setText(cw_info.author)
        self.le_editor.setText(cw_info.editor)
        self.le_publisher.setText(cw_info.publisher)
        self.le_copyright.setText(cw_info.cpyright)
        date_ = QtCore.QDate.fromString(datetime_to_str(cw_info.date, '%m/%d/%Y'), 'MM/dd/yyyy')
        self.de_date.setDate(date_ if date_.isValid() else QtCore.QDate.currentDate())

    ## Returns crossword information record initialized from the current control values.
    # @returns `crossword::CWInfo` crossword information record
    def to_info(self):
        return CWInfo(self.le_title.text(), self.le_author.text(), self.le_editor.text(),
                      self.le_publisher.text(), self.le_copyright.text(), 
                      self.de_date.dateTime().toPyDateTime() if self.de_date.date().isValid() else None)


# ******************************************************************************** #
# *****          DefLookupDialog
# ******************************************************************************** # 

## Word definition lookup dialog to look up a word in a dictionary and/or Google.
class DefLookupDialog(BasicDialog):
    
    ## Constructor.
    # @param word `str` the word string to look up
    # @param word_editable `bool` whether the word string can be edited in the dialog (default = `False`)
    # @param lang `str` short name of the langugage used to look up the word.
    # Can be one of: 'en' (English), 'ru' (Russian), 'fr' (French), 'es' (Spanish), 'de' (German), 'it' (Italian)
    # (see globalvars::LANG). If the value is an empty string (default), the setting from
    # guisettings::CWSettings::settings['lookup']['default_lang'] is taken.
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, word='', word_editable=False, lang='', 
                 parent=None, flags=QtCore.Qt.WindowFlags()):
        self.word = word.lower() or ''
        self.word_editable = word_editable
        self.word_def = None
        self.google_res = None
        self.dict_engine = None
        self.google_engine = None
        self.setlang(lang)

        super().__init__(None, _('Word Lookup'), 'worldwide.png', 
              parent, flags)
        ## worker threads to retrieve word definitions from the internet
        self.load_threads = {'dics': QThreadStump(on_start=self.on_dics_load_start, on_finish=self.on_dics_load_finish, on_run=self.on_dics_load_run, on_error=self.on_thread_error),
                             'google': QThreadStump(on_start=self.on_google_load_start, on_finish=self.on_google_load_finish, on_run=self.on_google_load_run, on_error=self.on_thread_error)}

    ## Before the dialog quits, need to stop all running background threads.
    def closeEvent(self, event):
        # close running threads
        self.kill_threads()  
        # close
        event.accept()      

    ## Retrieve results when the dialog shows.
    def showEvent(self, event):      
        self.update_content()
        event.accept()

    ## Stops any or both worker threads.
    # @param dics `bool` stop the dictionary thread (default = `True`)
    # @param google `bool` stop the google thread (default = `True`)
    def kill_threads(self, dics=True, google=True):
        for thread in self.load_threads:
            if self.load_threads[thread].isRunning() and \
                    (dics and thread == 'dics') or \
                    (google and thread == 'google'):
                self.load_threads[thread].terminate()
                self.load_threads[thread].wait()

    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout() 

        self.gb_word = QtWidgets.QGroupBox(_('Lookup word'))
        self.layout_gb_word = QtWidgets.QHBoxLayout()   
        self.le_word = QtWidgets.QLineEdit('') 
        self.le_word.textChanged.connect(self.on_le_word_changed)
        self.combo_lang = QtWidgets.QComboBox()                
        self.combo_lang.setEditable(False)
        self.combo_lang.addItems([k for k in LANG])
        self.combo_lang.activated.connect(self.on_combo_lang)
        self.layout_gb_word.addWidget(self.le_word)
        self.layout_gb_word.addWidget(self.combo_lang)
        self.gb_word.setLayout(self.layout_gb_word)
        self.layout_controls.addWidget(self.gb_word)

        self.gb_sources = QtWidgets.QGroupBox(_('Lookup in'))
        self.layout_gb_sources = QtWidgets.QHBoxLayout()
        self.rb_dict = QtWidgets.QRadioButton(_('Dictionary'))
        self.rb_dict.setChecked(True)
        self.rb_dict.toggled.connect(self.rb_source_toggled)
        self.rb_google = QtWidgets.QRadioButton(_('Google'))
        self.rb_google.toggled.connect(self.rb_source_toggled)
        self.layout_gb_sources.addWidget(self.rb_dict)
        self.layout_gb_sources.addWidget(self.rb_google)
        self.gb_sources.setLayout(self.layout_gb_sources)
        self.layout_controls.addWidget(self.gb_sources)

        self.stacked = QtWidgets.QStackedWidget() 
        self.add_pages()
        #self.stacked.setCurrentIndex(0)
        self.layout_controls.addWidget(self.stacked)

        self.init()

    ## Sets the language to search in the online services.
    # @param lang `str` search result language (see constructor for details of options)
    def setlang(self, lang=''):
        lang = lang or CWSettings.settings['lookup']['default_lang']
        if not lang: lang = 'en'
        self.lang = lang

    ## Initializes controls.
    def init(self):
        # languages combo
        index = self.combo_lang.findText(self.lang)
        if index < 0:
            raise Exception(_("Language '{}' not available!").format(self.lang))
        try:
            self.combo_lang.activated.disconnect()
        except:
            pass
        self.combo_lang.setCurrentIndex(index)
        self.combo_lang.activated.connect(self.on_combo_lang)
        # word        
        self.le_word.setEnabled(self.word_editable)
        self.le_word.textChanged.disconnect()
        self.le_word.setText(self.word) 
        self.word = self.word.lower()
        self.le_word.textChanged.connect(self.on_le_word_changed)
        # disable / enable pages
        self.rb_dict.setEnabled(CWSettings.settings['lookup']['dics']['show'])
        self.rb_google.setEnabled(CWSettings.settings['lookup']['google']['show'])
        if not self.rb_dict.isChecked() and not self.rb_google.isChecked():
            if CWSettings.settings['lookup']['dics']['show']:
                self.rb_dict.setChecked(True)
                #self.stacked.setCurrentIndex(1)
            elif CWSettings.settings['lookup']['google']['show']:
                self.rb_google.setChecked(True)
                #self.stacked.setCurrentIndex(2)
            else:
                self.stacked.setCurrentIndex(-1)  
        
    ## Sets the selected language.
    def update_language(self):
        self.lang = self.combo_lang.currentText()

    ## @brief Sets the online dictionary engine depending on the selected language.
    # If the language is English ('en'), the Merriam-Webster dictionary will be used;
    # otherwise, the Yandex dictionary will be used.
    # @see utils::onlineservices::MWDict, utils::onlineservices::YandexDict
    def update_dict_engine(self):
        self.update_language()
        timeout = CWSettings.settings['common']['web']['req_timeout'] * 1000
        if self.lang == 'en':
            self.dict_engine = MWDict(CWSettings.settings, timeout or None)
        else:
            self.dict_engine = YandexDict(CWSettings.settings, f"{self.lang}-{self.lang}", timeout or None)

    ## @brief Configures the Google search engine depending on the selected language.
    # @see utils::onlineservices::GoogleSearch
    def update_google_engine(self):
        settings = CWSettings.settings['lookup']['google']
        timeout = CWSettings.settings['common']['web']['req_timeout'] * 1000
        #settings['lang'] = self.lang
        self.google_engine = GoogleSearch(CWSettings.settings, self.word, exact_match=settings['exact_match'],
            file_types=settings['file_types'], lang=settings['lang'], country=settings['country'],
            interface_lang=settings['interface_lang'], link_site=settings['link_site'],
            related_site=settings['related_site'], in_site=settings['in_site'],
            nresults=settings['nresults'], safe_search=settings['safe_search'], timeout=timeout or None) 

    ## Adds the Dictionary and Google pages to the tab widget.
    def add_pages(self):
        # 1. Dictionary
        self.page_dict = QtWidgets.QWidget()
        self.layout_dict = QtWidgets.QVBoxLayout()
        self.combo_dict_homs = QtWidgets.QComboBox()
        self.combo_dict_homs.setEditable(False)
        self.combo_dict_homs.currentIndexChanged.connect(self.on_combo_dict_homs)
        self.layout_dict_top = QtWidgets.QFormLayout()
        self.layout_dict_top.addRow(_('Choose entry / meaning:'), self.combo_dict_homs)
        self.layout_dict.addLayout(self.layout_dict_top)    
        self.te_dict_defs = QtWidgets.QPlainTextEdit('')
        self.te_dict_defs.setStyleSheet('font-family: Arial; font-size: 10pt; font-weight: normal; background-color: white; color: black')
        self.te_dict_defs.setReadOnly(True)
        self.te_dict_defs.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        self.layout_dict.addWidget(self.te_dict_defs)  
        self.l_link_dict = QtWidgets.QLabel(_('Link'))
        self.l_link_dict.setTextFormat(QtCore.Qt.RichText)
        self.l_link_dict.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.l_link_dict.setOpenExternalLinks(True)
        self.l_link_dict.setEnabled(False)
        self.layout_dict.addWidget(self.l_link_dict)  
        self.page_dict.setLayout(self.layout_dict)
        self.stacked.addWidget(self.page_dict)

        # 2. Google
        self.page_google = QtWidgets.QWidget()
        self.layout_google = QtWidgets.QVBoxLayout()
        self.combo_google = QtWidgets.QComboBox()
        self.combo_google.setEditable(False)
        self.combo_google.currentIndexChanged.connect(self.on_combo_google)
        self.layout_google_top = QtWidgets.QFormLayout()
        self.layout_google_top.addRow(_('Choose link page:'), self.combo_google)
        self.layout_google.addLayout(self.layout_google_top)    
        self.te_google_res = QtWidgets.QPlainTextEdit('')
        self.te_google_res.setStyleSheet('font-family: Arial; font-size: 10pt; font-weight: normal; background-color: white; color: black')
        self.te_google_res.setReadOnly(True)
        self.te_google_res.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        self.layout_google.addWidget(self.te_google_res)
        self.l_link_google = QtWidgets.QLabel(_('Link'))
        self.l_link_google.setTextFormat(QtCore.Qt.RichText)
        self.l_link_google.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.l_link_google.setOpenExternalLinks(True)
        self.l_link_google.setEnabled(False)
        self.layout_google.addWidget(self.l_link_google)
        self.page_google.setLayout(self.layout_google)
        self.stacked.addWidget(self.page_google)

    ## Worker thread error handler.
    # @param thread `utils::QThreadStump` worker thread instance
    # @param err `str` error message
    @QtCore.pyqtSlot(QtCore.QThread, str)
    def on_thread_error(self, thread, err):
        MsgBox(_("Load failed with error:\n{}").format(err), self, _('Error'), 'error')

        if thread == self.load_threads['dics']:
            thread.lock()
            self.word_def = None
            thread.unlock()

        elif thread == self.load_threads['google']:
            thread.lock()
            self.google_res = None
            thread.unlock()

    ## Fires before the dictionary results are retrieved.
    def on_dics_load_start(self):
        #print(f"Started DICT thread for '{self.word}'...")
        self.word_def = None
        self.page_dict.setEnabled(False)
        self.l_link_dict.setEnabled(False)
        self.l_link_dict.setText(_('Link'))
        self.update_dict_engine()
        try:
            self.combo_dict_homs.currentIndexChanged.disconnect()
        except:
            pass
        self.combo_dict_homs.clear()
        self.te_dict_defs.setStyleSheet('font-family: Arial; font-size: 10pt; font-weight: bold; background-color: #ffd6e2; color: black')
        self.te_dict_defs.setPlainText(_('UPDATING ...'))     
        
    ## Dictionary thread run event handler: retrieve dictionary results.
    def on_dics_load_run(self):    
        thread = self.load_threads['dics']

        thread.lock()
        exact_match = CWSettings.settings['lookup']['dics']['exact_match']
        bad_pos = CWSettings.settings['lookup']['dics']['bad_pos']
        thread.unlock()
      
        word_def = self.dict_engine.get_short_defs(self.word, exact_match=exact_match, bad_pos=bad_pos)
        
        thread.lock()
        self.word_def = word_def
        thread.unlock()

    ## Fires after the dictionary results are retrieved.
    def on_dics_load_finish(self):
        #print('Finished DICT thread')
        self.te_dict_defs.setStyleSheet('font-family: Arial; font-size: 10pt; font-weight: normal; background-color: white; color: black')
        self.te_dict_defs.clear()
        if not self.word_def: return
        self.page_dict.setEnabled(True)
        self.l_link_dict.setEnabled(True)
        if CWSettings.settings['lookup']['dics']['show_pos']:
            self.combo_dict_homs.addItems([f"{entry[0]}: {entry[1]}" for entry in self.word_def])
        else:
            self.combo_dict_homs.addItems([entry[1] for entry in self.word_def])
        self.combo_dict_homs.setCurrentIndex(0)
        self.on_combo_dict_homs(0)
        self.combo_dict_homs.currentIndexChanged.connect(self.on_combo_dict_homs)
    
    ## Fires before the Google results are retrieved.
    def on_google_load_start(self):
        #print(f"Started GOOGLE thread for '{self.word}'...")
        self.google_res = None
        self.page_google.setEnabled(False)
        self.l_link_google.setEnabled(False)
        self.l_link_google.setText(_('Link'))
        self.update_google_engine()
        try:
            self.combo_google.currentIndexChanged.disconnect()
        except:
            pass
        self.combo_google.clear()
        self.te_google_res.setStyleSheet('font-family: Arial; font-size: 10pt; font-weight: bold; background-color: #ffd6e2; color: black')
        self.te_google_res.setPlainText(_('UPDATING ...')) 

    ## Google thread run event handler: retrieve Google search results.
    def on_google_load_run(self):     
        data = self.google_engine.search_lite()

        thread = self.load_threads['google']
        thread.lock()
        self.google_res = data
        thread.unlock()

    ## Fires after the Google results are retrieved.
    def on_google_load_finish(self):
        #print('Finished GOOGLE thread')
        self.te_google_res.setStyleSheet('font-family: Arial; font-size: 10pt; font-weight: normal; background-color: white; color: black')
        self.te_google_res.clear()
        if not self.google_res: return
        self.page_google.setEnabled(True)
        self.l_link_google.setEnabled(True)
        self.combo_google.addItems([entry['title'] for entry in self.google_res])
        self.combo_google.setCurrentIndex(0)
        self.on_combo_google(0)
        self.combo_google.currentIndexChanged.connect(self.on_combo_google)

    ## Fills the search results into the corresponding list and combo boxes.
    # @param dictionary `bool` whether to update the dictionary results
    # @param google `bool` whether to update the Google results
    def update_content(self, dictionary=True, google=True):
        if not self.word: return
        # kill running threads
        self.kill_threads(dictionary and CWSettings.settings['lookup']['dics']['show'], 
                          google and CWSettings.settings['lookup']['google']['show'])

        self.update_dict_engine()
        self.update_google_engine()
    
        # dict
        if dictionary and CWSettings.settings['lookup']['dics']['show']:
            self.load_threads['dics'].start()
    
        # google
        if google and CWSettings.settings['lookup']['google']['show']:
            self.load_threads['google'].start()

    ## Shows the specified page when a radio button is toggled.
    @QtCore.pyqtSlot(bool)        
    def rb_source_toggled(self, toggled):
        if self.rb_dict.isChecked():
            self.stacked.setCurrentIndex(0)
        elif self.rb_google.isChecked():
            self.stacked.setCurrentIndex(1)

    ## Sets a new search word and restarts the search.
    @QtCore.pyqtSlot(str)
    def on_le_word_changed(self, text):
        self.word = text.lower()
        try:
            self.le_word.textChanged.disconnect()
        except:
            pass
        self.le_word.setText(self.word)
        self.le_word.textChanged.connect(self.on_le_word_changed)
        self.update_content()

    ## When a language combo item is selected.
    @QtCore.pyqtSlot(int)
    def on_combo_lang(self, index):
        # update content
        self.update_content()

    ## When a word homonym is selected in the combo (Dictionary page).
    @QtCore.pyqtSlot(int)
    def on_combo_dict_homs(self, index):
        if index < 0 or not self.word_def or index >= len(self.word_def): return
        if self.word_def[index][3]:
            self.l_link_dict.setText(f'<a href="{self.word_def[index][3]}">Link</a>')
            self.l_link_dict.setToolTip(self.word_def[index][3])
            self.l_link_dict.setEnabled(True)
        else:
            self.l_link_dict.setText(_('Link'))
            self.l_link_dict.setToolTip('')
            self.l_link_dict.setEnabled(False)
        self.te_dict_defs.setPlainText('\n'.join(self.word_def[index][2]))

    ## When a Google result is selected in the combo (Google page).
    @QtCore.pyqtSlot(int)
    def on_combo_google(self, index):
        if index < 0 or not self.google_res or index >= len(self.google_res): return
        url = self.google_res[index]['url']
        if url:            
            self.l_link_google.setText(f'<a href="{url}">Link</a>')
            self.l_link_google.setToolTip(url)
            self.l_link_google.setEnabled(True)
        else:
            self.l_link_google.setText(_('Link'))
            self.l_link_google.setToolTip('')
            self.l_link_google.setEnabled(False)
        self.te_google_res.setPlainText(self.google_res[index]['summary'])

# ******************************************************************************** #
# *****          ReflectGridDialog
# ******************************************************************************** #  
    
## @bried Dialog to reflect / duplicate crossword grid cells.
# @see gui::MainWindow::act_reflect
class ReflectGridDialog(BasicDialog):
    
    ## Constructor.
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, parent=None, flags=QtCore.Qt.WindowFlags()):
        super().__init__(None, _('Duplicate Grid'), 'windows-1.png', 
              parent, flags)
        
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout()

        self.ag_dir = QtWidgets.QActionGroup(self)
        self.act_down = self.ag_dir.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-r.png"), 
                                                # NOTE: arrow button
                                                _('Down'))
        self.act_down.setCheckable(True)        
        self.act_down.toggled.connect(self.on_actdir)
        self.act_up = self.ag_dir.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-l.png"), _('Up'))
        self.act_up.setCheckable(True)
        self.act_up.toggled.connect(self.on_actdir)
        self.act_right = self.ag_dir.addAction(QtGui.QIcon(f"{ICONFOLDER}/fast-forward-1.png"), _('Right'))
        self.act_right.setCheckable(True)
        self.act_right.toggled.connect(self.on_actdir)
        self.act_left = self.ag_dir.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-1.png"), _('Left'))
        self.act_left.setCheckable(True)
        self.act_left.toggled.connect(self.on_actdir)
        self.tb_dir = QtWidgets.QToolBar()
        self.tb_dir.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.tb_dir.addAction(self.act_down)
        self.tb_dir.addAction(self.act_up)
        self.tb_dir.addAction(self.act_right)
        self.tb_dir.addAction(self.act_left)
        self.l_top = QtWidgets.QLabel(_('Duplication direction:'))

        self.ag_border = QtWidgets.QActionGroup(self)
        self.act_b0 = self.ag_border.addAction(QtGui.QIcon(f"{ICONFOLDER}/error.png"), _('No border'))
        self.act_b0.setCheckable(True)
        self.act_b0.setChecked(True)
        self.act_b1 = self.ag_border.addAction(QtGui.QIcon(f"{ICONFOLDER}/grid5.png"), _('Empty'))
        self.act_b1.setCheckable(True)
        self.act_b2 = self.ag_border.addAction(QtGui.QIcon(f"{ICONFOLDER}/grid6.png"), _('Filled-Empty'))
        self.act_b2.setCheckable(True)
        self.act_b3 = self.ag_border.addAction(QtGui.QIcon(f"{ICONFOLDER}/grid7.png"), _('Empty-Filled'))
        self.act_b3.setCheckable(True)
        self.act_b4 = self.ag_border.addAction(QtGui.QIcon(f"{ICONFOLDER}/grid9.png"), _('Filled'))
        self.act_b4.setCheckable(True)
        self.tb_border = QtWidgets.QToolBar()
        self.tb_border.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.tb_border.addAction(self.act_b0)
        self.tb_border.addAction(self.act_b1)
        self.tb_border.addAction(self.act_b2)
        self.tb_border.addAction(self.act_b3)
        self.tb_border.addAction(self.act_b4)
        self.l_border = QtWidgets.QLabel(_('Border style:'))

        self.gb_options = QtWidgets.QGroupBox(_('Duplicate options'))
        self.layout_gb_options = QtWidgets.QVBoxLayout()
        self.chb_mirror = QtWidgets.QCheckBox(_('Mirror'))
        self.chb_mirror.setToolTip(_('Mirror duplicate grids along duplication axis'))
        self.chb_mirror.setChecked(True)
        self.chb_reverse = QtWidgets.QCheckBox(_('Reverse'))
        self.chb_reverse.setToolTip(_('Reverse the sequence of duplicate grids'))
        self.chb_reverse.setChecked(True)
        self.layout_gb_options.addWidget(self.chb_mirror)
        self.layout_gb_options.addWidget(self.chb_reverse)
        self.gb_options.setLayout(self.layout_gb_options)

        self.layout_controls.addWidget(self.l_top)
        self.layout_controls.addWidget(self.tb_dir)
        self.layout_controls.addWidget(self.l_border)
        self.layout_controls.addWidget(self.tb_border)
        self.layout_controls.addWidget(self.gb_options)

        if not self.ag_border.checkedAction():
            self.act_b0.setChecked(True)

        if not self.ag_dir.checkedAction():
            self.act_down.setChecked(True)

    ## Changes the reflect direction button icons according to the direction.
    def update_dir_icons(self):
        if self.act_down.isChecked() or self.act_up.isChecked():
            self.act_b1.setIcon(QtGui.QIcon(f"{ICONFOLDER}/grid5.png"))
            self.act_b2.setIcon(QtGui.QIcon(f"{ICONFOLDER}/grid6.png"))
            self.act_b3.setIcon(QtGui.QIcon(f"{ICONFOLDER}/grid7.png"))
            self.act_b4.setIcon(QtGui.QIcon(f"{ICONFOLDER}/grid9.png"))
        else:
            self.act_b1.setIcon(QtGui.QIcon(f"{ICONFOLDER}/grid10.png"))
            self.act_b2.setIcon(QtGui.QIcon(f"{ICONFOLDER}/grid11.png"))
            self.act_b3.setIcon(QtGui.QIcon(f"{ICONFOLDER}/grid12.png"))
            self.act_b4.setIcon(QtGui.QIcon(f"{ICONFOLDER}/grid13.png"))

    ## Change relfect direction action.
    @QtCore.pyqtSlot(bool)
    def on_actdir(self, checked):
        self.update_dir_icons()

# ******************************************************************************** #
# *****          PasswordDialog
# ******************************************************************************** #

## Tiny login/password authentication dialog used by the inbuilt web browser (see pycross::browser).
class PasswordDialog(BasicDialog):
    
    ## Constructor.
    # @param title `str` dialog title
    # @param icon `str` dialog icon file
    # @param user_label `str` user (login) hint
    # @param password_label `str` password hint
    # @param allow_empty_user `bool` whether an empty user string is allowed
    # @param allow_empty_password `bool` dwhether an empty password string is allowed
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, title=_('Authentication'), icon='locked.png',
                 user_label=_('User'), password_label=_('Password'),
                 allow_empty_user=False, allow_empty_password=False,
                 parent=None, flags=QtCore.Qt.WindowFlags()):        
        self.user_label = user_label
        self.password_label = password_label
        self.allow_empty_user = allow_empty_user
        self.allow_empty_password = allow_empty_password
        super().__init__(None, title, icon, parent, flags)
        
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QFormLayout()
        self.le_user = QtWidgets.QLineEdit('')
        self.le_pass = QtWidgets.QLineEdit('')
        self.le_pass.setEchoMode(QtWidgets.QLineEdit.PasswordEchoOnEdit)
        self.layout_controls.addRow(self.user_label, self.le_user)
        self.layout_controls.addRow(self.password_label, self.le_pass)

    def validate(self):
        if not self.allow_empty_user and not self.le_user.text():
            MsgBox(_("{} field cannot be empty!").format(self.user_label), self, _('Error'), 'error')
            return False
        if not self.allow_empty_password and not self.le_pass.text():
            MsgBox(_("{} field cannot be empty!").format(self.password_label), self, _('Error'), 'error')
            return False
        return True

    ## Gets the user and password in a single 2-tuple.
    # @returns `2-tuple` (user, password)
    def get_auth(self):
        if self.validate():
            return (self.le_user.text(), self.le_pass.text())
        return None

# ******************************************************************************** #
# *****          AboutDialog
# ******************************************************************************** #

## Information dialog showing info about this app.
class AboutDialog(QtWidgets.QDialog):
    
    ## Constructor.
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, parent=None, flags=QtCore.Qt.WindowFlags()):
        super().__init__(parent, flags)
        self.initUI(None, _('About'), 'main.png')
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        
    def initUI(self, geometry=None, title=None, icon=None):        
        self.addMainLayout()
        
        self.btn_OK = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/like.png"), _('OK'), None)
        self.btn_OK.setMaximumWidth(150)
        self.btn_OK.setDefault(True)
        self.btn_OK.clicked.connect(self.accept)
        self.layout_bottom = QtWidgets.QHBoxLayout()
        self.layout_bottom.addWidget(self.btn_OK, alignment=QtCore.Qt.AlignHCenter)
        
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.addLayout(self.layout_controls)
        self.layout_main.addLayout(self.layout_bottom)
        
        self.setLayout(self.layout_main)

        if geometry:
            self.setGeometry(*geometry) 
        if title:
            self.setWindowTitle(title)      
        if icon:
            self.setWindowIcon(QtGui.QIcon(f"{ICONFOLDER}/{icon}")) 

        self.adjustSize()

    def addMainLayout(self):
        self.layout_controls = QtWidgets.QFormLayout()

        self.l_appname = QtWidgets.QLabel(APP_NAME)
        self.l_appname.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard)
        self.l_appversion = QtWidgets.QLabel(APP_VERSION)
        self.l_appversion.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard)
        self.l_author = QtWidgets.QLabel(APP_AUTHOR)
        self.l_author.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard)
        self.l_email = QtWidgets.QLabel(f'<a href="mailto:{APP_EMAIL}">{APP_EMAIL}</a>')
        self.l_email.setToolTip(_("Send mail to {}").format(APP_EMAIL))
        self.l_email.setTextFormat(QtCore.Qt.RichText)
        self.l_email.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.l_email.setOpenExternalLinks(True)
        self.l_github = QtWidgets.QLabel(f'<a href="{GIT_REPO}">{GIT_REPO}</a>')
        self.l_github.setToolTip(_("Visit {}").format(GIT_REPO))
        self.l_github.setTextFormat(QtCore.Qt.RichText)
        self.l_github.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.l_github.setOpenExternalLinks(True)
        self.te_thanks = QtWidgets.QTextBrowser()
        #self.te_thanks.setReadOnly(True)
        self.te_thanks.setFixedHeight(50)
        self.te_thanks.setOpenLinks(False)
        html = '<html><body><b>Icons</b> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a>'
        html += ' made by: <a href="https://www.flaticon.com/authors/freepik" title="Freepik">Freepik</a>, '
        html += '<a href="https://www.flaticon.com/authors/srip" title="srip">srip</a>, '
        html += '<a href="https://www.flaticon.com/authors/google" title="Google">Google</a>, '
        html += '<a href="https://www.flaticon.com/authors/roundicons" title="Roundicons">Roundicons</a>, '
        html += '<a href="https://www.flaticon.com/authors/smashicons" title="Smashicons">Smashicons</a>.</body></html>'
        self.te_thanks.setHtml(html)
        self.te_thanks.anchorClicked.connect(QtCore.pyqtSlot(QtCore.QUrl)(lambda url: QtGui.QDesktopServices.openUrl(url)))
        #self.te_thanks.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction | QtCore.Qt.LinksAccessibleByMouse)

        self.layout_controls.addRow(_('App name:'), self.l_appname)
        self.layout_controls.addRow(_('Version:'), self.l_appversion)
        self.layout_controls.addRow(_('Author:'), self.l_author)
        self.layout_controls.addRow(_('Email:'), self.l_email)
        self.layout_controls.addRow(_('Website:'), self.l_github)
        self.layout_controls.addRow(_('Acknowledgements:'), self.te_thanks)

# ******************************************************************************** #
# *****          KloudlessAuthDialog
# ******************************************************************************** #

## Authentication dialog for uploading files to the cloud (via Kloudess API).
class KloudlessAuthDialog(QtWidgets.QDialog):
    
    ## Constructor.
    # @param on_gettoken `callable` callback function to get a valid user token 
    # (callback takes no arguments and implies that the user will authorize online
    # and paste the token string from the web browser into the dialog) 
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, on_gettoken, parent=None, flags=QtCore.Qt.WindowFlags()):
        super().__init__(parent, flags)
        self.on_gettoken = on_gettoken
        self.initUI(None, _('Bearer Token required'), 'users.png')
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))

    def initUI(self, geometry=None, title=None, icon=None):
        
        self.addMainLayout()
        
        self.btn_OK = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/like.png"), _('OK'), None)
        self.btn_OK.setMaximumWidth(150)
        self.btn_OK.setDefault(True)
        self.btn_OK.clicked.connect(self.accept)

        self.btn_cancel = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/multiply-1.png"), _('Cancel'), None)
        self.btn_cancel.setMaximumWidth(150)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_gettoken = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/key-1.png"), _('Get token...'), None)
        self.btn_gettoken.setMaximumWidth(150)
        self.btn_gettoken.clicked.connect(self.on_gettoken)

        self.layout_bottom = QtWidgets.QHBoxLayout()
        self.layout_bottom.addWidget(self.btn_OK, alignment=QtCore.Qt.AlignHCenter)
        self.layout_bottom.addWidget(self.btn_cancel, alignment=QtCore.Qt.AlignHCenter)
        self.layout_bottom.addWidget(self.btn_gettoken, alignment=QtCore.Qt.AlignHCenter)
        
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.addLayout(self.layout_controls)
        self.layout_main.addLayout(self.layout_bottom)
        
        self.setLayout(self.layout_main)
        if geometry:
            self.setGeometry(*geometry) 
        if title:
            self.setWindowTitle(title)      
        if icon:
            self.setWindowIcon(QtGui.QIcon(f"{ICONFOLDER}/{icon}")) 

        self.adjustSize()

    def addMainLayout(self):
        self.layout_controls = QtWidgets.QFormLayout()
        self.le_token = QtWidgets.QLineEdit('')
        self.le_token.setEchoMode(QtWidgets.QLineEdit.Password)
        self.layout_controls.addRow(_('Your Bearer Token:'), self.le_token)
            

# ******************************************************************************** #
# *****          ShareDialog
# ******************************************************************************** #  

## Dialog for sharing crosswords in social networks.        
class ShareDialog(BasicDialog):
    
    ## Constructor.
    # @param mainwindow `QtWidgets.QMainWindow` pointer to gui::MainWindow instance
    # @param parent `QtWidgets.QWidget` parent widget (default = `None`, i.e. no parent)
    # @param flags `QtCore.Qt.WindowFlags` [Qt window flags](https://doc.qt.io/qt-5/qt.html#WindowType-enum)
    def __init__(self, mainwindow, parent=None, flags=QtCore.Qt.WindowFlags()):
        self.mainwindow = mainwindow
        super().__init__(None, _('Share'), 'share-1.png', 
              parent, flags)
        
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout()

        self.gb_share = QtWidgets.QGroupBox(_('Sharing'))
        self.layout_gb_share = QtWidgets.QFormLayout()
        self.combo_target = QtWidgets.QComboBox()
        self.combo_target.setEditable(False)
        self.combo_target.addItems(Share.SERVICES.keys())
        self.combo_target.setCurrentIndex(0)
        self.le_title = QtWidgets.QLineEdit()
        self.le_title.setText(_('My new crossword'))
        self.le_tags = QtWidgets.QLineEdit()
        self.le_tags.setText(_('pycrossword,crossword,python'))
        self.le_source = QtWidgets.QLineEdit()
        self.le_source.setText(f"{APP_NAME} {APP_VERSION}")
        self.te_notes = QtWidgets.QPlainTextEdit()
        self.te_notes.setWordWrapMode(1)
        self.btn_share_settings = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/settings-5.png"), _('Settings...'), None)
        self.btn_share_settings.setMaximumWidth(150)
        self.btn_share_settings.clicked.connect(self.on_btn_share_settings)
        self.layout_gb_share.addRow(_('Target'), self.combo_target)
        self.layout_gb_share.addRow(_('Title'), self.le_title)
        self.layout_gb_share.addRow(_('Tags'), self.le_tags)
        self.layout_gb_share.addRow(_('Source'), self.le_source)
        self.layout_gb_share.addRow(_('Notes'), self.te_notes)
        self.layout_gb_share.addRow('', self.btn_share_settings)
        self.gb_share.setLayout(self.layout_gb_share)
        self.layout_controls.addWidget(self.gb_share)

        self.gb_export = QtWidgets.QGroupBox(_('Export'))
        self.layout_gb_export = QtWidgets.QGridLayout()
        self.rb_pdf = QtWidgets.QRadioButton('PDF')
        self.rb_jpg = QtWidgets.QRadioButton('JPG')
        self.rb_png = QtWidgets.QRadioButton('PNG')
        self.rb_svg = QtWidgets.QRadioButton('SVG')
        self.rb_xpf = QtWidgets.QRadioButton('XPF')
        self.rb_ipuz = QtWidgets.QRadioButton('IPUZ')
        self.rb_pdf.setChecked(True)
        self.btn_export_settings = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/settings-5.png"), _('Settings...'), None)
        self.btn_export_settings.setMaximumWidth(150)
        self.btn_export_settings.clicked.connect(self.on_btn_export_settings)
        self.layout_gb_export.addWidget(self.rb_pdf, 0, 0)
        self.layout_gb_export.addWidget(self.rb_jpg, 1, 0)
        self.layout_gb_export.addWidget(self.rb_png, 2, 0)
        self.layout_gb_export.addWidget(self.rb_svg, 0, 1)
        self.layout_gb_export.addWidget(self.rb_xpf, 1, 1)
        self.layout_gb_export.addWidget(self.rb_ipuz, 2, 1)
        self.layout_gb_export.addWidget(self.btn_export_settings, 3, 1)
        self.gb_export.setLayout(self.layout_gb_export)
        self.layout_controls.addWidget(self.gb_export)

    ## Shows the Sharing page of the global settings dialog.
    @QtCore.pyqtSlot()
    def on_btn_share_settings(self):
        self.mainwindow.dia_settings.tree.setCurrentItem(self.mainwindow.dia_settings.tree.topLevelItem(9))
        self.mainwindow.on_act_config(False)

    ## Shows the Export page of the global settings dialog.
    @QtCore.pyqtSlot()
    def on_btn_export_settings(self):
        ind = 7 if self.rb_pdf.isChecked() else 5
        self.mainwindow.dia_settings.tree.setCurrentItem(self.mainwindow.dia_settings.tree.topLevelItem(ind))
        self.mainwindow.on_act_config(False)