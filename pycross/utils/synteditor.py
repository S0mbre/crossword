# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.synteditor
from .globalvars import ICONFOLDER
from .utils import make_font
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5 import Qsci

# ******************************************************************************** #
# *****          SynEditor
# ******************************************************************************** # 

## @brief Scintilla-based Python editor
# Adapted from [this example](https://eli.thegreenplace.net/2011/04/01/sample-using-qscintilla-with-pyqt)
# and [this addition](https://stackoverflow.com/questions/40002373/qscintilla-based-text-editor-in-pyqt5-with-clickable-functions-and-variables)
# @see [QScintilla docs](https://qscintilla.com/)
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

    def add_central(self, lexer, source):
        self.editor = SynEditor(self, lexer, source)
        self.layout_main.addWidget(self.editor)