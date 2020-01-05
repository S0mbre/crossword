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
    def on_authenticationRequired(self, requestUrl, authenticator):
        mainwindow = self.view().window()
        dia = PasswordDialog(parent=mainwindow)
        if not dia.exec():
            authenticator = None
            return
        auth = dia.get_auth()
        authenticator.setUser(auth[0])
        authenticator.setPassword(auth[1])

    @QtCore.pyqtSlot(QtCore.QUrl, QtWebEngineWidgets.QWebEnginePage.Feature)
    def on_featurePermissionRequested(self, securityOrigin, feature):
        questions = {QtWebEngineWidgets.QWebEnginePage.Geolocation: 'Allow {} to access your location information?',
                     QtWebEngineWidgets.QWebEnginePage.MediaAudioCapture: 'Allow {} to access your microphone?',
                     QtWebEngineWidgets.QWebEnginePage.MediaVideoCapture: 'Allow {} to access your webcam?',
                     QtWebEngineWidgets.QWebEnginePage.MediaAudioVideoCapture: 'Allow {} to access your microphone and webcam?',
                     QtWebEngineWidgets.QWebEnginePage.MouseLock: 'Allow {} to lock your mouse cursor?',
                     QtWebEngineWidgets.QWebEnginePage.DesktopVideoCapture: 'Allow {} to capture video of your desktop?',
                     QtWebEngineWidgets.QWebEnginePage.DesktopAudioVideoCapture: 'Allow {} to capture audio and video of your desktop?',
                     QtWebEngineWidgets.QWebEnginePage.Notifications: 'Allow {} to show notification on your desktop?'} 
        mainwindow = self.view().window()        
        if feature in questions and MsgBox(questions[feature].format(securityOrigin.host()), mainwindow, 'Permission Request', 'ask') == QtWidgets.QMessageBox.Yes:
            self.setFeaturePermission(securityOrigin, feature, QtWebEngineWidgets.QWebEnginePage.PermissionGrantedByUser)
        else:
            self.setFeaturePermission(securityOrigin, feature, QtWebEngineWidgets.QWebEnginePage.PermissionDeniedByUser)

    @QtCore.pyqtSlot('const QUrl &requestUrl, QAuthenticator *authenticator, const QString &proxyHost')
    def on_proxyAuthenticationRequired(self, requestUrl, authenticator, proxyHost):
        mainwindow = self.view().window()
        dia = PasswordDialog(user_label='Proxy user', password_label='Proxy password', parent=mainwindow)
        if not dia.exec():
            authenticator = None
            return
        auth = dia.get_auth()
        authenticator.setUser(auth[0])
        authenticator.setPassword(auth[1])

    @QtCore.pyqtSlot(QtWebEngineCore.QWebEngineRegisterProtocolHandlerRequest)
    def on_registerProtocolHandlerRequested(self, request):
        if MsgBox(f"Allow {request.origin().host()} to open all {request.scheme()} links?", mainwindow, 'Permission Request', 'ask') == QtWidgets.QMessageBox.Yes:
            request.accept()
        else:
            request.reject()

    @QtCore.pyqtSlot(QtWebEngineWidgets.QWebEngineClientCertificateSelection)
    def on_selectClientCertificate(self, selection):
        selection.select(selection.certificates()[0])

##############################################################################
######          WebView
##############################################################################

class WebView(QtWebEngineWidgets.QWebEngineView):

    def __init__(self, parent=None):
        super.__init__(parent)
        self.loadProgress = 100
        self.loadStarted.connect(self.on_loadStarted)
        self.loadProgress.connect(self.on_loadProgress)
        self.loadFinished.connect(self.on_loadFinished)
        self.iconChanged.connect(self.on_iconChanged)
        self.renderProcessTerminated.connect(self.on_renderProcessTerminated)

    def setPage(self, page):
        self.createWebActionTrigger(page, QtWebEngineWidgets.QWebEnginePage.Forward)
        self.createWebActionTrigger(page, QtWebEngineWidgets.QWebEnginePage.Back)
        self.createWebActionTrigger(page, QtWebEngineWidgets.QWebEnginePage.Reload)
        self.createWebActionTrigger(page, QtWebEngineWidgets.QWebEnginePage.Stop)
        super().setPage(page)

    def createWebActionTrigger(self, page, webAction):
        action = page.action(webAction)
        action.changed.connect(self.on_pageaction_changed)

    def on_pageaction_changed(self):
        



##############################################################################
######          WebPopupWindow
##############################################################################

class WebPopupWindow(QtWidgets.QWidget):

    def __init__(self, profile: QtWebEngineWidgets.QWebEngineProfile, parent=None, flags=QtCore.Qt.WindowFlags()):
        super().__init__(parent, flags)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum) 
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.setContentsMargins(0, 0, 0, 0)
        self.le_url = QtWidgets.QLineEdit()
        self.act_favicon = QtWidgets.QAction()
        self.wview = 
        
