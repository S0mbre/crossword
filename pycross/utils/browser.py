# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

##############################################################################
# Implementation uses Qt Simple Browser example: 
# https://doc.qt.io/qt-5/qtwebengine-webenginewidgets-simplebrowser-example.html
##############################################################################

from PyQt5 import (QtGui, QtCore, QtWidgets, QtNetwork, 
                    QtWebEngineWidgets, QtWebEngineCore, QtWebEngine)
from ..forms import PasswordDialog
from .utils import *
from .globalvars import *   

##############################################################################
######          WebPage
##############################################################################

class WebPage(QtWebEngineWidgets.QWebEnginePage):

    def __init__(self, profile: QtWebEngineWidgets.QWebEngineProfile, parent=None):
        super().__init__(profile, parent)
        self.authenticationRequired.connect(self.on_authenticationRequired)
        self.featurePermissionRequested.connect(self.on_featurePermissionRequested)
        self.proxyAuthenticationRequired.connect(self.on_proxyAuthenticationRequired)
        self.registerProtocolHandlerRequested.connect(self.on_registerProtocolHandlerRequested)
        self.selectClientCertificate.connect(self.on_selectClientCertificate)

    def certificateError(self, error: QtWebEngineWidgets.QWebEngineCertificateError):
        """
        Override event to get user choice: ignore or reject certificate error.
        """
        mainwindow = self.view().window()
        deferredError = error
        deferredError.defer()
        if not error.deferred():
            MsgBox(error.errorDescription(), mainwindow, 'Certificate Error', 'error')
        else:
            reply = MsgBox(f"{error.errorDescription()}{NEWLINE}Press YES to ignore certificate or NO to reject certificate.", 
                            mainwindow, 'Certificate Error', 'warn', 
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                error.ignoreCertificateError()
            else:
                error.rejectCertificate()
        return True

    @QtCore.pyqtSlot('const QUrl &requestUrl, QAuthenticator *authenticator')
    def on_authenticationRequired(self, requestUrl: QtCore.QUrl, authenticator: QtNetwork.QAuthenticator):
        mainwindow = self.view().window()
        dia = PasswordDialog(parent=mainwindow)
        if not dia.exec():
            authenticator = None
            return
        auth = dia.get_auth()
        authenticator.setUser(auth[0])
        authenticator.setPassword(auth[1])

