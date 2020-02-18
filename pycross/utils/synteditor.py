# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.synteditor
from .utils import make_font
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5 import Qsci

## @brief Scintilla-based Python editor
# Adapted from [this example](https://eli.thegreenplace.net/2011/04/01/sample-using-qscintilla-with-pyqt)
# and [this addition](https://stackoverflow.com/questions/40002373/qscintilla-based-text-editor-in-pyqt5-with-clickable-functions-and-variables)
class SynEditor(Qsci.QsciScintilla):
    
    ARROW_MARKER_NUM = 8
    #marginClicked = QtCore.pyqtSignal(int, int, QtCore.Qt.KeyboardModifiers)

    def __init__(self, parent=None, lexer=Qsci.QsciLexerPython(), minsize=(600, 400)):
        super(Qsci.QsciScintilla, self).__init__(parent)

        # Set the default font
        font = make_font('Courier', 10)
        font.setFixedPitch(True)
        self.setFont(font)
        self.setMarginsFont(font)

        # Margin 0 is used for line numbers
        fontmetrics = QtGui.QFontMetrics(font)
        self.setMarginsFont(font)
        self.setMarginWidth(0, fontmetrics.width('00000') + 6)
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(QtGui.QColor('#cccccc'))

        # Clickable margin 1 for showing markers
        self.setMarginSensitivity(1, True)
        self.marginClicked.connect(self.on_margin_clicked)
        self.markerDefine(Qsci.QsciScintilla.RightArrow, SynEditor.ARROW_MARKER_NUM)
        self.setMarkerBackgroundColor(QtGui.QColor("#ee1111"), SynEditor.ARROW_MARKER_NUM)

        # Brace matching: enable for a brace immediately before or after
        # the current position
        self.setBraceMatching(Qsci.QsciScintilla.SloppyBraceMatch)

        # Current line visible with special background color
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QtGui.QColor("#ffe4e4"))

        # Set Python lexer
        # Set style for Python comments (style number 1) to a fixed-width font.
        self.lexer = lexer
        self.lexer.setDefaultFont(font)
        self.setLexer(self.lexer)

        self.SendScintilla(Qsci.QsciScintilla.SCI_STYLESETFONT, 1, bytearray(str.encode(font.family())))

        # Don't want to see the horizontal scrollbar at all
        # Use raw message to Scintilla here.
        # All messages are documented [here](http://www.scintilla.org/ScintillaDoc.html)
        self.SendScintilla(Qsci.QsciScintilla.SCI_SETHSCROLLBAR, 0)

        # set minimum widget size
        if minsize: self.setMinimumSize(*minsize)

    # Toggle marker for the line the margin was clicked on
    @QtCore.pyqtSlot(int, int, QtCore.Qt.KeyboardModifiers)
    def on_margin_clicked(self, nmargin, nline, modifiers):
        if self.markersAtLine(nline) != 0:
            self.markerDelete(nline, SynEditor.ARROW_MARKER_NUM)
        else:
            self.markerAdd(nline, SynEditor.ARROW_MARKER_NUM)

class SynEditorWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = SynEditor(self) 