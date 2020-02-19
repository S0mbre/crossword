# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
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
class SynEditor(Qsci.QsciScintilla):
    
    ARROW_MARKER_NUM = 8

    def __init__(self, parent=None, lexer=Qsci.QsciLexerPython(), source=None):
        super(Qsci.QsciScintilla, self).__init__(parent)

        # Set the default font
        font = make_font('Courier', 10)
        font.setFixedPitch(True)
        self.setFont(font)

        # Indentation
        self.setIndentationsUseTabs(True)
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

class SynEditorWidget(QtWidgets.QMainWindow):

    def __init__(self, lexer=Qsci.QsciLexerPython(), source=None, minsize=(600, 400),
        icon='file.png', title=':: Code Editor ::'):
        super().__init__()
        self.wmain = QtWidgets.QFrame(self)
        self.wmain.setStyleSheet("QWidget { background-color: #ffeaeaea }")
        self.wmain.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.layout_main = QtWidgets.QVBoxLayout()
        self.editor = SynEditor(self, lexer, source)
        self.layout_main.addWidget(self.editor)
        self.wmain.setLayout(self.layout_main)
        self.setCentralWidget(self.wmain)
        # set minimum widget size
        if minsize: self.setMinimumSize(*minsize)
        self.setWindowIcon(QtGui.QIcon(f"{ICONFOLDER}/{icon}"))
        self.setWindowTitle(title)
        #self.show()
