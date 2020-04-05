# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.ipythoneditor
# IPython-based code editor adapted from the [official example](https://github.com/jupyter/qtconsole/blob/master/examples/embed_qtconsole.py).
from .globalvars import *
from .utils import re
from PyQt5 import QtGui, QtCore, QtWidgets
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager

# ******************************************************************************** #
# *****          SynEditorWidget
# ******************************************************************************** #            

class SynEditorWidget(QtWidgets.QDialog):

    def __init__(self, source=None, 
        minsize=(600, 400), icon='file.png', title=_(':: Code Editor ::')):
        super().__init__()
        self.layout_main = QtWidgets.QVBoxLayout()
        self.add_elements(source)     
        self.setLayout(self.layout_main)
        # set minimum widget size
        if minsize: self.setMinimumSize(*minsize)
        self.setWindowIcon(QtGui.QIcon(f"{ICONFOLDER}/{icon}"))
        self.setWindowTitle(title)

    def __del__(self):
        self.shutdown_kernel()

    def showEvent(self, event):
        self.restart_kernel()
        event.accept()

    def hideEvent(self, event):
        self.shutdown_kernel()
        event.accept()

    def make_jupyter_widget_with_kernel(self):
        """
        Start a kernel, connect to it, and create a RichJupyterWidget to use it.
        """
        self.editor = RichJupyterWidget()
        self.restart_kernel()

    def add_elements(self, source):
        self.add_central(source)
        self.add_bottom()

    def add_central(self, source):
        self.make_jupyter_widget_with_kernel()
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
        return 'self.editor.text()'

    @QtCore.pyqtSlot()
    def shutdown_kernel(self):
        print('Shutting down IPython kernel... ', end='')
        try:
            if self.editor.kernel_client:
                self.editor.kernel_client.stop_channels()
            if self.editor.kernel_manager:
                self.editor.kernel_manager.shutdown_kernel()
        except Exception as err:
            print('\n' + err)
        else:
            print('OK')

    @QtCore.pyqtSlot()
    def restart_kernel(self):
        self.shutdown_kernel()
        kernel_manager = QtKernelManager(kernel_name='python3')
        kernel_manager.start_kernel()
        kernel_client = kernel_manager.client()
        kernel_client.start_channels()
        self.editor.kernel_manager = kernel_manager
        self.editor.kernel_client = kernel_client

# ******************************************************************************** #
# *****          PluginSynEditorWidget
# ******************************************************************************** #            

class PluginSynEditorWidget(SynEditorWidget):

    RESRCH = re.compile(r'^[ ]{4}[\w"#@]', re.M | re.I)

    def __init__(self, methods, source=None, 
                 minsize=(800, 500), icon='file.png', title=_(':: Code Editor ::')):
        self.methods = methods
        super().__init__(source, minsize, icon, title)
        self._config_editor()

    def showEvent(self, event):
        super().showEvent(event)
        self.actn_filter_regex.setChecked(False)
        self.le_filter.clear()
        self._update_checked_methods()

    def add_central(self, source):
        self.make_jupyter_widget_with_kernel()

        self.splitter1 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter1.setChildrenCollapsible(False)
        self.lo_methods = QtWidgets.QVBoxLayout()
        self.lw_methods = QtWidgets.QListWidget()
        self.lw_methods.setSortingEnabled(True)
        self.lw_methods.setSelectionMode(1)
        self.lw_methods.currentItemChanged.connect(self.on_lw_methods_select)
        self.lw_methods.itemChanged.connect(self.on_lw_methods_changed)
        self.lw_methods.itemDoubleClicked.connect(self.on_lw_methods_dblclicked)
        self.reset_methods()

        self.actn_clear_filter = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/error.png"), _('Clear'))        
        self.actn_filter_regex = QtWidgets.QAction(QtGui.QIcon(f"{ICONFOLDER}/asterisk1.png"), _('Regex'))   
        self.actn_filter_regex.setCheckable(True)
        self.actn_filter_regex.setChecked(False)
        
        self.le_filter = QtWidgets.QLineEdit('')
        self.le_filter.setStyleSheet('background-color: #fffff0;')
        self.le_filter.setPlaceholderText(_('Filter'))
        self.le_filter.textChanged.connect(self.on_filter_changed)
        self.le_filter.addAction(self.actn_filter_regex, 1)
        self.le_filter.addAction(self.actn_clear_filter, 1)
        self.actn_clear_filter.triggered.connect(QtCore.pyqtSlot(bool)(lambda _: self.le_filter.clear()))
        self.actn_filter_regex.toggled.connect(self.on_actn_filter_regex_toggled)
        
        self.lo_methods.addWidget(self.le_filter)
        self.lo_methods.addWidget(self.lw_methods)
        self.methods_widget = QtWidgets.QWidget()
        self.methods_widget.setLayout(self.lo_methods)

        self.splitter1.addWidget(self.methods_widget)
        self.splitter1.addWidget(self.editor)
        self.splitter1.setStretchFactor(0, 0)
        self.layout_main.addWidget(self.splitter1)

    def _config_editor(self):
        #self.editor.textChanged.connect(self.on_editor_text_changed)
        pass
        
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
        txt = 'self.editor.text()'
        try:
            self.lw_methods.itemChanged.disconnect()
        except:
            pass
        for i in range(self.lw_methods.count()):
            item = self.lw_methods.item(i)
            item.setCheckState(QtCore.Qt.Checked if f"    def {item.text()}:" in txt else QtCore.Qt.Unchecked)
        self.lw_methods.itemChanged.connect(self.on_lw_methods_changed)

    def _apply_filter(self, text):
        text = text.lower()
        try:
            self.lw_methods.itemChanged.disconnect()
        except:
            pass
        if not text:
            for i in range(self.lw_methods.count()):
                self.lw_methods.item(i).setHidden(False)
        else:
            regex = self.actn_filter_regex.isChecked()
            for i in range(self.lw_methods.count()):
                item = self.lw_methods.item(i)
                item_txt = item.text().lower()
                try:
                    matched = (regex and re.match(text, item_txt)) or (not regex and (text in item_txt))
                except:
                    matched = False
                item.setHidden(not matched)
        self.lw_methods.itemChanged.connect(self.on_lw_methods_changed)

    @QtCore.pyqtSlot(bool)
    def on_actn_filter_regex_toggled(self, checked):
        self.actn_filter_regex.setIcon(QtGui.QIcon(f"{ICONFOLDER}/asterisk{'' if checked else '1'}.png"))
        self._apply_filter(self.le_filter.text())

    @QtCore.pyqtSlot(str)
    def on_filter_changed(self, text):
        if text:
            self.le_filter.setStyleSheet('background-color: #3eb9f2;')
        else:
            self.le_filter.setStyleSheet('background-color: #fffff0;')
        self._apply_filter(text)

    @QtCore.pyqtSlot()
    def on_editor_text_changed(self):
        self._update_checked_methods()

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem, QtWidgets.QListWidgetItem)
    def on_lw_methods_select(self, current, previous):
        """
        self.editor.cancelFind()
        self.editor.setSelection(0, 0, 0, 0)
        self.editor.findFirst(f"    def {current.text()}:", False, True, False, False, index=0)
        """

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def on_lw_methods_changed(self, item):
        txt = 'self.editor.text()'
        func = item.text().replace('(', r'\(').replace(')', r'\)').replace(',', r'\,')
        pattern = f'(^[ ]{{4}}[#"].*)*(^[ ]{{4}}@.+?)*(^[ ]{{4}}def {func}\\:)'
        res1 = re.search(pattern, txt, re.M | re.S)
        if res1 is None and item.checkState():
            # func not found, add it
            txt += '\n\n    @replace #@before @after\n' + '\n'.join([('    ' + l) for l in item.data(QtCore.Qt.UserRole).split('\n')])
            #self.editor.setText(txt)
            self._update_checked_methods()
            self.lw_methods.setCurrentItem(item, QtCore.QItemSelectionModel.Current)
        elif (not res1 is None) and (not bool(item.checkState())):
            # func found, delete it
            res2 = PluginSynEditorWidget.RESRCH.search(txt, res1.end(res1.lastindex))
            if not res2 is None:
                txt = txt[:res1.start()] + txt[res2.start():]
            else:
                txt = txt[:res1.start()]
            #self.editor.setText(txt)
            self._update_checked_methods()

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def on_lw_methods_dblclicked(self, item):
        checked = bool(item.checkState())
        item.setCheckState(QtCore.Qt.Unchecked if checked else QtCore.Qt.Checked)