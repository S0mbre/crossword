# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

from PyQt5 import QtGui, QtCore, QtWidgets, QtPrintSupport
from utils.utils import *
from utils.globalvars import *
from utils.onlineservices import MWDict, YandexDict, GoogleSearch
from crossword import BLANK, CWInfo
from guisettings import CWSettings
import os, copy, json
import numpy as np

##############################################################################
######          BasicDialog
##############################################################################

class BasicDialog(QtWidgets.QDialog):
    
    def __init__(self, geometry=None, title=None, icon=None, parent=None, 
                 flags=QtCore.Qt.WindowFlags(), 
                 sizepolicy=QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)):
        super().__init__(parent, flags)
        self.initUI(geometry, title, icon)
        self.setSizePolicy(sizepolicy)
        
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QFormLayout()
        
    def initUI(self, geometry=None, title=None, icon=None):
        
        self.addMainLayout()
        
        self.btn_OK = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/like.png"), 'OK', None)
        self.btn_OK.setMaximumWidth(150)
        self.btn_OK.setDefault(True)
        self.btn_OK.clicked.connect(self.on_btn_OK_clicked)
        self.btn_cancel = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/multiply-1.png"), 'Cancel', None)
        self.btn_cancel.setMaximumWidth(150)
        self.btn_cancel.clicked.connect(self.on_btn_cancel_clicked)
        
        self.layout_bottom = QtWidgets.QHBoxLayout()
        self.layout_bottom.setSpacing(10)
        self.layout_bottom.addWidget(self.btn_OK)
        self.layout_bottom.addWidget(self.btn_cancel)          
        
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
        
    def validate(self):        
        return True
    
    @QtCore.pyqtSlot()
    def on_btn_OK_clicked(self): 
        if self.validate(): self.accept()
        
    @QtCore.pyqtSlot()
    def on_btn_cancel_clicked(self): 
        self.reject() 
        
##############################################################################
######          LoadCwDialog
##############################################################################  
        
class LoadCwDialog(BasicDialog):
    
    def __init__(self, parent=None, flags=QtCore.Qt.WindowFlags()):
        super().__init__(None, 'Load crossword', 'crossword.png', 
              parent, flags)
        
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout()
        
        self.rb_grid = QtWidgets.QRadioButton('Pattern')
        self.rb_grid.setToolTip('Load pattern preset')
        self.rb_grid.toggle()
        self.rb_grid.toggled.connect(self.rb_toggled)
        self.rb_file = QtWidgets.QRadioButton('File')
        self.rb_file.setToolTip('Import crossword from file')
        self.rb_file.toggled.connect(self.rb_toggled)
        self.rb_empty = QtWidgets.QRadioButton('Empty grid')
        self.rb_empty.setToolTip('Set grid dimensions and edit manually')
        self.rb_empty.toggled.connect(self.rb_toggled)
        
        self.gb_pattern = QtWidgets.QGroupBox('Pattern file')
        self.le_pattern = QtWidgets.QLineEdit()
        self.le_pattern.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.act_pattern = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/folder-2.png"), 'Browse', None)
        self.act_pattern.setToolTip('Browse')
        self.act_pattern.triggered.connect(self.on_act_pattern)
        self.b_pattern = QtWidgets.QToolButton()
        self.b_pattern.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.b_pattern.setDefaultAction(self.act_pattern)        
        self.layout_pattern = QtWidgets.QHBoxLayout()
        self.layout_pattern.setSpacing(10)
        self.layout_pattern.addWidget(self.le_pattern)
        self.layout_pattern.addWidget(self.b_pattern)
        self.gb_pattern.setLayout(self.layout_pattern)
        #self.gb_pattern.setVisible(True)
        
        self.gb_file = QtWidgets.QGroupBox('Crossword file')
        self.le_file = QtWidgets.QLineEdit()
        self.le_file.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.act_file = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/folder-2.png"), 'Browse', None)
        self.act_file.setToolTip('Browse')
        self.act_file.triggered.connect(self.on_act_file)
        self.b_file = QtWidgets.QToolButton()
        self.b_file.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.b_file.setDefaultAction(self.act_file)        
        self.layout_file = QtWidgets.QHBoxLayout()
        self.layout_file.setSpacing(10)
        self.layout_file.addWidget(self.le_file)
        self.layout_file.addWidget(self.b_file)
        self.gb_file.setLayout(self.layout_file)
        self.gb_file.setVisible(False)
        
        self.gb_manual = QtWidgets.QGroupBox('Grid dimensions')
        self.le_rows = QtWidgets.QLineEdit('15')
        self.le_cols = QtWidgets.QLineEdit('15')
        self.combo_pattern = QtWidgets.QComboBox()
        for i in range(1, 5):
            icon = QtGui.QIcon(f"{ICONFOLDER}/grid{i}.png")
            self.combo_pattern.addItem(icon, f"Pattern {i}")
        self.layout_manual = QtWidgets.QFormLayout()
        self.layout_manual.addRow('Rows:', self.le_rows)
        self.layout_manual.addRow('Columns:', self.le_cols)
        self.layout_manual.addRow('Pattern:', self.combo_pattern)
        self.gb_manual.setLayout(self.layout_manual)
        self.gb_manual.setVisible(False)
        
        self.layout_controls.addWidget(self.rb_grid)
        self.layout_controls.addWidget(self.gb_pattern)
        self.layout_controls.addWidget(self.rb_file)
        self.layout_controls.addWidget(self.gb_file)
        self.layout_controls.addWidget(self.rb_empty)
        self.layout_controls.addWidget(self.gb_manual)
        #self.layout_controls.addStretch()
        
    def validate(self):
        if self.rb_grid.isChecked() and not os.path.isfile(self.le_pattern.text()):
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
            'Pattern file is unavailable, please check!', QtWidgets.QMessageBox.Ok, self).exec()
            return False
        if self.rb_file.isChecked() and not os.path.isfile(self.le_file.text()):
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
            'Crossword file is unavailable, please check!', QtWidgets.QMessageBox.Ok, self).exec()
            return False 
        try:
            int(self.le_rows.text())
            int(self.le_cols.text())
        except ValueError:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
            'Rows and columns must be valid numbers (e.g. 10)!', QtWidgets.QMessageBox.Ok, self).exec()
            return False
        return True
        
    # ----- Slots ----- #
    
    @QtCore.pyqtSlot(bool)        
    def rb_toggled(self, toggled):
        """
        Show / hide panels under radio buttons.
        """
        self.gb_pattern.setVisible(self.rb_grid.isChecked())
        self.gb_file.setVisible(self.rb_file.isChecked())
        self.gb_manual.setVisible(self.rb_empty.isChecked())
    
    @QtCore.pyqtSlot(bool)        
    def on_act_pattern(self, checked):
        """
        Browse for pattern file.
        """
        current_dir = self.le_pattern.text()
        selected_path = QtWidgets.QFileDialog.getOpenFileName(self, 'Select file', current_dir or os.getcwd(), 'All files (*.*)')
        if selected_path[0]:
            self.le_pattern.setText(selected_path[0].replace('/', os.sep))
    
    @QtCore.pyqtSlot(bool)        
    def on_act_file(self, checked):
        """
        Browse for cw file.
        """
        current_dir = self.le_file.text()
        selected_path = QtWidgets.QFileDialog.getOpenFileName(self, 'Select file', current_dir or os.getcwd(), 'Crossword files (*.xpf *.xml *.puz *.ipuz);;All files (*.*)')
        if selected_path[0]:
            self.le_file.setText(selected_path[0].replace('/', os.sep))
    
            
##############################################################################
######          WordSrcDialog
##############################################################################  
        
class WordSrcDialog(BasicDialog):
    
    """
    src = {'active': True|False, 'name': '<name>', 'type': 'db|file|list', 'file': '<path>', 
    'dbtype': '<sqlite>', 'dblogin': '', 'dbpass': '', 'dbtables': SQL_TABLES, 
    'haspos': True|False, 'encoding': 'utf-8', 'shuffle': True|False, 
    'delim': ' ', 'words': []}
    """
    
    def __init__(self, src=None, parent=None, flags=QtCore.Qt.WindowFlags()):
        self.src = src
        super().__init__(None, 'Word Source', 'database-3.png', 
              parent, flags)
        if self.src: self.from_src(self.src)
                
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout()     
        
        self.gb_name = QtWidgets.QGroupBox('Name')
        self.gb_name.setFlat(True)
        self.layout_gb_name = QtWidgets.QVBoxLayout() 
        self.le_name = QtWidgets.QLineEdit('')
        self.le_name.setStyleSheet('font-weight: bold;')
        self.layout_gb_name.addWidget(self.le_name)
        self.gb_name.setLayout(self.layout_gb_name)
        
        self.gb_type = QtWidgets.QGroupBox('Source type') 
        self.layout_gb_type = QtWidgets.QHBoxLayout() 
        self.rb_type_db = QtWidgets.QRadioButton('Database')
        self.rb_type_db.toggled.connect(self.rb_toggled)
        self.rb_type_file = QtWidgets.QRadioButton('File')
        self.rb_type_file.toggled.connect(self.rb_toggled)
        self.rb_type_list = QtWidgets.QRadioButton('Simple list')
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
        
    def add_pages(self):
        # 1. DB
        self.page_db = QtWidgets.QWidget()
        self.layout_db = QtWidgets.QFormLayout()
        self.le_dbfile = QtWidgets.QLineEdit('')
        self.combo_dbtype = QtWidgets.QComboBox()
        self.combo_dbtype.addItems(['SQLite'])
        self.combo_dbtype.setEditable(False)
        self.combo_dbtype.setCurrentIndex(0)
        self.le_dbuser = QtWidgets.QLineEdit('')
        self.le_dbpass = QtWidgets.QLineEdit('')
        self.le_dbtables = QtWidgets.QLineEdit(json.dumps(SQL_TABLES))
        self.chb_db_shuffle = QtWidgets.QCheckBox()
        self.layout_db.addRow('Path', self.le_dbfile)
        self.layout_db.addRow('Type', self.combo_dbtype)
        self.layout_db.addRow('User', self.le_dbuser)
        self.layout_db.addRow('Password', self.le_dbpass)
        self.layout_db.addRow('Tables', self.le_dbtables)
        self.layout_db.addRow('Shuffle', self.chb_db_shuffle)
        self.page_db.setLayout(self.layout_db)
        self.stacked.addWidget(self.page_db)
        
        # 2. File
        self.page_file = QtWidgets.QWidget()
        self.layout_file = QtWidgets.QFormLayout()
        self.le_txtfile = QtWidgets.QLineEdit('')
        self.combo_fileenc = QtWidgets.QComboBox()
        self.combo_fileenc.addItems(ENCODINGS)
        self.combo_fileenc.setEditable(False)
        self.combo_fileenc.setCurrentText('utf_8')
        self.combo_file_delim = QtWidgets.QComboBox()
        self.combo_file_delim.addItems(['SPACE', 'TAB', ';', ',', ':'])
        self.combo_file_delim.setEditable(True)
        self.combo_file_delim.setCurrentIndex(0)
        self.chb_file_shuffle = QtWidgets.QCheckBox()
        self.layout_file.addRow('Path', self.le_txtfile)
        self.layout_file.addRow('Encoding', self.combo_fileenc)
        self.layout_file.addRow('Delimiter', self.combo_file_delim)
        self.layout_file.addRow('Shuffle', self.chb_file_shuffle)
        self.page_file.setLayout(self.layout_file)
        self.stacked.addWidget(self.page_file)
        
        # 3. List
        self.page_list = QtWidgets.QWidget()
        self.layout_list = QtWidgets.QFormLayout()
        self.combo_list_delim = QtWidgets.QComboBox()
        self.combo_list_delim.addItems(['SPACE', 'TAB', ';', ',', ':'])
        self.combo_list_delim.setEditable(True)
        self.combo_list_delim.setCurrentIndex(0)
        self.chb_haspos = QtWidgets.QCheckBox()
        self.chb_haspos.setChecked(True)
        self.te_wlist = QtWidgets.QTextEdit('')
        self.te_wlist.setStyleSheet('font: 14pt "Courier";color: black')
        self.te_wlist.setAcceptRichText(False)
        self.te_wlist.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.chb_list_shuffle = QtWidgets.QCheckBox()
        self.layout_list.addRow('Delimiter', self.combo_list_delim)
        self.layout_list.addRow('Has parts of speech', self.chb_haspos)
        self.layout_list.addRow('Words', self.te_wlist)
        self.layout_list.addRow('Shuffle', self.chb_list_shuffle)
        self.page_list.setLayout(self.layout_list)
        self.stacked.addWidget(self.page_list)
                
    def from_src(self, src): 
        if not src: return
        
        self.le_name.setText(self.src['name'])
        
        if self.src['type'] == 'db':
            self.rb_type_db.setChecked(True)
            self.le_dbfile.setText(self.src['file'])
            self.combo_dbtype.setCurrentText(self.src['dbtype'])
            self.le_dbuser.setText(self.src['dblogin'])
            self.le_dbpass.setText(self.src['dbpass'])
            self.le_dbtables.setText(str(self.src['dbtables']))
            self.chb_db_shuffle.setChecked(self.src['shuffle'])
            
        elif self.src['type'] == 'file':
            self.rb_type_file.setChecked(True)
            self.le_txtfile.setText(self.src['file'])
            self.combo_fileenc.setCurrentText(self.src['encoding'])
            delim = self.src['delim']
            if delim == ' ':
                delim = 'SPACE'
            elif delim == '\t':
                delim = 'TAB'
            else:
                delim = delim[0]
            self.combo_file_delim.setCurrentText(delim)
            self.chb_file_shuffle.setChecked(self.src['shuffle'])
            
        elif self.src['type'] == 'list':
            self.rb_type_list.setChecked(True)
            delim = self.src['delim']
            if delim == ' ':
                delim = 'SPACE'
            elif delim == '\t':
                delim = 'TAB'
            else:
                delim = delim[0]
            self.combo_list_delim.setCurrentText(delim)
            self.chb_haspos.setChecked(self.src['haspos'])
            self.te_wlist.setPlainText('\n'.join(self.src['words']))
            self.chb_list_shuffle.setChecked(self.src['shuffle'])
            
        # activate page
        self.rb_toggled(True)
    
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
            self.src['dbtables'] = json.loads(self.le_dbtables.text())
            self.src['shuffle'] = self.chb_db_shuffle.isChecked()
                
        elif self.rb_type_file.isChecked():
            self.src['type'] = 'file'
            self.src['file'] = self.le_txtfile.text()
            self.src['encoding'] = self.combo_fileenc.currentText()
            delim = self.combo_file_delim.currentText()
            if delim == 'SPACE':
                delim = ' '
            elif delim == 'TAB':
                delim = '\t'
            else:
                delim = delim[0]
            self.src['delim'] = delim
            self.src['shuffle'] = self.chb_file_shuffle.isChecked()
            
        else:
            self.src['type'] = 'list'
            delim = self.combo_list_delim.currentText()
            if delim == 'SPACE':
                delim = ' '
            elif delim == 'TAB':
                delim = '\t'
            else:
                delim = delim[0]
            self.src['delim'] = delim
            self.src['haspos'] = self.chb_haspos.isChecked()
            self.src['words'] = self.te_wlist.toPlainText().strip().split('\n')
            self.src['shuffle'] = self.chb_list_shuffle.isChecked()
    
    def validate(self):
        if not self.le_name.text().strip():
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
            'Source must have a non-empty name!', QtWidgets.QMessageBox.Ok, self).exec()
            return False
        if self.rb_type_db.isChecked():
            if not self.le_dbfile.text() or not self.le_dbfile.text() in LANG:
                QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
                'DB file path must be valid!', QtWidgets.QMessageBox.Ok, self).exec()
                return False
            try:
                d = json.loads(self.le_dbtables.text())
                if not isinstance(d, dict): raise Exception()
            except:
                QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
                'DB tables field has incorrect value!', QtWidgets.QMessageBox.Ok, self).exec()
                return False
            
        elif self.rb_type_file.isChecked():
            if not self.le_txtfile.text():
                QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
                'Text file path must be valid!', QtWidgets.QMessageBox.Ok, self).exec()
                return False
            if not self.combo_fileenc.currentText():
                QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
                'Text file encoding must not be empty!', QtWidgets.QMessageBox.Ok, self).exec()
                return False
            delim = self.combo_file_delim.currentText()
            if not delim:
                QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
                'Text file delimiter must not be empty!', QtWidgets.QMessageBox.Ok, self).exec()
                return False
            if not delim in ('SPACE', 'TAB') and len(delim) > 1:
                QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
                'Text file delimiter must be either "SPACE" or "TAB" or a single character!', QtWidgets.QMessageBox.Ok, self).exec()
                return False
            
        elif self.rb_type_list.isChecked():
            if self.chb_haspos.isChecked():
                delim = self.combo_list_delim.currentText()
                if not delim:
                    QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
                    'Word list delimiter must not be empty if is has parts of speech!', QtWidgets.QMessageBox.Ok, self).exec()
                    return False
                if not delim in ('SPACE', 'TAB') and len(delim) > 1:
                    QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
                    'Word list delimiter must be either "SPACE" or "TAB" or a single character!', QtWidgets.QMessageBox.Ok, self).exec()
                    return False
            if not self.te_wlist.toPlainText().strip():
                QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
                'Word list is empty or invalid!', QtWidgets.QMessageBox.Ok, self).exec()
                return False
            
        self.to_src()
        return True
    
    @QtCore.pyqtSlot(bool)        
    def rb_toggled(self, toggled):
        if self.rb_type_db.isChecked():
            self.stacked.setCurrentIndex(0)
        elif self.rb_type_file.isChecked():
            self.stacked.setCurrentIndex(1)
        elif self.rb_type_list.isChecked():
            self.stacked.setCurrentIndex(2)
            
##############################################################################
######          SettingsDialog
##############################################################################  
        
class SettingsDialog(BasicDialog):
    
    def __init__(self, mainwindow=None, parent=None, flags=QtCore.Qt.WindowFlags()):
        self.mainwindow = mainwindow
        self.default_settings = self.load_default_settings()
        super().__init__(None, 'Settings', 'settings-5.png', 
              parent, flags)
        
    def load_default_settings(self):
        """
        Loads the default settings from 'defsettings.json'.
        """
        defsettings = CWSettings.validate_file(DEFAULT_SETTINGS_FILE)
        if defsettings: return defsettings
        CWSettings.save_to_file(DEFAULT_SETTINGS_FILE) 
        return copy.deepcopy(CWSettings.settings)
                
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QHBoxLayout()   

        self.tree = QtWidgets.QTreeWidget()         
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(100)
        self.tree.setMaximumWidth(500)
        
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(['Generation']))
        item = QtWidgets.QTreeWidgetItem(['Sources'])
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        item.addChild(QtWidgets.QTreeWidgetItem(['Source management']))
        item.addChild(QtWidgets.QTreeWidgetItem(['Search rules']))
        self.tree.addTopLevelItem(item)
        
        item = QtWidgets.QTreeWidgetItem(['User interface'])
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        item.addChild(QtWidgets.QTreeWidgetItem(['Window']))
        item.addChild(QtWidgets.QTreeWidgetItem(['Grid']))
        item.addChild(QtWidgets.QTreeWidgetItem(['Clues']))
        self.tree.addTopLevelItem(item)
        
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(['Definition lookup']))
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(['Import & Export']))
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(['Plugins']))
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(['Printing']))
        self.tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(['Updating']))
        self.tree.itemSelectionChanged.connect(self.on_tree_select)
        
        self.central_widget = QtWidgets.QWidget()
        self.layout_central = QtWidgets.QVBoxLayout()
        self.stacked = QtWidgets.QStackedWidget() 
        self.add_pages()
        self.btn_defaults = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/cloud-computing.png"), 'Restore defaults')
        self.btn_defaults.setToolTip('Restore default settings for selected page')
        self.btn_defaults.clicked.connect(self.on_btn_defaults)
        self.btn_load = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/folder-15.png"), 'Load Settings')
        self.btn_load.setToolTip('Load settings from file')
        self.btn_load.clicked.connect(self.on_btn_load)
        self.btn_save = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/save.png"), 'Save Settings')
        self.btn_save.setToolTip('Save settings to file')
        self.btn_save.clicked.connect(self.on_btn_save)
        self.layout_buttons = QtWidgets.QHBoxLayout()
        self.layout_buttons.setSpacing(20)
        self.layout_buttons.addWidget(self.btn_defaults)
        self.layout_buttons.addWidget(self.btn_load)
        self.layout_buttons.addWidget(self.btn_save)
        self.layout_central.addWidget(self.stacked)
        self.layout_central.addStretch()
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
        
    def add_pages(self):
        """
        Adds pages to self.stacked.
        """
        # 1. Generation
        self.page_generation = QtWidgets.QWidget()
        self.layout_generation = QtWidgets.QFormLayout()
        self.layout_generation.setSpacing(10)
        self.combo_gen_method = QtWidgets.QComboBox()
        self.combo_gen_method.addItems(['Guess', 'Iterative', 'Recursive'])
        self.combo_gen_method.setEditable(False)
        self.combo_gen_method.setCurrentIndex(0)
        self.spin_gen_timeout = QtWidgets.QDoubleSpinBox()
        self.spin_gen_timeout.setRange(0.0, 10000.0)
        self.spin_gen_timeout.setValue(60.0)
        self.spin_gen_timeout.setSuffix(' sec.')
        self.combo_log = QtWidgets.QComboBox()
        self.combo_log.addItems(['No log', 'Console', 'File...'])
        self.combo_log.setEditable(True)
        self.combo_log.setCurrentIndex(0)
        self.combo_log.activated.connect(self.on_combo_log)
                
        self.layout_generation.addRow('Method', self.combo_gen_method)
        self.layout_generation.addRow('Timeout', self.spin_gen_timeout)
        self.layout_generation.addRow('Log', self.combo_log)
        
        self.page_generation.setLayout(self.layout_generation)
        self.stacked.addWidget(self.page_generation)
        
        # 2. Sources > Source management
        self.page_src_mgmt = QtWidgets.QWidget()
        self.layout_src_mgmt = QtWidgets.QVBoxLayout()
        
        self.gb_src = QtWidgets.QGroupBox('Manage sources')        
        self.layout_gb_src = QtWidgets.QHBoxLayout()
        self.lw_sources = QtWidgets.QListWidget()
        self.lw_sources.setToolTip('Higher sources in this list take higher precedence (use UP and DOWN buttons to move items)')
        #self.lw_sources.addItems([str(i) for i in range(10)])
        self.lw_sources.itemSelectionChanged.connect(self.on_lw_sources_select)
        self.lw_sources.itemDoubleClicked.connect(self.on_lw_sources_dblclick)
        self.layout_gb_src.addWidget(self.lw_sources)
        
        self.tb_src_mgmt = QtWidgets.QToolBar()
        self.tb_src_mgmt.setOrientation(QtCore.Qt.Vertical)
        self.act_src_up = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-l.png"), 'Up')
        self.act_src_up.triggered.connect(self.on_act_src_up)
        self.act_src_down = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-r.png"), 'Down')
        self.act_src_down.triggered.connect(self.on_act_src_down)        
        self.tb_src_mgmt.addSeparator()
        self.act_src_add = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/plus.png"), 'Add')
        self.act_src_add.triggered.connect(self.on_act_src_add)
        self.act_src_remove = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/minus.png"), 'Remove')
        self.act_src_remove.triggered.connect(self.on_act_src_remove)
        self.act_src_edit = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/edit.png"), 'Edit')
        self.act_src_edit.triggered.connect(self.on_act_src_edit)
        self.act_src_clear = self.tb_src_mgmt.addAction(QtGui.QIcon(f"{ICONFOLDER}/garbage.png"), 'Clear')
        self.act_src_clear.triggered.connect(self.on_act_src_clear)
        self.layout_gb_src.addWidget(self.tb_src_mgmt)
        self.gb_src.setLayout(self.layout_gb_src)
        
        self.gb_src_settings = QtWidgets.QGroupBox('Settings')
        self.layout_src_settings = QtWidgets.QGridLayout()
        self.chb_maxfetch = QtWidgets.QCheckBox('Constrain max results:')
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
                
        # 3. Sources > Search rules
        self.page_src_rules = QtWidgets.QWidget()
        self.layout_src_rules = QtWidgets.QVBoxLayout()        
        self.gb_pos = QtWidgets.QGroupBox('Parts of speech')
        self.layout_gb_pos = QtWidgets.QVBoxLayout()
        self.lw_pos = QtWidgets.QListWidget()
        self.lw_pos.setToolTip('Check / uncheck items to include in search (valid only for sources with POS data)')
        for p in POS[:-1]:
            lwitem = QtWidgets.QListWidgetItem(p[1])
            lwitem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            #lwitem.setData(QtCore.Qt.EditRole, p[0])
            lwitem.setCheckState(QtCore.Qt.Checked if p[0] == 'N' else QtCore.Qt.Unchecked)
            self.lw_pos.addItem(lwitem)
        self.layout_gb_pos.addWidget(self.lw_pos)
        self.gb_pos.setLayout(self.layout_gb_pos)
        self.layout_src_rules.addWidget(self.gb_pos)
        
        self.gb_excluded = QtWidgets.QGroupBox('Excluded words')
        self.layout_gb_excluded = QtWidgets.QVBoxLayout()
        self.te_excluded = QtWidgets.QTextEdit('')
        self.te_excluded.setStyleSheet('font: 14pt "Courier";color: maroon')
        self.te_excluded.setAcceptRichText(False)
        self.te_excluded.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.layout_gb_excluded.addWidget(self.te_excluded)
        self.chb_excl_regex = QtWidgets.QCheckBox('Use regular expressions')
        self.chb_excl_regex.setChecked(False)
        self.layout_gb_excluded.addWidget(self.chb_excl_regex)
        self.gb_excluded.setLayout(self.layout_gb_excluded)
        self.layout_src_rules.addWidget(self.gb_excluded)
        
        self.page_src_rules.setLayout(self.layout_src_rules)
        self.stacked.addWidget(self.page_src_rules)
        
        # 4. UI > Window
        self.page_window = QtWidgets.QWidget()
        self.layout_window = QtWidgets.QFormLayout()
                
        self.combo_apptheme = QtWidgets.QComboBox()
        self.combo_apptheme.addItems(QtWidgets.QStyleFactory.keys())
        self.combo_apptheme.setEditable(False)
        self.combo_apptheme.setCurrentText(QtWidgets.QApplication.instance().style().objectName())
        self.combo_toolbarpos = QtWidgets.QComboBox()
        self.combo_toolbarpos.addItems(['Top', 'Bottom', 'Left', 'Right', 'Hidden'])
        self.combo_toolbarpos.setEditable(False)
        self.combo_toolbarpos.setCurrentIndex(0)
        
        self.layout_window.addRow('Theme', self.combo_apptheme)
        self.layout_window.addRow('Toolbar position', self.combo_toolbarpos)
        self.page_window.setLayout(self.layout_window)
        self.stacked.addWidget(self.page_window)
        
        # 5. UI > Grid
        self.page_grid = QtWidgets.QScrollArea()
        self.page_grid.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.page_grid.setWidgetResizable(True)
        self.layout_grid = QtWidgets.QFormLayout()
        
        self.spin_cwscale = QtWidgets.QSpinBox()
        self.spin_cwscale.setRange(100, 300)
        self.spin_cwscale.setValue(100)        
        self.chb_showgrid = QtWidgets.QCheckBox('')
        self.chb_showgrid.setChecked(True)
        self.chb_showcoords = QtWidgets.QCheckBox('')
        self.chb_showcoords.setChecked(False)
        self.combo_gridlinestyle = QtWidgets.QComboBox()
        self.combo_gridlinestyle.addItems(['Solid', 'Dash', 'Dot', 'Dash-dot'])
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
        self.btn_numbersfont = QtWidgets.QPushButton('Font...')
        self.btn_numbersfont.setStyleSheet('font-family: "Arial"; font-size: 8pt; font-weight: bold;')
        self.btn_numbersfont.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_numbersfont.clicked.connect(self.on_font_btn_clicked)
        self.combo_charcase = QtWidgets.QComboBox()
        self.combo_charcase.addItems(['UPPERCASE', 'lowercase'])
        self.combo_charcase.setEditable(False)
        self.combo_charcase.setCurrentIndex(1)
        
        # cell formatting
        self.btn_cell_normal_bg_color = QtWidgets.QPushButton('')
        self.btn_cell_normal_bg_color.setStyleSheet('background-color: white;')
        self.btn_cell_normal_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_normal_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_cell_normal_style = QtWidgets.QComboBox()
        self.combo_cell_normal_style.addItems(['Solid', 'Dense', 'Striped', 'Lines', 'Checkered', 'Diag1', 'Diag2', 'Diag cross', 'Gradient linear', 'Gradient radial'])
        self.combo_cell_normal_style.setEditable(False)
        self.combo_cell_normal_style.setCurrentIndex(0)
        self.btn_cell_normal_fg_color = QtWidgets.QPushButton('')
        self.btn_cell_normal_fg_color.setStyleSheet('background-color: black;')
        self.btn_cell_normal_fg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_normal_fg_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_cell_normal_font = QtWidgets.QPushButton('Font...')
        self.btn_cell_normal_font.setStyleSheet('font-family: "Arial"; font-size: 18pt; font-weight: bold;')
        self.btn_cell_normal_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_normal_font.clicked.connect(self.on_font_btn_clicked)
        
        self.btn_cell_hilite_bg_color = QtWidgets.QPushButton('')
        self.btn_cell_hilite_bg_color.setStyleSheet('background-color: yellow;')
        self.btn_cell_hilite_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_hilite_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_cell_hilite_style = QtWidgets.QComboBox()
        self.combo_cell_hilite_style.addItems(['Solid', 'Dense', 'Striped', 'Lines', 'Checkered', 'Diag1', 'Diag2', 'Diag cross', 'Gradient linear', 'Gradient radial'])
        self.combo_cell_hilite_style.setEditable(False)
        self.combo_cell_hilite_style.setCurrentIndex(0)
        self.btn_cell_hilite_fg_color = QtWidgets.QPushButton('')
        self.btn_cell_hilite_fg_color.setStyleSheet('background-color: black;')
        self.btn_cell_hilite_fg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_hilite_fg_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_cell_hilite_font = QtWidgets.QPushButton('Font...')
        self.btn_cell_hilite_font.setStyleSheet('font-family: "Arial"; font-size: 18pt; font-weight: bold;')
        self.btn_cell_hilite_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_hilite_font.clicked.connect(self.on_font_btn_clicked)
        
        self.btn_cell_blank_bg_color = QtWidgets.QPushButton('')
        self.btn_cell_blank_bg_color.setStyleSheet('background-color: white;')
        self.btn_cell_blank_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_blank_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_cell_blank_style = QtWidgets.QComboBox()
        self.combo_cell_blank_style.addItems(['Solid', 'Dense', 'Striped', 'Lines', 'Checkered', 'Diag1', 'Diag2', 'Diag cross', 'Gradient linear', 'Gradient radial'])
        self.combo_cell_blank_style.setEditable(False)
        self.combo_cell_blank_style.setCurrentIndex(0)
        
        self.btn_cell_filler_bg_color = QtWidgets.QPushButton('')
        self.btn_cell_filler_bg_color.setStyleSheet('background-color: black;')
        self.btn_cell_filler_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_filler_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_cell_filler_style = QtWidgets.QComboBox()
        self.combo_cell_filler_style.addItems(['Solid', 'Dense', 'Striped', 'Lines', 'Checkered', 'Diag1', 'Diag2', 'Diag cross', 'Gradient linear', 'Gradient radial'])
        self.combo_cell_filler_style.setEditable(False)
        self.combo_cell_filler_style.setCurrentIndex(0)
        
        self.btn_cell_filler2_bg_color = QtWidgets.QPushButton('')
        self.btn_cell_filler2_bg_color.setStyleSheet('background-color: black;')
        self.btn_cell_filler2_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cell_filler2_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_cell_filler2_style = QtWidgets.QComboBox()
        self.combo_cell_filler2_style.addItems(['Solid', 'Dense', 'Striped', 'Lines', 'Checkered', 'Diag1', 'Diag2', 'Diag cross', 'Gradient linear', 'Gradient radial'])
        self.combo_cell_filler2_style.setEditable(False)
        self.combo_cell_filler2_style.setCurrentIndex(0)        
        
        self.layout_grid.addRow('Grid scale', self.spin_cwscale)
        self.layout_grid.addRow('Show grid borders', self.chb_showgrid)
        self.layout_grid.addRow('Show grid coords', self.chb_showcoords)
        self.layout_grid.addRow('Grid border style', self.combo_gridlinestyle)
        self.layout_grid.addRow('Grid border width', self.spin_gridlinesz)
        self.layout_grid.addRow('Grid border color', self.btn_gridlinecolor)
        self.layout_grid.addRow('Active cell color', self.btn_activecellcolor)
        self.layout_grid.addRow('Grid cell size', self.spin_cellsz)
        self.layout_grid.addRow('Character case', self.combo_charcase)
        self.layout_wspacer1 = QtWidgets.QVBoxLayout()
        self.layout_wspacer1.addSpacing(20)        
        self.layout_grid.addRow(self.layout_wspacer1)
        self.layout_grid.addRow('Show word numbers', self.chb_shownumbers)
        self.layout_grid.addRow('Word number color', self.btn_numberscolor)
        self.layout_grid.addRow('Word number font', self.btn_numbersfont)
        self.layout_wspacer2 = QtWidgets.QVBoxLayout()
        self.layout_wspacer2.addSpacing(20)
        self.layout_grid.addRow(self.layout_wspacer2)
        self.layout_grid.addRow('Normal cell color', self.btn_cell_normal_bg_color)
        self.layout_grid.addRow('Normal cell style', self.combo_cell_normal_style)
        self.layout_grid.addRow('Normal cell font color', self.btn_cell_normal_fg_color)
        self.layout_grid.addRow('Normal cell font', self.btn_cell_normal_font)
        self.layout_wspacer3 = QtWidgets.QVBoxLayout()
        self.layout_wspacer3.addSpacing(20)
        self.layout_grid.addRow(self.layout_wspacer3)
        self.layout_grid.addRow('Hilite cell color', self.btn_cell_hilite_bg_color)
        self.layout_grid.addRow('Hilite cell style', self.combo_cell_hilite_style)
        self.layout_grid.addRow('Hilite cell font color', self.btn_cell_hilite_fg_color)
        self.layout_grid.addRow('Hilite cell font', self.btn_cell_hilite_font)
        self.layout_wspacer4 = QtWidgets.QVBoxLayout()
        self.layout_wspacer4.addSpacing(20)
        self.layout_grid.addRow(self.layout_wspacer4)
        self.layout_grid.addRow('Blank cell color', self.btn_cell_blank_bg_color)
        self.layout_grid.addRow('Blank cell style', self.combo_cell_blank_style)
        self.layout_wspacer5 = QtWidgets.QVBoxLayout()
        self.layout_wspacer5.addSpacing(20)
        self.layout_grid.addRow(self.layout_wspacer5)
        self.layout_grid.addRow('Filler cell color', self.btn_cell_filler_bg_color)
        self.layout_grid.addRow('Filler cell style', self.combo_cell_filler_style)
        self.layout_wspacer6 = QtWidgets.QVBoxLayout()
        self.layout_wspacer6.addSpacing(20)
        self.layout_grid.addRow(self.layout_wspacer6)
        self.layout_grid.addRow('Surrounding color', self.btn_cell_filler2_bg_color)
        self.layout_grid.addRow('Surrounding style', self.combo_cell_filler2_style)  
        
        self.widget_layout_grid = QtWidgets.QWidget()
        self.widget_layout_grid.setLayout(self.layout_grid)
        self.page_grid.setWidget(self.widget_layout_grid)
        self.stacked.addWidget(self.page_grid)

        # 6. Clues
        self.page_clues = QtWidgets.QScrollArea()
        self.page_clues.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.page_clues.setWidgetResizable(True)
        self.layout_clues = QtWidgets.QFormLayout()

        self.btn_clue_normal_bg_color = QtWidgets.QPushButton('')
        self.btn_clue_normal_bg_color.setStyleSheet('background-color: white;')
        self.btn_clue_normal_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_normal_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_clue_normal_style = QtWidgets.QComboBox()
        self.combo_clue_normal_style.addItems(['Solid', 'Dense', 'Striped', 'Lines', 'Checkered', 'Diag1', 'Diag2', 'Diag cross', 'Gradient linear', 'Gradient radial'])
        self.combo_clue_normal_style.setEditable(False)
        self.combo_clue_normal_style.setCurrentIndex(0)
        self.btn_clue_normal_fg_color = QtWidgets.QPushButton('')
        self.btn_clue_normal_fg_color.setStyleSheet('background-color: black;')
        self.btn_clue_normal_fg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_normal_fg_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_clue_normal_font = QtWidgets.QPushButton('Font...')
        self.btn_clue_normal_font.setStyleSheet('font-family: "Arial"; font-size: 12pt; font-weight: bold')
        self.btn_clue_normal_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_normal_font.clicked.connect(self.on_font_btn_clicked)
        self.combo_clue_normal_alignment = QtWidgets.QComboBox()
        self.combo_clue_normal_alignment.addItems(['Left', 'Center', 'Right'])
        self.combo_clue_normal_alignment.setEditable(False)
        self.combo_clue_normal_alignment.setCurrentIndex(0)

        self.btn_clue_incomplete_bg_color = QtWidgets.QPushButton('')
        self.btn_clue_incomplete_bg_color.setStyleSheet('background-color: magenta;')
        self.btn_clue_incomplete_bg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_incomplete_bg_color.clicked.connect(self.on_color_btn_clicked)
        self.combo_clue_incomplete_style = QtWidgets.QComboBox()
        self.combo_clue_incomplete_style.addItems(['Solid', 'Dense', 'Striped', 'Lines', 'Checkered', 'Diag1', 'Diag2', 'Diag cross', 'Gradient linear', 'Gradient radial'])
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
        self.combo_clue_complete_style.addItems(['Solid', 'Dense', 'Striped', 'Lines', 'Checkered', 'Diag1', 'Diag2', 'Diag cross', 'Gradient linear', 'Gradient radial'])
        self.combo_clue_complete_style.setEditable(False)
        self.combo_clue_complete_style.setCurrentIndex(0)
        self.btn_clue_complete_fg_color = QtWidgets.QPushButton('')
        self.btn_clue_complete_fg_color.setStyleSheet('background-color: black;')
        self.btn_clue_complete_fg_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clue_complete_fg_color.clicked.connect(self.on_color_btn_clicked)

        self.layout_clues.addRow('Font', self.btn_clue_normal_font)
        self.layout_clues.addRow('Text alignment', self.combo_clue_normal_alignment)
        self.layout_clues_wspacer1 = QtWidgets.QVBoxLayout()
        self.layout_clues_wspacer1.addSpacing(20)
        self.layout_clues.addRow(self.layout_clues_wspacer1)

        self.layout_clues.addRow('Normal color', self.btn_clue_normal_bg_color)
        self.layout_clues.addRow('Normal style', self.combo_clue_normal_style)
        self.layout_clues.addRow('Normal font color', self.btn_clue_normal_fg_color)        
        self.layout_clues_wspacer2 = QtWidgets.QVBoxLayout()
        self.layout_clues_wspacer2.addSpacing(20)
        self.layout_clues.addRow(self.layout_clues_wspacer2)
        self.layout_clues.addRow('Incomplete color', self.btn_clue_incomplete_bg_color)
        self.layout_clues.addRow('Incomplete style', self.combo_clue_incomplete_style)
        self.layout_clues.addRow('Incomplete font color', self.btn_clue_incomplete_fg_color)        
        self.layout_clues_wspacer3 = QtWidgets.QVBoxLayout()
        self.layout_clues_wspacer3.addSpacing(20)
        self.layout_clues.addRow(self.layout_clues_wspacer3)
        self.layout_clues.addRow('Complete color', self.btn_clue_complete_bg_color)
        self.layout_clues.addRow('Complete style', self.combo_clue_complete_style)
        self.layout_clues.addRow('Complete font color', self.btn_clue_complete_fg_color)    
        self.layout_clues_wspacer4 = QtWidgets.QVBoxLayout()
        self.layout_clues_wspacer4.addSpacing(20)
        self.layout_clues.addRow(self.layout_clues_wspacer4)

        self.layout_clues_all = QtWidgets.QVBoxLayout()
        self.layout_clues_all.addLayout(self.layout_clues)

        self.gb_clues_cols = QtWidgets.QGroupBox('Columns')
        self.layout_gb_clues_cols = QtWidgets.QHBoxLayout()
        self.lw_clues_cols = QtWidgets.QListWidget()
        self.lw_clues_cols.setToolTip('Check / uncheck items to show or hide columns, drag to reorder')
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
        self.act_cluecol_up = self.tb_clues_cols.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-l.png"), 'Up')
        self.act_cluecol_up.triggered.connect(self.on_act_cluecol_up)
        self.act_cluecol_down = self.tb_clues_cols.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-r.png"), 'Down')
        self.act_cluecol_down.triggered.connect(self.on_act_cluecol_down)
        self.layout_gb_clues_cols.addWidget(self.tb_clues_cols)

        self.gb_clues_cols.setLayout(self.layout_gb_clues_cols)
        self.layout_clues_all.addWidget(self.gb_clues_cols)

        self.widget_layout_clues = QtWidgets.QWidget()
        self.widget_layout_clues.setLayout(self.layout_clues_all)
        self.page_clues.setWidget(self.widget_layout_clues)
        self.stacked.addWidget(self.page_clues)

        # 7. Definition lookup
        self.page_lookup = QtWidgets.QScrollArea()
        self.page_lookup.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.page_lookup.setWidgetResizable(True)
        self.layout_lookup = QtWidgets.QVBoxLayout()

        # def language
        self.layout_lookup_top = QtWidgets.QFormLayout()
        self.combo_lookup_deflang = QtWidgets.QComboBox()
        for k, v in LANG.items():
            self.combo_lookup_deflang.addItem(v, QtCore.QVariant(k))
        self.combo_lookup_deflang.setEditable(False)
        self.combo_lookup_deflang.setCurrentIndex(0)
        # timeout
        self.spin_lookup_timeout = QtWidgets.QSpinBox()
        self.spin_lookup_timeout.setRange(0, 60)
        self.spin_lookup_timeout.setValue(5)
        self.layout_lookup_top.addRow('Default language:', self.combo_lookup_deflang)
        self.layout_lookup_top.addRow('Request timeout (sec):', self.spin_lookup_timeout)
        self.layout_lookup.addLayout(self.layout_lookup_top)

        # dictionaries
        self.gb_dics = QtWidgets.QGroupBox('Dictionaries')
        self.layout_gb_dics = QtWidgets.QFormLayout()
        self.chb_dics_show = QtWidgets.QCheckBox('')
        self.chb_dics_exact = QtWidgets.QCheckBox('')
        self.chb_dics_showpos = QtWidgets.QCheckBox('')
        self.le_dics_badpos = QtWidgets.QLineEdit('UNKNOWN')
        self.le_dics_apikey_mw = QtWidgets.QLineEdit('')
        self.le_dics_apikey_mw.setToolTip('Merriam-Webster Dictionary API key (empty string to use default)')
        self.le_dics_apikey_yandex = QtWidgets.QLineEdit('')
        self.le_dics_apikey_yandex.setToolTip('Yandex Dictionary API key (empty string to use default)')
        self.layout_gb_dics.addRow('Show:', self.chb_dics_show)
        self.layout_gb_dics.addRow('Exact word match:', self.chb_dics_exact)
        self.layout_gb_dics.addRow('Show parts of speech:', self.chb_dics_showpos)
        self.layout_gb_dics.addRow('Unknown parts of speech:', self.le_dics_badpos)
        self.layout_gb_dics.addRow('Merriam-Webster Dictionary API key:', self.le_dics_apikey_mw)
        self.layout_gb_dics.addRow('Yandex Dictionary API key:', self.le_dics_apikey_yandex)
        self.gb_dics.setLayout(self.layout_gb_dics)
        self.layout_lookup.addWidget(self.gb_dics)

        # google
        self.gb_google = QtWidgets.QGroupBox('Google Search')
        self.layout_gb_google = QtWidgets.QFormLayout()
        self.chb_google_show = QtWidgets.QCheckBox('')
        self.chb_google_exact = QtWidgets.QCheckBox('')
        self.chb_google_safe = QtWidgets.QCheckBox('')
        self.le_google_filetypes = QtWidgets.QLineEdit('')
        self.le_google_filetypes.setToolTip('Add file types delimited by SPACE, e.g. "txt doc pdf"')
        self.chb_google_lang_all = QtWidgets.QCheckBox('ALL')
        self.chb_google_lang_all.setTristate(True)
        self.chb_google_lang_all.setCheckState(QtCore.Qt.Unchecked)
        self.chb_google_lang_all.stateChanged.connect(self.on_chb_google_lang_all) #
        self.lw_google_lang = QtWidgets.QListWidget()
        self.lw_google_lang.setToolTip('Search documents restricted only to checked languages')
        d = GoogleSearch.get_document_languages()
        for l in d:
            lwitem = QtWidgets.QListWidgetItem(d[l])
            lwitem.setData(QtCore.Qt.StatusTipRole, l)
            lwitem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)            
            lwitem.setCheckState(QtCore.Qt.Unchecked)
            self.lw_google_lang.addItem(lwitem)
        self.lw_google_lang.itemChanged.connect(self.on_lw_google_lang_changed) #
        self.chb_google_interface_lang_all = QtWidgets.QCheckBox('ALL')
        self.chb_google_interface_lang_all.setTristate(True)
        self.chb_google_interface_lang_all.setCheckState(QtCore.Qt.Unchecked)
        self.chb_google_interface_lang_all.stateChanged.connect(self.on_chb_google_interface_lang_all) #
        self.lw_google_interface_lang = QtWidgets.QListWidget()
        self.lw_google_interface_lang.setToolTip('Search using only checked interface languages')
        d = GoogleSearch.get_interface_languages()
        for l in d:
            lwitem = QtWidgets.QListWidgetItem(d[l])
            lwitem.setData(QtCore.Qt.StatusTipRole, l)
            lwitem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)            
            lwitem.setCheckState(QtCore.Qt.Unchecked)
            self.lw_google_interface_lang.addItem(lwitem)
        self.lw_google_interface_lang.itemChanged.connect(self.on_lw_google_interface_lang_changed) #
        self.chb_google_geo_all = QtWidgets.QCheckBox('ALL')
        self.chb_google_geo_all.setTristate(True)
        self.chb_google_geo_all.setCheckState(QtCore.Qt.Unchecked)
        self.chb_google_geo_all.stateChanged.connect(self.on_chb_google_geo_all) #
        self.lw_google_geo = QtWidgets.QListWidget()
        self.lw_google_geo.setToolTip('Search in checked locations only')
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
        self.spin_google_nresults.setToolTip('Limit returned results for page (-1 = no limit)')
        self.spin_google_nresults.setRange(-1, 10)
        self.spin_google_nresults.setValue(-1)
        self.le_google_apikey = QtWidgets.QLineEdit('')
        self.le_google_apikey.setToolTip('Google Custom Search API key (empty string to use default)')
        self.le_google_cseid = QtWidgets.QLineEdit('')
        self.le_google_cseid.setToolTip('Google Custom Search CSE ID (empty string to use default)')

        self.layout_gb_google.addRow('Show:', self.chb_google_show)
        self.layout_gb_google.addRow('Exact phrase:', self.chb_google_exact)
        self.layout_gb_google.addRow('File types:', self.le_google_filetypes)
        self.layout_gb_google.addRow('', self.chb_google_lang_all)
        self.layout_gb_google.addRow('Document languages:', self.lw_google_lang)
        self.layout_gb_google.addRow('', self.chb_google_interface_lang_all)
        self.layout_gb_google.addRow('Interface languages:', self.lw_google_interface_lang)
        self.layout_gb_google.addRow('', self.chb_google_geo_all)
        self.layout_gb_google.addRow('Locations:', self.lw_google_geo)
        self.layout_gb_google.addRow('Link site:', self.le_google_linksite)
        self.layout_gb_google.addRow('Related (parent) site:', self.le_google_relatedsite)
        self.layout_gb_google.addRow('Search in site:', self.le_google_insite)
        self.layout_gb_google.addRow('Results per page:', self.spin_google_nresults)
        self.layout_gb_google.addRow('Safe filter:', self.chb_google_safe)
        self.layout_gb_google.addRow('Google Custom Search API key:', self.le_google_apikey)
        self.layout_gb_google.addRow('Google Custom Search CSE ID:', self.le_google_cseid)

        self.gb_google.setLayout(self.layout_gb_google)
        self.layout_lookup.addWidget(self.gb_google)

        self.widget_layout_lookup = QtWidgets.QWidget()
        self.widget_layout_lookup.setLayout(self.layout_lookup)
        self.page_lookup.setWidget(self.widget_layout_lookup)
        self.stacked.addWidget(self.page_lookup)

        # 8. Import & Export
        self.page_importexport = QtWidgets.QWidget()
        self.layout_importexport = QtWidgets.QVBoxLayout()
        self.layout_importexport.setSpacing(10)

        self.gb_export = QtWidgets.QGroupBox('Export')
        self.layout_gb_export = QtWidgets.QFormLayout()
        self.chb_export_openfile = QtWidgets.QCheckBox('')
        self.chb_export_clearcw = QtWidgets.QCheckBox('')
        self.spin_export_resolution_img = QtWidgets.QSpinBox()
        self.spin_export_resolution_img.setRange(0, 2400)
        self.spin_export_resolution_img.setSuffix(' dpi')
        self.spin_export_resolution_pdf = QtWidgets.QSpinBox()
        self.spin_export_resolution_pdf.setRange(0, 2400)
        self.spin_export_resolution_pdf.setSuffix(' dpi')
        self.spin_export_cellsize = QtWidgets.QSpinBox()
        self.spin_export_cellsize.setRange(2, 100)
        self.spin_export_cellsize.setSuffix(' mm')
        self.spin_export_quality = QtWidgets.QSpinBox()
        self.spin_export_quality.setRange(-1, 100)
        self.spin_export_quality.setSuffix(' %')
        self.spin_export_quality.setToolTip('Quality in percent (set to -1 for auto quality)')
        self.btn_export_auto_resolution_img = QtWidgets.QPushButton('Auto')
        self.btn_export_auto_resolution_img.clicked.connect(self.on_btn_export_auto_resolution_img)
        self.btn_export_auto_resolution_pdf = QtWidgets.QPushButton('Auto')
        self.btn_export_auto_resolution_pdf.clicked.connect(self.on_btn_export_auto_resolution_pdf)
        self.layout_export_resolution_img = QtWidgets.QHBoxLayout()
        self.layout_export_resolution_img.addWidget(self.spin_export_resolution_img)
        self.layout_export_resolution_img.addWidget(self.btn_export_auto_resolution_img)
        self.layout_export_resolution_pdf = QtWidgets.QHBoxLayout()
        self.layout_export_resolution_pdf.addWidget(self.spin_export_resolution_pdf)
        self.layout_export_resolution_pdf.addWidget(self.btn_export_auto_resolution_pdf)
        self.le_svg_title = QtWidgets.QLineEdit()
        self.le_svg_description = QtWidgets.QLineEdit()
        self.layout_gb_export.addRow('Image resolution', self.layout_export_resolution_img)
        self.layout_gb_export.addRow('PDF resolution', self.layout_export_resolution_pdf)
        self.layout_gb_export.addRow('Image quality', self.spin_export_quality)
        self.layout_gb_export.addRow('Output grid cell size', self.spin_export_cellsize)
        self.layout_gb_export.addRow('SVG image title', self.le_svg_title)
        self.layout_gb_export.addRow('SVG image description', self.le_svg_description)
        self.layout_gb_export.addRow('Clear crossword before export', self.chb_export_clearcw)
        self.layout_gb_export.addRow('Open exported file', self.chb_export_openfile)
        self.gb_export.setLayout(self.layout_gb_export)
        self.layout_importexport.addWidget(self.gb_export)

        self.page_importexport.setLayout(self.layout_importexport)
        self.stacked.addWidget(self.page_importexport)

        # 9. Plugins
        self.page_plugins = QtWidgets.QWidget()
        self.layout_plugins = QtWidgets.QFormLayout()
        self.layout_plugins.setSpacing(10)
        self.page_plugins.setLayout(self.layout_plugins)
        self.stacked.addWidget(self.page_plugins)

        # 10. Printing
        self.page_printing = QtWidgets.QScrollArea()
        self.page_printing.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.page_printing.setWidgetResizable(True)
        self.layout_printing = QtWidgets.QVBoxLayout()
        self.layout_printing.setSpacing(10)

        self.layout_combo_print_layout = QtWidgets.QFormLayout()
        self.combo_print_layout = QtWidgets.QComboBox()
        self.combo_print_layout.addItems(['Auto', 'Portrait', 'Landscape'])
        self.combo_print_layout.setEditable(False)
        self.le_print_title = QtWidgets.QLineEdit('<title>')
        self.le_print_clues_title = QtWidgets.QLineEdit('Clues')

        self.layout_combo_print_layout.addRow('Page layout', self.combo_print_layout)
        self.layout_combo_print_layout.addRow('Crossword title', self.le_print_title)
        self.layout_combo_print_layout.addRow('Clues title (header)', self.le_print_clues_title)

        self.gb_print_margins = QtWidgets.QGroupBox('Margins')
        self.layout_gb_print_margins = QtWidgets.QFormLayout()
        self.spin_margin_left = QtWidgets.QSpinBox()
        self.spin_margin_left.setRange(0, 50)
        self.spin_margin_left.setSuffix(' mm')
        self.spin_margin_right = QtWidgets.QSpinBox()
        self.spin_margin_right.setRange(0, 50)
        self.spin_margin_right.setSuffix(' mm')
        self.spin_margin_top = QtWidgets.QSpinBox()
        self.spin_margin_top.setRange(0, 100)
        self.spin_margin_top.setSuffix(' mm')
        self.spin_margin_bottom = QtWidgets.QSpinBox()
        self.spin_margin_bottom.setRange(0, 100)
        self.spin_margin_bottom.setSuffix(' mm')
        self.layout_gb_print_margins.addRow('Left', self.spin_margin_left)
        self.layout_gb_print_margins.addRow('Right', self.spin_margin_right)
        self.layout_gb_print_margins.addRow('Top', self.spin_margin_top)
        self.layout_gb_print_margins.addRow('Bottom', self.spin_margin_bottom)
        self.gb_print_margins.setLayout(self.layout_gb_print_margins)
        self.chb_print_font_embed = QtWidgets.QCheckBox('Embed fonts')
        self.chb_print_antialias = QtWidgets.QCheckBox('Antialiasing')
        self.chb_print_print_cw = QtWidgets.QCheckBox('Print crossword grid')
        self.chb_print_print_clues = QtWidgets.QCheckBox('Print clues')
        self.chb_print_clear_cw = QtWidgets.QCheckBox('Empty grid')
        self.chb_print_print_cw.toggled.connect(self.chb_print_clear_cw.setEnabled)
        self.chb_print_print_clue_letters = QtWidgets.QCheckBox('Include word size hint')
        self.chb_print_print_clues.toggled.connect(self.chb_print_print_clue_letters.setEnabled)
        self.chb_print_print_info = QtWidgets.QCheckBox('Print crossword information')
        self.chb_print_color_print = QtWidgets.QCheckBox('Colored output')        
        self.chb_print_openfile = QtWidgets.QCheckBox('Open file (PDF) on print complete')        

        self.gb_print_fonts = QtWidgets.QGroupBox('Fonts')
        self.layout_gb_print_fonts = QtWidgets.QFormLayout()

        self.btn_print_header_color = QtWidgets.QPushButton('')
        self.btn_print_header_color.setStyleSheet('background-color: blue;')
        self.btn_print_header_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_header_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_print_header_font = QtWidgets.QPushButton('Font...')
        self.btn_print_header_font.setStyleSheet('font-family: "Verdana"; font-size: 20pt; font-weight: bold;')
        self.btn_print_header_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_header_font.clicked.connect(self.on_font_btn_clicked)

        self.btn_print_info_color = QtWidgets.QPushButton('')
        self.btn_print_info_color.setStyleSheet('background-color: blue;')
        self.btn_print_info_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_info_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_print_info_font = QtWidgets.QPushButton('Font...')
        self.btn_print_info_font.setStyleSheet('font-family: "Verdana"; font-size: 20pt; font-weight: bold;')
        self.btn_print_info_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_info_font.clicked.connect(self.on_font_btn_clicked)

        self.btn_print_clue_number_color = QtWidgets.QPushButton('')
        self.btn_print_clue_number_color.setStyleSheet('background-color: blue;')
        self.btn_print_clue_number_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_number_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_print_clue_number_font = QtWidgets.QPushButton('Font...')
        self.btn_print_clue_number_font.setStyleSheet('font-family: "Verdana"; font-size: 20pt; font-weight: bold;')
        self.btn_print_clue_number_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_number_font.clicked.connect(self.on_font_btn_clicked)

        self.btn_print_clue_text_color = QtWidgets.QPushButton('')
        self.btn_print_clue_text_color.setStyleSheet('background-color: blue;')
        self.btn_print_clue_text_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_text_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_print_clue_text_font = QtWidgets.QPushButton('Font...')
        self.btn_print_clue_text_font.setStyleSheet('font-family: "Verdana"; font-size: 20pt; font-weight: bold;')
        self.btn_print_clue_text_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_text_font.clicked.connect(self.on_font_btn_clicked)

        self.btn_print_clue_sizehint_color = QtWidgets.QPushButton('')
        self.btn_print_clue_sizehint_color.setStyleSheet('background-color: blue;')
        self.btn_print_clue_sizehint_color.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_sizehint_color.clicked.connect(self.on_color_btn_clicked)
        self.btn_print_clue_sizehint_font = QtWidgets.QPushButton('Font...')
        self.btn_print_clue_sizehint_font.setStyleSheet('font-family: "Verdana"; font-size: 20pt; font-weight: bold;')
        self.btn_print_clue_sizehint_font.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_print_clue_sizehint_font.clicked.connect(self.on_font_btn_clicked)

        self.layout_gb_print_fonts.addRow('Title color', self.btn_print_header_color)
        self.layout_gb_print_fonts.addRow('Title font', self.btn_print_header_font)
        self.layout_gb_print_fonts.addRow('Info color', self.btn_print_info_color)
        self.layout_gb_print_fonts.addRow('Info font', self.btn_print_info_font)
        self.layout_gb_print_fonts.addRow('Clues color', self.btn_print_clue_text_color)
        self.layout_gb_print_fonts.addRow('Clues font', self.btn_print_clue_text_font)
        self.layout_gb_print_fonts.addRow('Word number color', self.btn_print_clue_number_color)
        self.layout_gb_print_fonts.addRow('Word number font', self.btn_print_clue_number_font)
        self.layout_gb_print_fonts.addRow('Word size hint color', self.btn_print_clue_sizehint_color)
        self.layout_gb_print_fonts.addRow('Word size hint font', self.btn_print_clue_sizehint_font)
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

        # 11. Updating
        self.page_updating = QtWidgets.QWidget()
        self.layout_updating = QtWidgets.QFormLayout()
        self.layout_updating.setSpacing(10)

        self.spin_update_period = QtWidgets.QSpinBox()
        self.spin_update_period.setRange(-1, 365)
        self.spin_update_period.setSuffix(' days')
        self.spin_update_period.setToolTip('Set to -1 to disable update checks')
        self.chb_update_auto = QtWidgets.QCheckBox('')
        self.chb_update_major_only = QtWidgets.QCheckBox('')
        self.chb_update_restart = QtWidgets.QCheckBox('')
        self.le_update_tempdir = QtWidgets.QLineEdit('')
        self.le_update_tempdir.setToolTip('Temp directory (leave empty for default)')
        self.act_update_tempdir_browse = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/folder-2.png"), 'Browse', None)
        self.act_update_tempdir_browse.setToolTip('Browse')
        self.act_update_tempdir_browse.triggered.connect(self.on_act_update_tempdir_browse)
        self.btn_update_tempdir_browse = QtWidgets.QToolButton()
        self.btn_update_tempdir_browse.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.btn_update_tempdir_browse.setDefaultAction(self.act_update_tempdir_browse)
        self.layout_update_tempdir = QtWidgets.QHBoxLayout()
        self.layout_update_tempdir.addWidget(self.le_update_tempdir)
        self.layout_update_tempdir.addWidget(self.btn_update_tempdir_browse)
        self.le_update_logfile = QtWidgets.QLineEdit('')
        self.le_update_logfile.setToolTip('Log file for update operations')
        self.act_update_log_browse = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/folder-2.png"), 'Browse', None)
        self.act_update_log_browse.setToolTip('Browse')
        self.act_update_log_browse.triggered.connect(self.on_act_update_log_browse)
        self.btn_update_log_browse = QtWidgets.QToolButton()
        self.btn_update_log_browse.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.btn_update_log_browse.setDefaultAction(self.act_update_log_browse)
        self.layout_update_log = QtWidgets.QHBoxLayout()
        self.layout_update_log.addWidget(self.le_update_logfile)
        self.layout_update_log.addWidget(self.btn_update_log_browse)

        self.layout_updating.addRow('Check for updates every', self.spin_update_period)
        self.layout_updating.addRow('Check / update major releases only', self.chb_update_major_only)
        self.layout_updating.addRow('Auto update', self.chb_update_auto)
        self.layout_updating.addRow('Restart on update', self.chb_update_restart)
        self.layout_updating.addRow('Temp directory', self.layout_update_tempdir)
        self.layout_updating.addRow('Log file', self.layout_update_log)

        self.page_updating.setLayout(self.layout_updating)
        self.stacked.addWidget(self.page_updating)

    def _fill_clue_cols(self):
        self.lw_clues_cols.clear()
        for col in CWSettings.settings['clues']['columns']:
            lwitem = QtWidgets.QListWidgetItem(col['name'])
            if col['name'] == 'Direction':
                lwitem.setFlags(QtCore.Qt.NoItemFlags)
                lwitem.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.red), QtCore.Qt.SolidPattern))
            else:
                lwitem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled)                
            lwitem.setCheckState(QtCore.Qt.Checked if col['visible'] else QtCore.Qt.Unchecked)
            self.lw_clues_cols.addItem(lwitem)

    def to_settings(self):
        """
        Saves settings in CWSettings.settings format.
        It doesn't update CWSettings.settings automatically!
        """
        
        settings = {'gui': {}, 'cw_settings': {}, 'grid_style': {}, 'cell_format': {}, 
                    'wordsrc': {}, 'clues': {}, 'lookup': {}, 'printing': {}, 'export': {},
                    'update': {}}
        
        # user interface
        settings['gui']['theme'] = self.combo_apptheme.currentText()
        settings['gui']['toolbar_pos'] = self.combo_toolbarpos.currentIndex()
        settings['gui']['win_pos'] = (self.mainwindow.pos().x(), self.mainwindow.pos().y())
        settings['gui']['win_size'] = (self.mainwindow.width(), self.mainwindow.height())
        
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
        if log == 'No log':
            settings['cw_settings']['log'] = None
        elif log == 'Console':
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
                print('No user data in src!')
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
        # columns
        settings['clues']['columns'] = []
        for i in range(self.lw_clues_cols.count()):
            item = self.lw_clues_cols.item(i)
            settings['clues']['columns'].append({'name': item.text(), 
                'visible': bool(item.checkState()), 'width': -1})
            
        # lookup
        settings['lookup']['default_lang'] = self.combo_lookup_deflang.currentData()
        settings['lookup']['timeout'] = self.spin_lookup_timeout.value()

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
        settings['update']['temp_dir'] = self.le_update_tempdir.text()
        settings['update']['logfile'] = os.path.relpath(self.le_update_logfile.text(), os.path.dirname(__file__)) if self.le_update_logfile.text() else ''
        
        return settings

    def _set_spin_value_safe(self, spin, val):
        if val < spin.minimum():
            val = spin.minimum()
        elif val > spin.maximum():
            val = spin.maximum()
        spin.setValue(val)
    
    def from_settings(self, settings=None, page=None):
        """
        Updates GUI controls from 'settings' dict.
        If 'settings' is None, CWSettings.settings is used.
        GUI controls are updated only on page given by 'page' (name),
        or on all pages in 'page' == None.
        """
        
        if settings is None:
            settings = CWSettings.settings
        
        # engine
        if page is None or page == 'Generation':
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
        if page is None or page == 'Source management':
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
        if page is None or page == 'Search rules':
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
        if page is None or page == 'Window':
            index = self.combo_apptheme.findText(settings['gui']['theme'])
            if index >= 0:
                self.combo_apptheme.setCurrentIndex(index)
            index = settings['gui']['toolbar_pos']
            if index >=0 and index <5:
                self.combo_toolbarpos.setCurrentIndex(index)
        
        # UI > grid
        if page is None or page == 'Grid':
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
        if page is None or page == 'Clues':
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

            # columns
            self._fill_clue_cols()
        
        # Lookup
        if page is None or page == 'Definition lookup':
            self.combo_lookup_deflang.setCurrentText(LANG[settings['lookup']['default_lang']])
            self._set_spin_value_safe(self.spin_lookup_timeout, settings['lookup']['timeout'])

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

        # Import & Expo
        if page is None or page == 'Import & Export':

            settings = CWSettings.settings['export']

            self.chb_export_openfile.setChecked(settings['openfile'])
            self.chb_export_clearcw.setChecked(settings['clear_cw'])
            self._set_spin_value_safe(self.spin_export_resolution_img, settings['img_resolution'])
            self._set_spin_value_safe(self.spin_export_resolution_pdf, settings['pdf_resolution'])
            self._set_spin_value_safe(self.spin_export_cellsize, settings['mm_per_cell'])
            self._set_spin_value_safe(self.spin_export_quality, settings['img_output_quality'])
            self.le_svg_title.setText(settings['svg_title'])
            self.le_svg_description.setText(settings['svg_description'])
        
        # Plugins
        if page is None or page == 'Plugins':
            pass
        
        # Printing
        if page is None or page == 'Printing':

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
        if page is None or page == 'Updating':
            
            settings = CWSettings.settings['update']
            self._set_spin_value_safe(self.spin_update_period, settings['check_every'])
            self.chb_update_auto.setChecked(settings['auto_update'])
            self.chb_update_major_only.setChecked(settings['only_major_versions'])
            self.chb_update_restart.setChecked(settings['restart_on_update'])
            self.le_update_tempdir.setText(settings['temp_dir'])
            self.le_update_logfile.setText(settings['logfile'])
    
    def addoredit_wordsrc(self, src, src_item=None):
        """
        Adds a new word source from 'src' dict
        or assigns it to existing 'src_item' (of type QtWidgets.QListWidgetItem).
        See dict format in WordSrcDialog docs.
        """
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
    
    def showEvent(self, event):
        # read settings
        self.from_settings()
    
    @QtCore.pyqtSlot()        
    def on_tree_select(self):
        item = self.tree.currentItem()
        if not item: return
        txt = item.text(0)
        if txt == 'Generation':
            self.stacked.setCurrentIndex(0)
        elif txt == 'Source management':
            self.stacked.setCurrentIndex(1)
        elif txt == 'Search rules':
            self.stacked.setCurrentIndex(2)
        elif txt == 'Window':
            self.stacked.setCurrentIndex(3)
        elif txt == 'Grid':
            self.stacked.setCurrentIndex(4)
        elif txt == 'Clues':
            self.stacked.setCurrentIndex(5)
        elif txt == 'Definition lookup':
            self.stacked.setCurrentIndex(6)
        elif txt == 'Import & Export':
            self.stacked.setCurrentIndex(7)
        elif txt == 'Plugins':
            self.stacked.setCurrentIndex(8)
        elif txt == 'Printing':
            self.stacked.setCurrentIndex(9)
        elif txt == 'Updating':
            self.stacked.setCurrentIndex(10)
        elif txt in ('Sources', 'User interface'):
            item.setExpanded(True)
            self.tree.setCurrentItem(item.child(0))
            
    @QtCore.pyqtSlot(bool) 
    def on_btn_defaults(self, checked):
        """
        Restore default settings for current page or for all pages.
        """
        btn = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, 'Restore defaults', 
            'Press YES to restore defaults only for current page and YES TO ALL to restore all default settings', 
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.YesToAll | QtWidgets.QMessageBox.Cancel, self).exec()
        if btn != QtWidgets.QMessageBox.Cancel:
            self.from_settings(self.default_settings, self.tree.currentItem().text(0) if btn == QtWidgets.QMessageBox.Yes else None)

    @QtCore.pyqtSlot(bool) 
    def on_btn_load(self, checked):
        """
        Loads settings from file for current page or for all pages.
        """
        btn = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, 'Load defaults', 
            'Press YES to load settings only for current page and YES TO ALL to load all settings', 
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.YesToAll | QtWidgets.QMessageBox.Cancel, self).exec()
        if btn == QtWidgets.QMessageBox.Cancel: return
        selected_path = QtWidgets.QFileDialog.getOpenFileName(self, 'Select file', os.getcwd(), 'Settings files (*.json)')
        if not selected_path[0]: return
        selected_path = selected_path[0].replace('/', os.sep).lower()
        settings = CWSettings.validate_file(selected_path)
        if not settings: 
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', 
            f"File '{selected_path}' has a wrong format or incomplete settings!", QtWidgets.QMessageBox.Ok, self).exec()
            return
        self.from_settings(settings, self.tree.currentItem().text(0) if btn == QtWidgets.QMessageBox.Yes else None)

    @QtCore.pyqtSlot(bool) 
    def on_btn_save(self, checked):
        """
        Saves current settings to file.
        """
        selected_path = QtWidgets.QFileDialog.getSaveFileName(self, 'Select file', os.path.join(os.getcwd(), 'settings.json'), 'Settings files (*.json)')
        if not selected_path[0]: return
        selected_path = selected_path[0].replace('/', os.sep).lower()
        CWSettings.save_to_file(selected_path)

    @QtCore.pyqtSlot(int)
    def on_combo_log(self, index):
        """
        When a log combo item is selected.
        """
        if index == 2:
            selected_path = QtWidgets.QFileDialog.getSaveFileName(self, 'Select file', os.getcwd(), 'All files (*.*)')
            if selected_path[0]:
                self.combo_log.setCurrentText(selected_path[0].replace('/', os.sep))
            
    @QtCore.pyqtSlot()        
    def on_lw_sources_select(self):
        item = self.lw_sources.currentItem()
        if not item: return
        #print(item.data(QtCore.Qt.UserRole))
        
    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def on_lw_sources_dblclick(self, item):
        self.on_act_src_edit(False)
            
    @QtCore.pyqtSlot(int)
    def on_chb_maxfetch_checked(self, state):
        self.spin_maxfetch.setEnabled(bool(state))
        
    @QtCore.pyqtSlot(bool)        
    def on_act_src_up(self, checked):
        item = self.lw_sources.currentItem()
        if not item: return
        row = self.lw_sources.row(item)
        if not row: return
        self.lw_sources.insertItem(row - 1, self.lw_sources.takeItem(row))
        self.lw_sources.setCurrentRow(row - 1)
    
    @QtCore.pyqtSlot(bool)        
    def on_act_src_down(self, checked):
        item = self.lw_sources.currentItem()
        if not item: return
        row = self.lw_sources.row(item)
        if row == (self.lw_sources.count() - 1): return
        self.lw_sources.insertItem(row + 1, self.lw_sources.takeItem(row))
        self.lw_sources.setCurrentRow(row + 1)
    
    @QtCore.pyqtSlot(bool)        
    def on_act_src_add(self, checked):
        dia_src = WordSrcDialog()
        if not dia_src.exec(): return
        self.addoredit_wordsrc(dia_src.src)
    
    @QtCore.pyqtSlot(bool)        
    def on_act_src_remove(self, checked):
        row = self.lw_sources.currentRow()
        if row < 0: return
        self.lw_sources.takeItem(row)
    
    @QtCore.pyqtSlot(bool)        
    def on_act_src_edit(self, checked):
        item = self.lw_sources.currentItem()
        if not item: return
        try:
            src = json.loads(item.data(QtCore.Qt.UserRole))
            if not src or not isinstance(src, dict):
                print('No user data in src!')
                return
            b_active = src['active']
            dia_src = WordSrcDialog(src)
            if not dia_src.exec(): return
            dia_src.src['active'] = b_active
            self.addoredit_wordsrc(dia_src.src, item)
        except Exception as err:
            print(err)
            return
    
    @QtCore.pyqtSlot(bool)        
    def on_act_src_clear(self, checked):
        self.lw_sources.clear()

    @QtCore.pyqtSlot(bool)        
    def on_act_cluecol_up(self, checked):
        item = self.lw_clues_cols.currentItem()
        if not item: return
        row = self.lw_clues_cols.row(item)
        if row < 2: return
        self.lw_clues_cols.insertItem(row - 1, self.lw_clues_cols.takeItem(row))
        self.lw_clues_cols.setCurrentRow(row - 1)
    
    @QtCore.pyqtSlot(bool)        
    def on_act_cluecol_down(self, checked):
        item = self.lw_clues_cols.currentItem()
        if not item: return
        row = self.lw_clues_cols.row(item)
        if row == 0 or row == (self.lw_clues_cols.count() - 1): return
        self.lw_clues_cols.insertItem(row + 1, self.lw_clues_cols.takeItem(row))
        self.lw_clues_cols.setCurrentRow(row + 1)
        
    @QtCore.pyqtSlot(bool)        
    def on_color_btn_clicked(self, checked):
        """
        Triggers when any of the color select buttons is clicked.
        """
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
            
    @QtCore.pyqtSlot(bool)        
    def on_font_btn_clicked(self, checked):
        """
        Triggers when any of the font select buttons is clicked.
        """
        btn = self.sender()
        if not btn: return
        # get btn font
        style = btn.styleSheet()
        #print(f"BTN '{btn.objectName()}': {style}")
        font = font_from_stylesheet(style)        
        # show font dialog
        new_font = QtWidgets.QFontDialog.getFont(font, self, 'Choose font')
        if new_font[1]:
            btn.setStyleSheet(font_to_stylesheet(new_font[0], style))

    @QtCore.pyqtSlot(int)        
    def on_chb_google_lang_all(self, state):
        if state == QtCore.Qt.Checked or state == QtCore.Qt.Unchecked:
            self.chb_google_lang_all.stateChanged.disconnect()
            self.lw_google_lang.itemChanged.disconnect()
            for i in range(self.lw_google_lang.count()):
                self.lw_google_lang.item(i).setCheckState(state)
            self.chb_google_lang_all.stateChanged.connect(self.on_chb_google_lang_all)
            self.lw_google_lang.itemChanged.connect(self.on_lw_google_lang_changed)

    @QtCore.pyqtSlot(int)        
    def on_chb_google_interface_lang_all(self, state):
        if state == QtCore.Qt.Checked or state == QtCore.Qt.Unchecked:
            self.chb_google_interface_lang_all.stateChanged.disconnect()
            self.lw_google_interface_lang.itemChanged.disconnect()
            for i in range(self.lw_google_interface_lang.count()):
                self.lw_google_interface_lang.item(i).setCheckState(state)
            self.chb_google_interface_lang_all.stateChanged.connect(self.on_chb_google_interface_lang_all)
            self.lw_google_interface_lang.itemChanged.connect(self.on_lw_google_interface_lang_changed)

    @QtCore.pyqtSlot(int)        
    def on_chb_google_geo_all(self, state):
        if state == QtCore.Qt.Checked or state == QtCore.Qt.Unchecked:
            self.chb_google_geo_all.stateChanged.disconnect()
            self.lw_google_geo.itemChanged.disconnect()
            for i in range(self.lw_google_geo.count()):
                self.lw_google_geo.item(i).setCheckState(state)
            self.chb_google_geo_all.stateChanged.connect(self.on_chb_google_geo_all)
            self.lw_google_geo.itemChanged.connect(self.on_lw_google_geo_changed)

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

    @QtCore.pyqtSlot() 
    def on_btn_export_auto_resolution_img(self):
        self.spin_export_resolution_img.setValue(72)

    @QtCore.pyqtSlot() 
    def on_btn_export_auto_resolution_pdf(self):
        self.spin_export_resolution_pdf.setValue(1200)

    @QtCore.pyqtSlot(bool)        
    def on_act_update_tempdir_browse(self, checked):
        """
        Browse for temp dir.
        """
        current_dir = self.le_update_tempdir.text()
        default_dir = get_tempdir().replace('/', os.sep).lower()
        selected_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select directory', current_dir or default_dir)
        selected_path = selected_path.replace('/', os.sep).lower()
        if selected_path:
            self.le_file.setText(selected_path if selected_path != default_dir else '')

    @QtCore.pyqtSlot(bool)        
    def on_act_update_log_browse(self, checked):
        """
        Browse for log file.
        """
        current_file = make_abspath(self.le_update_logfile.text())
        default_file = os.path.join(os.getcwd(), 'update.log')
        selected_path = QtWidgets.QFileDialog.getSaveFileName(self, 'Select file', current_file or default_file, 'All files (*.*)')
        if not selected_path[0]: return
        selected_path =  os.path.relpath(selected_path[0], os.path.dirname(__file__)).replace('/', os.sep)
        self.le_update_logfile.setText(selected_path)
        
##############################################################################
######          CwTable
############################################################################## 

class CwTable(QtWidgets.QTableWidget):
    
    def __init__(self, on_key=None, parent: QtWidgets.QWidget=None):
        self.on_key = on_key
        super().__init__(parent)        
        
    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        #super().keyReleaseEvent(event)
        if self.on_key: self.on_key(event)
        
    def keyboardSearch(self, search: str):
        # override this to disable keyboard search
        return
    
    """
    def wheelEvent(self, event: QtGui.QWheelEvent):
        # override mouse wheel for zooming
        event.ignore()
    """

##############################################################################
######          ClickableLabel
############################################################################## 

class ClickableLabel(QtWidgets.QLabel):

    clicked = QtCore.pyqtSignal(QtGui.QMouseEvent)
    dblclicked = QtCore.pyqtSignal(QtGui.QMouseEvent)

    def __init__(self, parent: QtWidgets.QWidget=None, flags: QtCore.Qt.WindowFlags=QtCore.Qt.WindowFlags()):
        super().__init__(parent)

    def mousePressEvent(self, event):
        self.clicked.emit(event)

    def mouseDoubleClickEvent(self, event):
        self.dblclicked.emit(event)
        
        
##############################################################################
######          CrosswordMenu
##############################################################################    
        
class CrosswordMenu(QtWidgets.QMenu):
    
    def __init__(self, mainwindow, on_triggered=None, parent=None):
        self.mainwindow = mainwindow
        super().__init__(parent=parent)
        self.initActions()
        if on_triggered: self.triggered.connect(on_triggered)
        
    def initActions(self):
        #self.setTitle('')
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
   

##############################################################################
######          WordSuggestDialog
##############################################################################  
        
class WordSuggestDialog(BasicDialog):
    
    def __init__(self, mainwindow, word='', word_editable=False, getresults=None, 
                parent=None, flags=QtCore.Qt.WindowFlags()):
        """
        Params:
        * mainwindow [QWidget]: the main application window
        * word [str]: the word string to look up in suggestions
        * word_editable [bool]: if the word string can be edited directly in the dialog
        * getresults [callable]: pointer to function that retrieves suggestions;
            this function takes one argument - the word string, and returns suggestions as a list of strings
        * parent, flags: see BasicDialog
        """
        self.mainwindow = mainwindow
        self.sortdir = ''       
        self.word = word
        self.word_editable = word_editable
        self.getresults = getresults 
        self.results = []
        self.selected = ''
        super().__init__(None, 'Word Lookup', 'magic-wand.png', 
              parent, flags)

    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout()

        self.layout_top = QtWidgets.QHBoxLayout()
        self.l_word = QtWidgets.QLabel('Suggestions for:')
        self.le_word = QtWidgets.QLineEdit('')
        self.le_word.setToolTip(f"Use '{BLANK}' as blank symbol")
        self.le_word.textEdited.connect(self.on_word_edited)
        self.layout_top.addWidget(self.l_word)
        self.layout_top.addWidget(self.le_word)
        self.layout_center = QtWidgets.QHBoxLayout()
        self.lw_words = QtWidgets.QListWidget()
        self.lw_words.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.lw_words.itemDoubleClicked.connect(self.on_word_dblclick)
        self.tb_actions = QtWidgets.QToolBar()
        self.tb_actions.setOrientation(QtCore.Qt.Vertical)
        self.act_refresh = self.tb_actions.addAction(QtGui.QIcon(f"{ICONFOLDER}/repeat.png"), 'Refresh')
        self.act_refresh.triggered.connect(self.on_act_refresh)
        self.act_sort = self.tb_actions.addAction(QtGui.QIcon(f"{ICONFOLDER}/sort.png"), 'Sort')
        self.act_sort.triggered.connect(self.on_act_sort)
        self.act_shuffle = self.tb_actions.addAction(QtGui.QIcon(f"{ICONFOLDER}/shuffle.png"), 'Shuffle')
        self.act_shuffle.triggered.connect(self.on_act_shuffle)
        self.act_source_config = self.tb_actions.addAction(QtGui.QIcon(f"{ICONFOLDER}/database-3.png"), 'Sources...')
        self.act_source_config.triggered.connect(self.on_act_source_config)
        self.layout_center.addWidget(self.lw_words)
        self.layout_center.addWidget(self.tb_actions)
        self.l_count = QtWidgets.QLabel('')
        self.ch_truncate = QtWidgets.QCheckBox('Truncate')
        self.ch_truncate.setToolTip('Uncheck to retrieve all results with no truncation')
        self.ch_truncate.setChecked(True)
        self.ch_truncate.toggled.connect(self.on_ch_truncate)
        self.layout_lower = QtWidgets.QHBoxLayout()
        self.layout_lower.addWidget(self.l_count)
        self.layout_lower.addWidget(self.ch_truncate)

        self.layout_controls.addLayout(self.layout_top)
        self.layout_controls.addLayout(self.layout_center)
        self.layout_controls.addLayout(self.layout_lower)
        self.init(self.word, self.word_editable)

    def showEvent(self, event):     
        self.selected = ''
        self.old_truncate = self.mainwindow.cw.wordsource.max_fetch
        super().showEvent(event) 

    def closeEvent(self, event):
        self.mainwindow.cw.wordsource.max_fetch = self.old_truncate
        super().closeEvent(event)

    def init(self, word='', word_editable=False):
        self.selected = ''
        self.word = word
        self.word_editable = word_editable
        self.le_word.setText(self.word)
        self.le_word.setEnabled(self.word_editable)
        self.fill_words()

    def validate(self): 
        self.selected = ''
        if self.lw_words.currentItem() is None:
            MsgBox('No word selected!', self, 'Error', 'error')
            return False
        self.selected = self.lw_words.currentItem().text()
        return True

    def fill_words(self):
        self.lw_words.clear()
        cnt = 0
        if self.getresults:
            self.results = self.getresults(self.word)
            if self.results:
                cnt = len(self.results)
                self.lw_words.addItems(self.results)
                self.sort_words()
        self.l_count.setText(f"{cnt} result{'s' if cnt and cnt > 1 else ''}")
        self.update_actions()

    def update_actions(self):
        b_words = bool(self.results)
        self.act_sort.setEnabled(b_words)
        self.act_shuffle.setEnabled(b_words)
        self.act_source_config.setEnabled(not self.mainwindow is None)

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

    @QtCore.pyqtSlot(bool) 
    def on_ch_truncate(self, checked):
        self.mainwindow.cw.wordsource.max_fetch = CWSettings.settings['wordsrc']['maxres'] if checked else None
        self.fill_words()

    @QtCore.pyqtSlot(str) 
    def on_word_edited(self, text):
        self.word = text  
        #self.fill_words()  

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)         
    def on_word_dblclick(self, item):
        self.on_btn_OK_clicked()

    @QtCore.pyqtSlot(bool)        
    def on_act_refresh(self, checked):
        self.fill_words()

    @QtCore.pyqtSlot(bool)        
    def on_act_sort(self, checked):
        self.sort_words('toggle')

    @QtCore.pyqtSlot(bool)        
    def on_act_shuffle(self, checked):
        if not self.results: return
        np.random.seed()
        np.random.shuffle(self.results)
        self.lw_words.clear()
        self.lw_words.addItems(self.results)

    @QtCore.pyqtSlot(bool)        
    def on_act_source_config(self, checked):
        self.mainwindow.on_act_wsrc(False)


##############################################################################
######          PrintPreviewDialog
##############################################################################  
        
class PrintPreviewDialog(BasicDialog):
    
    def __init__(self, printer, mainwindow, parent=None, flags=QtCore.Qt.WindowFlags()):
        if not printer.isValid():
            raise Exception('No valid printer!')
        if getattr(mainwindow, 'cw', None) is None:
            raise Exception('Crossword not available!')
        self.printer = printer
        self.mainwindow = mainwindow
        super().__init__(None, f"Printing to: {self.printer.printerName()}", 'binoculars.png', 
              parent, flags)

    def showEvent(self, event):      
        event.accept()
        self.ppreview.updatePreview()

    def _make_labelled_widgets(self, name, label, widgets):
        layout = QtWidgets.QVBoxLayout()
        self.__dict__[f"l_{name}"] = QtWidgets.QLabel(label)
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
        self.layout_pagesize = self._make_labelled_widgets('pagesize', 'Page Size', [self.combo_page_size])
        self.layout_tb_main.addLayout(self.layout_pagesize)

        self.combo_view = QtWidgets.QComboBox()
        self.combo_view.addItems(['Single', 'Two', 'All'])
        self.combo_view.setEditable(False)
        self.combo_view.setCurrentIndex(0)
        self.combo_view.activated.connect(self.on_combo_view)
        self.layout_view = self._make_labelled_widgets('view', 'View', [self.combo_view])
        self.layout_tb_main.addLayout(self.layout_view)

        self.combo_layout = QtWidgets.QComboBox()
        self.combo_layout.addItems(['Auto', 'Portrait', 'Landscape'])
        self.combo_layout.setEditable(False)
        self.combo_layout.setCurrentIndex(0)
        self.combo_layout.activated.connect(self.on_combo_layout)
        self.layout_layout = self._make_labelled_widgets('layout', 'Layout', [self.combo_layout])
        self.layout_tb_main.addLayout(self.layout_layout)

        self.btn_fit_width = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/width.png"), 'Zoom to width', None)
        self.btn_fit_width.setToolTip('Zoom to window width')
        self.btn_fit_width.clicked.connect(self.on_btn_fit_width)
        self.btn_fit_all = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/fitsize.png"), 'Fit in window', None)
        self.btn_fit_all.setToolTip('Zoom to window size')
        self.btn_fit_all.clicked.connect(self.on_btn_fit_all)
        self.slider_zoom = QtWidgets.QSlider()
        self.slider_zoom.setOrientation(QtCore.Qt.Horizontal)
        self.slider_zoom.setRange(10, 500)
        self.slider_zoom.setSingleStep(1)
        self.slider_zoom.setPageStep(10)
        self.slider_zoom.setToolTip('Zoom %')
        self.slider_zoom.valueChanged.connect(self.on_zoom_changed)
        self.layout_fit = self._make_labelled_widgets('fit', 'Fit & Zoom', [self.btn_fit_width, self.btn_fit_all, self.slider_zoom])
        self.layout_tb_main.addLayout(self.layout_fit)

        self.combo_color = QtWidgets.QComboBox()
        self.combo_color.addItems(['Greyscale', 'Color'])
        self.combo_color.setEditable(False)
        self.combo_color.setCurrentIndex(1)
        self.combo_color.activated.connect(self.on_combo_color)
        self.layout_color = self._make_labelled_widgets('color', 'Color Print', [self.combo_color])
        self.layout_tb_main.addLayout(self.layout_color)

        self.le_margin_l = QtWidgets.QLineEdit('0')
        self.le_margin_l.setMaximumWidth(20)
        self.le_margin_l.setToolTip('Left, mm')
        self.le_margin_l.textChanged.connect(self.on_margins_changed)
        self.le_margin_r = QtWidgets.QLineEdit('0')
        self.le_margin_r.setMaximumWidth(20)
        self.le_margin_r.setToolTip('Right, mm')
        self.le_margin_r.textChanged.connect(self.on_margins_changed)
        self.le_margin_t = QtWidgets.QLineEdit('0')
        self.le_margin_t.setMaximumWidth(20)
        self.le_margin_t.setToolTip('Top, mm')
        self.le_margin_t.textChanged.connect(self.on_margins_changed)
        self.le_margin_b = QtWidgets.QLineEdit('0')
        self.le_margin_b.setMaximumWidth(20)
        self.le_margin_b.setToolTip('Bottom, mm')
        self.le_margin_b.textChanged.connect(self.on_margins_changed)
        self.layout_margins = self._make_labelled_widgets('margins', 'Margins', [self.le_margin_l, self.le_margin_r, self.le_margin_t, self.le_margin_b])
        self.layout_tb_main.addLayout(self.layout_margins)

        self.layout_tb_main.addSpacing(20) 

        self.btn_settings = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/settings-5.png"), 'Settings', None)
        self.btn_settings.setToolTip('Configure additional printing settings')
        self.btn_settings.clicked.connect(self.on_btn_settings)
        self.layout_tb_main.addWidget(self.btn_settings)

        self.layout_controls.addLayout(self.layout_tb_main)
        
        # central preview widget
        self.layout_center = QtWidgets.QHBoxLayout()
        self.ppreview = QtPrintSupport.QPrintPreviewWidget(self.printer)        
        self.layout_center.addWidget(self.ppreview)
        self.layout_controls.addLayout(self.layout_center)

        self.update_controls()

    def update_controls(self):
        """
        Updates the printer settings from CWSettings and 
        updates the controls in toolbar and preview according to current
        printer settings.
        """
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

    def write_settings(self):
        """
        Saves current settings to CWSettings.
        """
        settings = CWSettings.settings['printing']

        margins = self.printer.pageLayout().margins(QtGui.QPageLayout.Millimeter)
        settings['margins'][0] = int(margins.left())
        settings['margins'][1] = int(margins.right())
        settings['margins'][2] = int(margins.top())
        settings['margins'][3] = int(margins.bottom())
        settings['layout'] = self.combo_layout.currentText().lower()
        settings['color_print'] = bool(self.combo_color.currentIndex())

        CWSettings.save_to_file()

    @QtCore.pyqtSlot(int)
    def on_combo_page_size(self, index):
        if self.printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId(self.combo_page_size.itemData(index)))):
            self.ppreview.updatePreview()
        else:
            self.update_page_size()

    @QtCore.pyqtSlot(int)
    def on_combo_view(self, index):
        self.ppreview.setViewMode(QtPrintSupport.QPrintPreviewWidget.ViewMode(index))

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

    @QtCore.pyqtSlot()
    def on_btn_fit_width(self):
        self.ppreview.setZoomMode(QtPrintSupport.QPrintPreviewWidget.FitToWidth)
        self.slider_zoom.valueChanged.disconnect()
        self.slider_zoom.setValue(self.ppreview.zoomFactor() * 100.0)
        self.slider_zoom.valueChanged.connect(self.on_zoom_changed)

    @QtCore.pyqtSlot()
    def on_btn_fit_all(self):
        self.ppreview.setZoomMode(QtPrintSupport.QPrintPreviewWidget.FitInView)
        self.slider_zoom.valueChanged.disconnect()
        self.slider_zoom.setValue(self.ppreview.zoomFactor() * 100.0)
        self.slider_zoom.valueChanged.connect(self.on_zoom_changed)

    @QtCore.pyqtSlot(int)
    def on_combo_color(self, index):
        self.printer.setColorMode(QtPrintSupport.QPrinter.ColorMode(index))
        self.ppreview.updatePreview()

    @QtCore.pyqtSlot(int)
    def on_zoom_changed(self, value):
        if not self.slider_zoom.hasFocus(): return
        self.ppreview.setZoomMode(QtPrintSupport.QPrintPreviewWidget.CustomZoom)
        self.ppreview.setZoomFactor(value / 100.0)

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

    @QtCore.pyqtSlot()
    def on_btn_settings(self):
        if not hasattr(self.mainwindow, 'dia_settings'):
            self.mainwindow.dia_settings = SettingsDialog(self.mainwindow)
        self.mainwindow.dia_settings.tree.setCurrentItem(self.mainwindow.dia_settings.tree.topLevelItem(6))
        if not self.mainwindow.dia_settings.exec(): return
        settings = self.mainwindow.dia_settings.to_settings()
        if json.dumps(settings, sort_keys=True) != json.dumps(CWSettings.settings, sort_keys=True):
            CWSettings.settings = settings
            self.update_controls()
            self.ppreview.paintRequested.emit(self.printer)            

##############################################################################
######          CwInfoDialog
##############################################################################  
        
class CwInfoDialog(BasicDialog):
    
    def __init__(self, mainwindow, parent=None, flags=QtCore.Qt.WindowFlags()):
        self.mainwindow = mainwindow
        super().__init__(None, 'Crossword Info', 'info1.png', 
              parent, flags)
                
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QFormLayout()  

        self.le_title = QtWidgets.QLineEdit('')
        self.le_author = QtWidgets.QLineEdit('')
        self.le_editor = QtWidgets.QLineEdit('')
        self.le_publisher = QtWidgets.QLineEdit('')
        self.le_copyright = QtWidgets.QLineEdit('')
        self.de_date = QtWidgets.QDateEdit()
        self.de_date.setCalendarPopup(True)

        self.layout_controls.addRow('Title:', self.le_title)
        self.layout_controls.addRow('Author:', self.le_author)
        self.layout_controls.addRow('Editor:', self.le_editor)
        self.layout_controls.addRow('Publisher:', self.le_publisher)
        self.layout_controls.addRow('Copyright:', self.le_copyright)
        self.layout_controls.addRow('Date:', self.de_date)

        self.init()

    def init(self):
        """
        Initializes control values from mainwindow.cw.
        """
        cw_info = self.mainwindow.cw.words.info if self.mainwindow.cw else CWInfo()
        self.le_title.setText(cw_info.title)
        self.le_author.setText(cw_info.author)
        self.le_editor.setText(cw_info.editor)
        self.le_publisher.setText(cw_info.publisher)
        self.le_copyright.setText(cw_info.cpyright)
        date_ = QtCore.QDate.fromString(cw_info.date, 'yyyy-MM-dd')
        self.de_date.setDate(date_ if date_.isValid() else QtCore.QDate.currentDate())

    def to_info(self):
        return CWInfo(self.le_title.text(), self.le_author.text(), self.le_editor.text(),
                      self.le_publisher.text(), self.le_copyright.text(), 
                      self.de_date.date().toString('yyyy-MM-dd') if self.de_date.date().isValid() else '')


##############################################################################
######          DefLookupDialog
############################################################################## 
      
class DefLookupDialog(BasicDialog):
    
    def __init__(self, word='', word_editable=False, lang='', 
                 parent=None, flags=QtCore.Qt.WindowFlags()):
        """
        Params:
        - word [str]: the word string to look up (def='')
        - word_editable [bool]: whether the word string can be edited in the dialog (def=False)
        - lang [str]: the short name of the langugage used to look up the word (def='').
            Can be one of: 'en' (English), 'ru' (Russian), 'fr' (French), 'es' (Spanish), 'de' (German), 'it' (Italian)
            (see LANG global). If the value is an empty string (default), the setting from
            CWSettings.settings['lookup']['default_lang']
        """      
        self.word = word.lower() or ''
        self.word_editable = word_editable
        self.word_def = None
        self.google_res = None
        self.dict_engine = None
        self.google_engine = None
        self.setlang(lang)

        super().__init__(None, 'Word Lookup', 'worldwide.png', 
              parent, flags)
        
        self.load_threads = {'dics': QThreadStump(on_start=self.on_dics_load_start, on_finish=self.on_dics_load_finish, on_run=self.on_dics_load_run, on_error=self.on_thread_error),
                             'google': QThreadStump(on_start=self.on_google_load_start, on_finish=self.on_google_load_finish, on_run=self.on_google_load_run, on_error=self.on_thread_error)}

    def closeEvent(self, event):
        """
        Need to stop running background threads.
        """      
        # close running threads
        self.kill_threads()  
        # close
        event.accept()      

    def showEvent(self, event):      
        self.update_content()
        event.accept()

    def kill_threads(self, dics=True, google=True):
        for thread in self.load_threads:
            if self.load_threads[thread].isRunning() and \
                    (dics and thread == 'dics') or \
                    (google and thread == 'google'):
                self.load_threads[thread].terminate()
                self.load_threads[thread].wait()

    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout() 

        self.gb_word = QtWidgets.QGroupBox('Lookup word')
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

        self.gb_sources = QtWidgets.QGroupBox('Lookup in')
        self.layout_gb_sources = QtWidgets.QHBoxLayout()
        self.rb_dict = QtWidgets.QRadioButton('Dictionary')
        self.rb_dict.setChecked(True)
        self.rb_dict.toggled.connect(self.rb_source_toggled)
        self.rb_google = QtWidgets.QRadioButton('Google')
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

    def setlang(self, lang=''):
        lang = lang or CWSettings.settings['lookup']['default_lang']
        if not lang: lang = 'en'
        self.lang = lang

    def init(self):
        # languages combo
        index = self.combo_lang.findText(self.lang)
        if index < 0:
            raise Exception(f"Language '{self.lang}' not available!")
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
        
    def update_language(self):
        self.lang = self.combo_lang.currentText()

    def update_dict_engine(self):
        self.update_language()
        timeout = CWSettings.settings['lookup']['timeout'] * 1000
        if self.lang == 'en':
            self.dict_engine = MWDict(CWSettings.settings, timeout)
        else:
            self.dict_engine = YandexDict(CWSettings.settings, f"{self.lang}-{self.lang}", timeout)

    def update_google_engine(self):
        settings = CWSettings.settings['lookup']['google']
        timeout = CWSettings.settings['lookup']['timeout'] * 1000
        #settings['lang'] = self.lang
        self.google_engine = GoogleSearch(CWSettings.settings, self.word, exact_match=settings['exact_match'],
            file_types=settings['file_types'], lang=settings['lang'], country=settings['country'],
            interface_lang=settings['interface_lang'], link_site=settings['link_site'],
            related_site=settings['related_site'], in_site=settings['in_site'],
            nresults=settings['nresults'], safe_search=settings['safe_search'], timeout=timeout) 

    def add_pages(self):
        # 1. Dictionary
        self.page_dict = QtWidgets.QWidget()
        self.layout_dict = QtWidgets.QVBoxLayout()
        self.combo_dict_homs = QtWidgets.QComboBox()
        self.combo_dict_homs.setEditable(False)
        self.combo_dict_homs.currentIndexChanged.connect(self.on_combo_dict_homs)
        self.layout_dict_top = QtWidgets.QFormLayout()
        self.layout_dict_top.addRow('Choose entry / meaning:', self.combo_dict_homs)
        self.layout_dict.addLayout(self.layout_dict_top)    
        self.te_dict_defs = QtWidgets.QPlainTextEdit('')
        self.te_dict_defs.setStyleSheet('font-family: Arial; font-size: 10pt; font-weight: normal; background-color: white; color: black')
        self.te_dict_defs.setReadOnly(True)
        self.te_dict_defs.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        self.layout_dict.addWidget(self.te_dict_defs)  
        self.l_link_dict = QtWidgets.QLabel('Link')
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
        self.layout_google_top.addRow('Choose link page:', self.combo_google)
        self.layout_google.addLayout(self.layout_google_top)    
        self.te_google_res = QtWidgets.QPlainTextEdit('')
        self.te_google_res.setStyleSheet('font-family: Arial; font-size: 10pt; font-weight: normal; background-color: white; color: black')
        self.te_google_res.setReadOnly(True)
        self.te_google_res.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        self.layout_google.addWidget(self.te_google_res)
        self.l_link_google = QtWidgets.QLabel('Link')
        self.l_link_google.setTextFormat(QtCore.Qt.RichText)
        self.l_link_google.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.l_link_google.setOpenExternalLinks(True)
        self.l_link_google.setEnabled(False)
        self.layout_google.addWidget(self.l_link_google)
        self.page_google.setLayout(self.layout_google)
        self.stacked.addWidget(self.page_google)

    @QtCore.pyqtSlot(QtCore.QThread, str)
    def on_thread_error(self, thread, err):
        MsgBox(f"Load failed with error:{NEWLINE}{err}", self, 'Error', 'error')

        if thread == self.load_threads['dics']:
            thread.lock()
            self.word_def = None
            thread.unlock()

        elif thread == self.load_threads['google']:
            thread.lock()
            self.google_res = None
            thread.unlock()

    def on_dics_load_start(self):
        #print(f"Started DICT thread for '{self.word}'...")
        self.word_def = None
        self.page_dict.setEnabled(False)
        self.l_link_dict.setEnabled(False)
        self.l_link_dict.setText('Link')
        self.update_dict_engine()
        try:
            self.combo_dict_homs.currentIndexChanged.disconnect()
        except:
            pass
        self.combo_dict_homs.clear()
        self.te_dict_defs.setStyleSheet('font-family: Arial; font-size: 10pt; font-weight: bold; background-color: #ffd6e2; color: black')
        self.te_dict_defs.setPlainText('UPDATING ...')     
        
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
    
    def on_google_load_start(self):
        #print(f"Started GOOGLE thread for '{self.word}'...")
        self.google_res = None
        self.page_google.setEnabled(False)
        self.l_link_google.setEnabled(False)
        self.l_link_google.setText('Link')
        self.update_google_engine()
        try:
            self.combo_google.currentIndexChanged.disconnect()
        except:
            pass
        self.combo_google.clear()
        self.te_google_res.setStyleSheet('font-family: Arial; font-size: 10pt; font-weight: bold; background-color: #ffd6e2; color: black')
        self.te_google_res.setPlainText('UPDATING ...') 

    def on_google_load_run(self):     
        data = self.google_engine.search_lite()

        thread = self.load_threads['google']
        thread.lock()
        self.google_res = data
        thread.unlock()

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

    @QtCore.pyqtSlot(bool)        
    def rb_source_toggled(self, toggled):
        """
        Show specified source page.
        """
        if self.rb_dict.isChecked():
            self.stacked.setCurrentIndex(0)
        elif self.rb_google.isChecked():
            self.stacked.setCurrentIndex(1)

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

    @QtCore.pyqtSlot(int)
    def on_combo_lang(self, index):
        """
        When a language combo item is selected.
        """     
        # update content
        self.update_content()

    @QtCore.pyqtSlot(int)
    def on_combo_dict_homs(self, index):
        if index < 0 or not self.word_def or index >= len(self.word_def): return
        if self.word_def[index][3]:
            self.l_link_dict.setText(f'<a href="{self.word_def[index][3]}">Link</a>')
            self.l_link_dict.setToolTip(self.word_def[index][3])
            self.l_link_dict.setEnabled(True)
        else:
            self.l_link_dict.setText('Link')
            self.l_link_dict.setToolTip('')
            self.l_link_dict.setEnabled(False)
        self.te_dict_defs.setPlainText('\n'.join(self.word_def[index][2]))

    @QtCore.pyqtSlot(int)
    def on_combo_google(self, index):
        if index < 0 or not self.google_res or index >= len(self.google_res): return
        url = self.google_res[index]['url']
        if url:            
            self.l_link_google.setText(f'<a href="{url}">Link</a>')
            self.l_link_google.setToolTip(url)
            self.l_link_google.setEnabled(True)
        else:
            self.l_link_google.setText('Link')
            self.l_link_google.setToolTip('')
            self.l_link_google.setEnabled(False)
        self.te_google_res.setPlainText(self.google_res[index]['summary'])

##############################################################################
######          ReflectGridDialog
##############################################################################  
        
class ReflectGridDialog(BasicDialog):
    
    def __init__(self, parent=None, flags=QtCore.Qt.WindowFlags()):
        super().__init__(None, 'Duplicate Grid', 'windows-1.png', 
              parent, flags)
        
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QVBoxLayout()

        self.ag_dir = QtWidgets.QActionGroup(self)
        self.act_down = self.ag_dir.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-r.png"), 'Down')
        self.act_down.setCheckable(True)        
        self.act_down.toggled.connect(self.on_actdir)
        self.act_up = self.ag_dir.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-l.png"), 'Up')
        self.act_up.setCheckable(True)
        self.act_up.toggled.connect(self.on_actdir)
        self.act_right = self.ag_dir.addAction(QtGui.QIcon(f"{ICONFOLDER}/fast-forward-1.png"), 'Right')
        self.act_right.setCheckable(True)
        self.act_right.toggled.connect(self.on_actdir)
        self.act_left = self.ag_dir.addAction(QtGui.QIcon(f"{ICONFOLDER}/rewind-1.png"), 'Left')
        self.act_left.setCheckable(True)
        self.act_left.toggled.connect(self.on_actdir)
        self.tb_dir = QtWidgets.QToolBar()
        self.tb_dir.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.tb_dir.addAction(self.act_down)
        self.tb_dir.addAction(self.act_up)
        self.tb_dir.addAction(self.act_right)
        self.tb_dir.addAction(self.act_left)
        self.l_top = QtWidgets.QLabel('Duplication direction:')

        self.ag_border = QtWidgets.QActionGroup(self)
        self.act_b0 = self.ag_border.addAction(QtGui.QIcon(f"{ICONFOLDER}/error.png"), 'No border')
        self.act_b0.setCheckable(True)
        self.act_b0.setChecked(True)
        self.act_b1 = self.ag_border.addAction(QtGui.QIcon(f"{ICONFOLDER}/grid5.png"), 'Empty')
        self.act_b1.setCheckable(True)
        self.act_b2 = self.ag_border.addAction(QtGui.QIcon(f"{ICONFOLDER}/grid6.png"), 'Filled-Empty')
        self.act_b2.setCheckable(True)
        self.act_b3 = self.ag_border.addAction(QtGui.QIcon(f"{ICONFOLDER}/grid7.png"), 'Empty-Filled')
        self.act_b3.setCheckable(True)
        self.act_b4 = self.ag_border.addAction(QtGui.QIcon(f"{ICONFOLDER}/grid9.png"), 'Filled')
        self.act_b4.setCheckable(True)
        self.tb_border = QtWidgets.QToolBar()
        self.tb_border.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.tb_border.addAction(self.act_b0)
        self.tb_border.addAction(self.act_b1)
        self.tb_border.addAction(self.act_b2)
        self.tb_border.addAction(self.act_b3)
        self.tb_border.addAction(self.act_b4)
        self.l_border = QtWidgets.QLabel('Border style:')

        self.gb_options = QtWidgets.QGroupBox('Duplicate options')
        self.layout_gb_options = QtWidgets.QVBoxLayout()
        self.chb_mirror = QtWidgets.QCheckBox('Mirror')
        self.chb_mirror.setToolTip('Mirror duplicate grids along duplication axis')
        self.chb_mirror.setChecked(True)
        self.chb_reverse = QtWidgets.QCheckBox('Reverse')
        self.chb_reverse.setToolTip('Reverse the sequence of duplicate grids')
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

    @QtCore.pyqtSlot(bool)
    def on_actdir(self, checked):
        self.update_dir_icons()

##############################################################################
######          AboutDialog
##############################################################################

class AboutDialog(QtWidgets.QDialog):
    
    def __init__(self, parent=None, flags=QtCore.Qt.WindowFlags()):
        super().__init__(parent, flags)
        self.initUI(None, 'About', 'main.png')
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        
    def addMainLayout(self):
        self.layout_controls = QtWidgets.QFormLayout()

        self.l_appname = QtWidgets.QLabel(APP_NAME)
        self.l_appname.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard)
        self.l_appversion = QtWidgets.QLabel(APP_VERSION)
        self.l_appversion.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard)
        self.l_author = QtWidgets.QLabel(APP_AUTHOR)
        self.l_author.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard)
        self.l_email = QtWidgets.QLabel(f'<a href="mailto:{APP_EMAIL}">{APP_EMAIL}</a>')
        self.l_email.setToolTip(f"Send mail to {APP_EMAIL}")
        self.l_email.setTextFormat(QtCore.Qt.RichText)
        self.l_email.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.l_email.setOpenExternalLinks(True)
        self.l_github = QtWidgets.QLabel(f'<a href="{GIT_REPO}">{GIT_REPO}</a>')
        self.l_github.setToolTip(f"Visit {GIT_REPO}")
        self.l_github.setTextFormat(QtCore.Qt.RichText)
        self.l_github.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.l_github.setOpenExternalLinks(True)

        self.layout_controls.addRow('App name:', self.l_appname)
        self.layout_controls.addRow('Version:', self.l_appversion)
        self.layout_controls.addRow('Author:', self.l_author)
        self.layout_controls.addRow('Email:', self.l_email)
        self.layout_controls.addRow('Website:', self.l_github)
        
    def initUI(self, geometry=None, title=None, icon=None):
        
        self.addMainLayout()
        
        self.btn_OK = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/like.png"), 'OK', None)
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
