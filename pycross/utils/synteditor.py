# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.synteditor
from .globalvars import ICONFOLDER
from .utils import make_font, re
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5 import Qsci

# ******************************************************************************** #
# *****          SynEditor
# ******************************************************************************** # 

## @brief Scintilla-based Python editor
# Adapted from [this example](https://eli.thegreenplace.net/2011/04/01/sample-using-qscintilla-with-pyqt)
# and [this addition](https://stackoverflow.com/questions/40002373/qscintilla-based-text-editor-in-pyqt5-with-clickable-functions-and-variables)
# @see [QScintilla docs](https://qscintilla.com/), [API reference](https://www.riverbankcomputing.com/static/Docs/QScintilla/classQsciScintilla.html)
class SynEditor(Qsci.QsciScintilla):
    
    ARROW_MARKER_NUM = 8

    def __init__(self, parent=None, lexer=Qsci.QsciLexerPython(), source=None):
        super(Qsci.QsciScintilla, self).__init__(parent)

        # Set the default font
        font = make_font('Courier', 10)
        font.setFixedPitch(True)
        self.setFont(font)

        # Indentation
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setAutoIndent(True)

        # Margins
        self.setMarginsFont(font)
        self.setMarginsBackgroundColor(QtGui.QColor('#5d5d5d'))
        self.setMarginsForegroundColor(QtGui.QColor(QtCore.Qt.yellow))

        # Margin 0 is used for line numbers
        self.setMarginType(0, Qsci.QsciScintilla.NumberMargin)        
        self.setMarginWidth(0, '00000')
        self.setMarginLineNumbers(0, True)        

        # Clickable margin 1 for showing markers
        self.setMarginType(1, Qsci.QsciScintilla.SymbolMargin)
        self.setMarginWidth(1, 20)
        self.setMarginSensitivity(1, True)
        self.marginClicked.connect(self.on_margin_clicked)
        self.markerDefine(Qsci.QsciScintilla.RightArrow, SynEditor.ARROW_MARKER_NUM)
        self.setMarkerBackgroundColor(QtGui.QColor(QtCore.Qt.magenta), SynEditor.ARROW_MARKER_NUM)
        
        # Brace matching: enable for a brace immediately before or after
        # the current position
        self.setBraceMatching(Qsci.QsciScintilla.SloppyBraceMatch)

        # Current line visible with special background color
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QtGui.QColor("#f2f2f2"))

        # Set Python lexer
        # Set style for Python comments (style number 1) to a fixed-width font.
        self.lexer = lexer
        self.lexer.setDefaultFont(font)
        self.setLexer(self.lexer)
        # set font
        self.SendScintilla(Qsci.QsciScintilla.SCI_STYLESETFONT, 1, bytearray(str.encode(font.family())))
        # tab guides
        self.setIndentationGuides(True)

        # set source
        if source: self.setText(source)

    # Toggle marker for the line the margin was clicked on
    @QtCore.pyqtSlot(int, int, QtCore.Qt.KeyboardModifiers)
    def on_margin_clicked(self, nmargin, nline, modifiers):
        if self.markersAtLine(nline) != 0:
            self.markerDelete(nline, SynEditor.ARROW_MARKER_NUM)
        else:
            self.markerAdd(nline, SynEditor.ARROW_MARKER_NUM)

# ******************************************************************************** #
# *****          SynEditorWidget
# ******************************************************************************** #            

class SynEditorWidget(QtWidgets.QDialog):

    def __init__(self, lexer=Qsci.QsciLexerPython(), source=None, minsize=(600, 400),
                 icon='file.png', title=':: Code Editor ::'):
        super().__init__()
        self.layout_main = QtWidgets.QVBoxLayout()
        self.add_elements(lexer, source)     
        self.setLayout(self.layout_main)
        # set minimum widget size
        if minsize: self.setMinimumSize(*minsize)
        self.setWindowIcon(QtGui.QIcon(f"{ICONFOLDER}/{icon}"))
        self.setWindowTitle(title)

    def add_elements(self, lexer, source):
        self.add_central(lexer, source)
        self.add_bottom()

    def add_central(self, lexer, source):
        self.editor = SynEditor(self, lexer, source)
        self.layout_main.addWidget(self.editor)

    def add_bottom(self):
        self.layout_bottom = QtWidgets.QHBoxLayout()
        self.layout_bottom.setSpacing(10)
        self.btn_OK = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/like.png"), _('OK'), None)
        self.btn_OK.setMaximumWidth(150)
        self.btn_OK.setDefault(True)
        self.btn_OK.clicked.connect(self.accept)
        self.btn_cancel = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/multiply-1.png"), _('Cancel'), None)
        self.btn_cancel.setMaximumWidth(150)
        self.btn_cancel.clicked.connect(self.reject)
        self.layout_bottom.addWidget(self.btn_OK)
        self.layout_bottom.addWidget(self.btn_cancel)
        self.layout_main.addLayout(self.layout_bottom)

    def currenttext(self):
        return self.editor.text()

# ******************************************************************************** #
# *****          PluginSynEditorWidget
# ******************************************************************************** #            

class PluginSynEditorWidget(SynEditorWidget):

    RESRCH = re.compile(r'^[ ]{4}[\w"#@]', re.M | re.I)

    def __init__(self, methods, lexer=Qsci.QsciLexerPython(), source=None, minsize=(600, 400),
                 icon='file.png', title=':: Code Editor ::'):
        self.methods = methods
        super().__init__(lexer, source, minsize, icon, title)
        #self._update_checked_methods()

    def showEvent(self, event):
        self._update_checked_methods()
        event.accept()

    def add_central(self, lexer, source):
        self.editor = SynEditor(self, lexer, source)

        self.splitter1 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.lw_methods = QtWidgets.QListWidget()
        self.lw_methods.setSortingEnabled(True)
        self.lw_methods.setSelectionMode(1)
        self.lw_methods.currentItemChanged.connect(self.on_lw_methods_select)
        self.lw_methods.itemChanged.connect(self.on_lw_methods_changed)
        self.lw_methods.itemDoubleClicked.connect(self.on_lw_methods_dblclicked)
        self.reset_methods()

        self.splitter1.addWidget(self.lw_methods)
        self.splitter1.addWidget(self.editor)
        self.layout_main.addWidget(self.splitter1)

    def _config_editor(self):
        self.editor.textChanged.connect(self.on_editor_text_changed)

    def reset_methods(self):
        self.lw_methods.blockSignals(True)
        self.lw_methods.clear()
        for meth in self.methods:
            mlines = meth.split('\n')
            lwitem = QtWidgets.QListWidgetItem(mlines[0][4:-1])
            lwitem.setToolTip('\n'.join([l.strip()[2:] for l in mlines[1:-1]]) if len(mlines) > 2 else '')
            lwitem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            lwitem.setData(QtCore.Qt.UserRole, meth)
            lwitem.setCheckState(QtCore.Qt.Unchecked)
            self.lw_methods.addItem(lwitem)
        self.lw_methods.blockSignals(False)

    def _update_checked_methods(self):
        txt = self.editor.text()
        try:
            self.lw_methods.itemChanged.disconnect()
        except:
            pass
        for i in range(self.lw_methods.count()):
            item = self.lw_methods.item(i)
            item.setCheckState(QtCore.Qt.Checked if f"    def {item.text()}:" in txt else QtCore.Qt.Unchecked)
        self.lw_methods.itemChanged.connect(self.on_lw_methods_changed)

    @QtCore.pyqtSlot()
    def on_editor_text_changed(self):
        self._update_checked_methods()

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem, QtWidgets.QListWidgetItem)
    def on_lw_methods_select(self, current, previous):
        self.editor.cancelFind()
        self.editor.setSelection(0, 0, 0, 0)
        self.editor.findFirst(f"    def {current.text()}:", False, True, False, False, index=0)

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def on_lw_methods_changed(self, item):
        txt = self.editor.text()
        func = item.text().replace('(', r'\(').replace(')', r'\)').replace(',', r'\,')
        pattern = f'(^[ ]{{4}}[#"].*)*(^[ ]{{4}}@.+?)*(^[ ]{{4}}def {func}\\:)'
        res1 = re.search(pattern, txt, re.M | re.S)
        if res1 is None and item.checkState():
            # func not found, add it
            txt += '\n\n    @replace #@before @after\n' + '\n'.join([('    ' + l) for l in item.data(QtCore.Qt.UserRole).split('\n')])
            self.editor.setText(txt)
            self._update_checked_methods()
            self.lw_methods.setCurrentItem(item, QtCore.QItemSelectionModel.Current)
        elif (not res1 is None) and (not bool(item.checkState())):
            # func found, delete it
            res2 = PluginSynEditorWidget.RESRCH.search(txt, res1.end(res1.lastindex))
            if not res2 is None:
                txt = txt[:res1.start()] + txt[res2.start():]
            else:
                txt = txt[:res1.start()]
            self.editor.setText(txt)
            self._update_checked_methods()

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def on_lw_methods_dblclicked(self, item):
        checked = bool(item.checkState())
        item.setCheckState(QtCore.Qt.Unchecked if checked else QtCore.Qt.Checked)