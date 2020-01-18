# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

##############################################################################
# Implementation uses Qt Simple Browser example: 
# https://doc.qt.io/qt-5/qtwebengine-webenginewidgets-simplebrowser-example.html
##############################################################################

from PyQt5 import (QtGui, QtCore, QtWidgets, QtNetwork, 
                    QtWebEngineWidgets, QtWebEngineCore, QtWebEngine)

from utils.globalvars import * 
from utils.utils import *
from forms import (PasswordDialog, AboutDialog)

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
        try:
            self.selectClientCertificate.connect(self.on_selectClientCertificate)
        except:
            pass

    def certificateError(self, error: QtWebEngineWidgets.QWebEngineCertificateError):
        """
        Override event to get user choice: ignore or reject certificate error.
        """
        mainwindow = self.view().window()
        deferredError = error
        deferredError.defer()

        def handle_error():
            if not deferredError.deferred():
                MsgBox(deferredError.errorDescription(), mainwindow, _('Certificate Error'), 'error')
            else:
                reply = MsgBox(_("{}\nPress YES to ignore certificate or NO to reject certificate.").format(deferredError.errorDescription()), 
                                mainwindow, _('Certificate Error'), 'warn', 
                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if reply == QtWidgets.QMessageBox.Yes:
                    deferredError.ignoreCertificateError()
                else:
                    deferredError.rejectCertificate()

        QtCore.QTimer.singleShot(0, mainwindow, handle_error)        
        return True

    @QtCore.pyqtSlot('QUrl, QAuthenticator*')
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
        questions = {QtWebEngineWidgets.QWebEnginePage.Geolocation: _('Allow {} to access your location information?'),
                     QtWebEngineWidgets.QWebEnginePage.MediaAudioCapture: _('Allow {} to access your microphone?'),
                     QtWebEngineWidgets.QWebEnginePage.MediaVideoCapture: _('Allow {} to access your webcam?'),
                     QtWebEngineWidgets.QWebEnginePage.MediaAudioVideoCapture: _('Allow {} to access your microphone and webcam?'),
                     QtWebEngineWidgets.QWebEnginePage.MouseLock: _('Allow {} to lock your mouse cursor?'),
                     QtWebEngineWidgets.QWebEnginePage.DesktopVideoCapture: _('Allow {} to capture video of your desktop?'),
                     QtWebEngineWidgets.QWebEnginePage.DesktopAudioVideoCapture: _('Allow {} to capture audio and video of your desktop?'),
                     QtWebEngineWidgets.QWebEnginePage.Notifications: _('Allow {} to show notification on your desktop?')} 
        mainwindow = self.view().window()        
        if feature in questions and MsgBox(questions[feature].format(securityOrigin.host()), mainwindow, _('Permission Request'), 'ask') == QtWidgets.QMessageBox.Yes:
            self.setFeaturePermission(securityOrigin, feature, QtWebEngineWidgets.QWebEnginePage.PermissionGrantedByUser)
        else:
            self.setFeaturePermission(securityOrigin, feature, QtWebEngineWidgets.QWebEnginePage.PermissionDeniedByUser)

    @QtCore.pyqtSlot('QUrl, QAuthenticator*, QString')
    def on_proxyAuthenticationRequired(self, requestUrl, authenticator, proxyHost):
        mainwindow = self.view().window()
        dia = PasswordDialog(user_label=_('Proxy user'), password_label=_('Proxy password'), parent=mainwindow)
        if not dia.exec():
            authenticator = None
            return
        auth = dia.get_auth()
        authenticator.setUser(auth[0])
        authenticator.setPassword(auth[1])

    @QtCore.pyqtSlot(QtWebEngineCore.QWebEngineRegisterProtocolHandlerRequest)
    def on_registerProtocolHandlerRequested(self, request):
        mainwindow = self.view().window()
        if MsgBox(_("Allow {} to open all {} links?").format(request.origin().host(), request.scheme()), mainwindow, _('Permission Request'), 'ask') == QtWidgets.QMessageBox.Yes:
            request.accept()
        else:
            request.reject()

    @QtCore.pyqtSlot('QWebEngineClientCertificateSelection')
    def on_selectClientCertificate(self, selection):
        try:
            selection.select(selection.certificates()[0])
        except:
            pass


##############################################################################
######          WebView
##############################################################################

class WebPopupWindow(QtWidgets.QWidget):
    pass

class WebView(QtWebEngineWidgets.QWebEngineView):

    webActionEnabledChanged = QtCore.pyqtSignal(QtWebEngineWidgets.QWebEnginePage.WebAction, bool)
    favIconChanged = QtCore.pyqtSignal(QtGui.QIcon)
    devToolsRequested = QtCore.pyqtSignal(QtWebEngineWidgets.QWebEnginePage)

    def __init__(self, parent=None):
        QtWebEngineWidgets.QWebEngineView.__init__(self, parent)
        self.m_loadProgress = 100
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
        action.changed.connect(QtCore.pyqtSlot()(lambda: self.webActionEnabledChanged.emit(webAction, action.isEnabled())))

    def isWebActionEnabled(self, webAction):
        return self.page().action(webAction).isEnabled()

    def favIcon(self):
        icon = self.icon()
        if icon: return icon
        if self.m_loadProgress < 0:
            return QtGui.QIcon(f"{ICONFOLDER}/error.png")
        if self.m_loadProgress < 100:
            return QtGui.QIcon(f"{ICONFOLDER}/repeat-1.png")
        return QtGui.QIcon(f"{ICONFOLDER}/worldwide.png")

    def createWindow(self, windowtype):
        mainWindow = self.window()
        if not mainWindow: return None
        if windowtype == QtWebEngineWidgets.QWebEnginePage.WebBrowserTab:
            return mainWindow.tabWidget().createTab()
        if windowtype == QtWebEngineWidgets.QWebEnginePage.WebBrowserBackgroundTab:
            return mainWindow.tabWidget().createBackgroundTab()
        if windowtype == QtWebEngineWidgets.QWebEnginePage.WebBrowserWindow:
            return mainWindow.browser().createWindow().currentTab()
        if windowtype == QtWebEngineWidgets.QWebEnginePage.WebDialog:
            popup = WebPopupWindow(self.page().profile())
            popup.view().devToolsRequested.connect(self.devToolsRequested)
            return popup.view()
        return None

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        menu = self.page().createStandardContextMenu()
        actions = menu.actions()
        try:
            index = actions.index(self.page().action(QtWebEngineWidgets.QWebEnginePage.InspectElement))
            actions[index].setText(_('Inspect element'))
        except ValueError:
            if not self.page().action(QtWebEngineWidgets.QWebEnginePage.ViewSource) in actions:
                menu.addSeparator()
            action = QtWidgets.QAction(menu)
            action.setText(_('Open inspector in new window'))
            action.triggered.connect(self.on_menu_action)
            menu.addAction(action)

        menu.popup(event.globalPos())

    @QtCore.pyqtSlot(bool)
    def on_menu_action(self, checked):
        self.devToolsRequested.emit(self.page())

    @QtCore.pyqtSlot()
    def on_loadStarted(self):
        self.favIconChanged.emit(self.favIcon())

    @QtCore.pyqtSlot(int)
    def on_loadProgress(self, value):
        self.m_loadProgress = value

    @QtCore.pyqtSlot(bool)
    def on_loadFinished(self, ok):
        self.m_loadProgress = 100 if ok else -1
        self.favIconChanged.emit(self.favIcon())

    @QtCore.pyqtSlot(QtGui.QIcon)
    def on_iconChanged(self, icon):
        self.favIconChanged.emit(self.favIcon())

    @QtCore.pyqtSlot(QtWebEngineWidgets.QWebEnginePage.RenderProcessTerminationStatus, int)
    def on_renderProcessTerminated(self, terminationStatus, exitCode):
        if MsgBox(_(f"Page rendering stopped. Reload page?"), self.window(), _('Rendering stopped'), 'ask') == QtWidgets.QMessageBox.Yes:
            QtCore.QTimer.singleShot(0, self.reload)


##############################################################################
######          WebPopupWindow
##############################################################################

class WebPopupWindow(QtWidgets.QWidget):

    def __init__(self, profile: QtWebEngineWidgets.QWebEngineProfile, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum) 
        self.le_url = QtWidgets.QLineEdit()
        self.act_favicon = QtWidgets.QAction()
        self.wview = WebView(self)
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.setContentsMargins(0, 0, 0, 0)
        self.layout_main.addWidget(self.le_url)
        self.layout_main.addWidget(self.wview)
        self.wview.setPage(WebPage(profile, self.wview))
        self.wview.setFocus()
        self.le_url.setReadOnly(True)
        self.le_url.addAction(self.act_favicon, QtWidgets.QLineEdit.LeadingPosition)
        self.wview.titleChanged.connect(self.setWindowTitle)
        self.wview.urlChanged.connect(QtCore.pyqtSlot(QtCore.QUrl)(lambda url: self.le_url.setText(url.toDisplayString())))
        self.wview.favIconChanged.connect(self.act_favicon.setIcon)
        self.wview.page().geometryChangeRequested.connect(self.on_geometryChangeRequested)
        self.wview.page().windowCloseRequested.connect(self.close)

    def view(self):
        return self.wview

    @QtCore.pyqtSlot(QtCore.QRect)
    def on_geometryChangeRequested(self, newGeometry):
        window = self.windowHandle()
        if window:
            self.setGeometry(newGeometry.marginsRemoved(window.frameMargins()))
        self.show()
        self.wview.setFocus()

##############################################################################
######          TabWidget
##############################################################################

class TabWidget(QtWidgets.QTabWidget):

    linkHovered = QtCore.pyqtSignal(str)
    loadProgress = QtCore.pyqtSignal(int)
    titleChanged = QtCore.pyqtSignal(str)
    urlChanged = QtCore.pyqtSignal(QtCore.QUrl)
    favIconChanged = QtCore.pyqtSignal(QtGui.QIcon)
    webActionEnabledChanged = QtCore.pyqtSignal(QtWebEngineWidgets.QWebEnginePage.WebAction, bool)
    devToolsRequested = QtCore.pyqtSignal(QtWebEngineWidgets.QWebEnginePage)
    findTextFinished = QtCore.pyqtSignal(QtWebEngineCore.QWebEngineFindTextResult)

    def __init__(self, profile: QtWebEngineWidgets.QWebEngineProfile, parent=None):
        super().__init__(parent)
        self.m_profile = profile
        tabBar = self.tabBar()
        tabBar.setTabsClosable(True)
        tabBar.setSelectionBehaviorOnRemove(QtWidgets.QTabBar.SelectPreviousTab)
        tabBar.setMovable(True)
        tabBar.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tabBar.customContextMenuRequested.connect(self.on_customContextMenuRequested)
        tabBar.tabCloseRequested.connect(self.closeTab)
        tabBar.tabBarDoubleClicked.connect(QtCore.pyqtSlot(int)(lambda index: self.createTab() if index == -1 else None))
        #self.setTabBarAutoHide(True)
        self.setDocumentMode(True)
        self.setElideMode(QtCore.Qt.ElideRight)
        self.currentChanged.connect(self.on_currentChanged)
        self.icon = None
        if profile.isOffTheRecord():
            self.icon = QtWidgets.QLabel(self)
            self.icon.setPixmap(QtGui.QPixmap(f"{ICONFOLDER}/view-no.png").scaledToHeight(tabBar.height()))
            self.setStyleSheet(f"QTabWidget::tab-bar {{ left: {self.icon.pixmap().width()}px; }}")

    def currentWebView(self):
        return self.webView(self.currentIndex())

    def webView(self, index):
        return self.widget(index)

    def navigate(self, url, newtab=True, background=False):
        if newtab:
            webView = self.createBackgroundTab() if background else self.createTab()
        else:
            webView = self.webView(self.currentIndex())

        if not isinstance(url, QtCore.QUrl):
            url = QtCore.QUrl.fromUserInput(url) if not os.path.isfile(url) else QtCore.QUrl.fromLocalFile(url)

        webView.setUrl(url)

    def setupView(self, webView):

        @QtCore.pyqtSlot(str)
        def on_webview_titlechanged(title):
            index = self.indexOf(webView)
            if index != -1:
                self.setTabText(index, title)
                self.setTabToolTip(index, title)
            if self.currentIndex() == index:
                self.titleChanged.emit(title)
        
        @QtCore.pyqtSlot(QtCore.QUrl)
        def on_webview_urlchanged(url):
            index = self.indexOf(webView)
            if index != -1:
                self.tabBar().setTabData(index, url)
            if self.currentIndex() == index:
                self.urlChanged.emit(url)

        @QtCore.pyqtSlot(int)
        def on_webview_loadprogress(progress):
            if self.currentIndex() == self.indexOf(webView):
                self.loadProgress.emit(progress)

        @QtCore.pyqtSlot(str)
        def on_webview_linkhovered(url):
            if self.currentIndex() == self.indexOf(webView):
                self.linkHovered.emit(url)

        @QtCore.pyqtSlot(QtGui.QIcon)
        def on_webview_iconchanged(icon):
            index = self.indexOf(webView)
            if index != -1:
                self.setTabIcon(index, icon)
            if self.currentIndex() == index:
                self.favIconChanged.emit(icon)

        @QtCore.pyqtSlot(QtWebEngineWidgets.QWebEnginePage.WebAction, bool)
        def on_webview_webactionenabledchanged(action, enabled):
            if self.currentIndex() == self.indexOf(webView):
                self.webActionEnabledChanged.emit(action, enabled)

        @QtCore.pyqtSlot()
        def on_webview_windowcloserequested():
            index = self.indexOf(webView)
            if index >= 0:
                self.closeTab(index)         

        @QtCore.pyqtSlot(QtWebEngineCore.QWebEngineFindTextResult)
        def on_webview_findtextfinished(result):
            if self.currentIndex() == self.indexOf(webView):
                self.findTextFinished.emit(result)   

        webPage = webView.page()
        webView.titleChanged.connect(on_webview_titlechanged)
        webView.urlChanged.connect(on_webview_urlchanged)
        webView.loadProgress.connect(on_webview_loadprogress)
        webView.favIconChanged.connect(on_webview_iconchanged)
        webView.webActionEnabledChanged.connect(on_webview_webactionenabledchanged)
        webView.devToolsRequested.connect(self.devToolsRequested)
        webPage.linkHovered.connect(on_webview_linkhovered)
        webPage.windowCloseRequested.connect(on_webview_windowcloserequested)
        webPage.findTextFinished.connect(on_webview_findtextfinished)

    @QtCore.pyqtSlot()
    def createTab(self):
        webView = self.createBackgroundTab()
        self.setCurrentWidget(webView)
        return webView

    @QtCore.pyqtSlot()
    def createBackgroundTab(self):
        webView = WebView()
        webPage = WebPage(self.m_profile, webView)
        webView.setPage(webPage)
        self.setupView(webView)
        index = self.addTab(webView, _('Untitled'))
        self.setTabIcon(index, webView.favIcon())
        # Workaround for QTBUG-61770
        webView.resize(self.currentWidget().size())
        webView.show()
        return webView

    @QtCore.pyqtSlot()
    def reloadAllTabs(self):
        for i in range(self.count()):
            self.webView(i).reload()

    @QtCore.pyqtSlot(int)
    def closeOtherTabs(self, index):
        for i in range(self.count() - 1, index, -1):
            self.closeTab(i)
        for i in range(index - 1, -1, -1):
            self.closeTab(i)

    @QtCore.pyqtSlot(int)
    def closeTab(self, index):
        view = self.webView(index)
        if not view: return
        self.removeTab(index)
        if view.hasFocus() and self.count():
            self.currentWebView().setFocus()
        if not self.count():
            self.createTab()
        view.deleteLater()

    @QtCore.pyqtSlot(int)
    def cloneTab(self, index):
        view = self.webView(index)
        if not view: return
        tab = self.createTab()
        tab.setUrl(view.url())

    @QtCore.pyqtSlot(QtCore.QUrl)
    def setUrl(self, url):
        view = self.currentWebView()
        if not view: return
        view.setUrl(url)
        view.setFocus()

    @QtCore.pyqtSlot(QtWebEngineWidgets.QWebEnginePage.WebAction)
    def triggerWebPageAction(self, action):
        view = self.currentWebView()
        if not view: return
        view.triggerPageAction(action)
        view.setFocus()

    @QtCore.pyqtSlot()
    def nextTab(self):
        next_ = self.currentIndex() + 1
        if next_ == self.count():
            next_ = 0
        self.setCurrentIndex(next_)

    @QtCore.pyqtSlot()
    def previousTab(self):
        next_ = self.currentIndex() - 1
        if next_ < 0:
            next_ = self.count() - 1
        self.setCurrentIndex(next_)

    @QtCore.pyqtSlot(int)
    def reloadTab(self, index):
        view = self.webView(index)
        if view: view.reload()

    @QtCore.pyqtSlot(int)
    def on_currentChanged(self, index):
        if index != -1:
            view = self.webView(index)
            if not view.url().isEmpty():
                view.setFocus()
            self.titleChanged.emit(view.title())
            self.loadProgress.emit(view.m_loadProgress)
            self.urlChanged.emit(view.url())
            self.favIconChanged.emit(view.favIcon())
            self.webActionEnabledChanged.emit(QtWebEngineWidgets.QWebEnginePage.Back, view.isWebActionEnabled(QtWebEngineWidgets.QWebEnginePage.Back))
            self.webActionEnabledChanged.emit(QtWebEngineWidgets.QWebEnginePage.Forward, view.isWebActionEnabled(QtWebEngineWidgets.QWebEnginePage.Forward))
            self.webActionEnabledChanged.emit(QtWebEngineWidgets.QWebEnginePage.Stop, view.isWebActionEnabled(QtWebEngineWidgets.QWebEnginePage.Stop))
            self.webActionEnabledChanged.emit(QtWebEngineWidgets.QWebEnginePage.Reload, view.isWebActionEnabled(QtWebEngineWidgets.QWebEnginePage.Reload))
        else:
            self.titleChanged.emit('')
            self.loadProgress.emit(0)
            self.urlChanged.emit(QtCore.QUrl())
            self.favIconChanged.emit(QtGui.QIcon())
            self.webActionEnabledChanged.emit(QtWebEngineWidgets.QWebEnginePage.Back, False)
            self.webActionEnabledChanged.emit(QtWebEngineWidgets.QWebEnginePage.Forward, False)
            self.webActionEnabledChanged.emit(QtWebEngineWidgets.QWebEnginePage.Stop, False)
            self.webActionEnabledChanged.emit(QtWebEngineWidgets.QWebEnginePage.Reload, False)

    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_customContextMenuRequested(self, pos):
        menu = QtWidgets.QMenu()
        menu.addAction(_('New &Tab'), self.createTab, QtGui.QKeySequence.AddTab)
        index = self.tabBar().tabAt(pos)
        if index == -1:
            menu.addSeparator()
        else:
            action = menu.addAction(_('C&lone Tab'))
            action.triggered.connect(QtCore.pyqtSlot()(lambda: self.cloneTab(index)))
            menu.addSeparator()
            action = menu.addAction(_('&Close Tab'))
            action.setShortcut(QtGui.QKeySequence.Close)
            action.triggered.connect(QtCore.pyqtSlot()(lambda: self.closeTab(index)))
            action = menu.addAction(_('Close &Other Tabs'))
            action.triggered.connect(QtCore.pyqtSlot()(lambda: self.closeOtherTabs(index)))
            menu.addSeparator()
            action = menu.addAction(_('&Reload Tab'))
            action.setShortcut(QtGui.QKeySequence.Refresh)
            action.triggered.connect(QtCore.pyqtSlot()(lambda: self.reloadTab(index)))
        menu.addAction(_('Reload &All Tabs'), self.reloadAllTabs)
        menu.exec(QtGui.QCursor.pos())

##############################################################################
######          DownloadWidget
##############################################################################

class DownloadWidget(QtWidgets.QFrame):

    removeClicked = QtCore.pyqtSignal(QtWidgets.QFrame)

    def __init__(self, download: QtWebEngineWidgets.QWebEngineDownloadItem, parent=None):
        super().__init__(parent)
        self.m_download = download
        self.m_download.downloadProgress.connect(self.updateWidget)
        self.m_download.stateChanged.connect(self.updateWidget)
        self.m_timeAdded = QtCore.QElapsedTimer()
        self.m_timeAdded.start()
        self.layout_main = QtWidgets.QGridLayout()
        self.layout_main.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.l_filename = QtWidgets.QLabel(self.m_download.downloadFileName())
        self.l_filename.setStyleSheet('font-weight: bold;')
        self.btn_cancel = QtWidgets.QPushButton(QtGui.QIcon(f"{ICONFOLDER}/garbage.png"), _('Cancel'))
        self.btn_cancel.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.btn_cancel.clicked.connect(self.on_btn_cancel)
        self.l_url = QtWidgets.QLabel(self.m_download.url().toDisplayString())
        self.l_url.setMinimumWidth(350)
        self.pb = QtWidgets.QProgressBar()
        self.layout_main.addWidget(self.l_filename, 0, 0)
        self.layout_main.addWidget(self.btn_cancel, 0, 1)
        self.layout_main.addWidget(self.l_url, 1, 0, 1, 2)
        self.layout_main.addWidget(self.pb, 2, 0, 1, 2)
        self.setLayout(self.layout_main)
        self.updateWidget()

    @QtCore.pyqtSlot(bool)
    def on_btn_cancel(self, checked):
        if self.m_download.state() == QtWebEngineWidgets.QWebEngineDownloadItem.DownloadInProgress:
            self.m_download.cancel()
        else:
            self.removeClicked.emit(self)

    @QtCore.pyqtSlot()
    def updateWidget(self):
        totalBytes = self.m_download.totalBytes()
        receivedBytes = self.m_download.receivedBytes()
        bytesPerSecond = receivedBytes / self.m_timeAdded.elapsed() * 1000
        state = self.m_download.state()
        self.btn_cancel.setIcon(QtGui.QIcon(f"{ICONFOLDER}/garbage.png"))
        self.btn_cancel.setToolTip(_('Remove from list'))

        if state == QtWebEngineWidgets.QWebEngineDownloadItem.DownloadInProgress:
            self.btn_cancel.setIcon(QtGui.QIcon(f"{ICONFOLDER}/error.png"))
            self.btn_cancel.setToolTip(_('Stop download'))
            self.pb.setDisabled(False)
            if totalBytes > 0:
                self.pb.setValue(int(100 * receivedBytes / totalBytes))                
                self.pb.setFormat(_("%p% - {} of {} - {}/s").format(receivedBytes, totalBytes, bytesPerSecond))
            else:
                self.pb.setValue(0)
                self.pb.setFormat(_("{} downloaded - {}/s").format(receivedBytes, bytesPerSecond))

        elif state == QtWebEngineWidgets.QWebEngineDownloadItem.DownloadCompleted:
            self.pb.setDisabled(True)
            self.pb.setValue(100)                
            self.pb.setFormat(_("Completed - {} downloaded - {}/s").format(receivedBytes, bytesPerSecond))

        elif state == QtWebEngineWidgets.QWebEngineDownloadItem.DownloadCancelled:
            self.pb.setDisabled(True)
            self.pb.setValue(0)                
            self.pb.setFormat(_("Cancelled - {} downloaded - {}/s").format(receivedBytes, bytesPerSecond))

        elif state == QtWebEngineWidgets.QWebEngineDownloadItem.DownloadInterrupted:
            self.pb.setDisabled(True)
            self.pb.setValue(100)                
            self.pb.setFormat(_("Interrupted - {}").format(self.m_download.interruptReasonString()))


##############################################################################
######          DownloadManagerWidget
##############################################################################

class DownloadManagerWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_numDownloads = 0
        self.setBaseSize(500, 300)
        self.setWindowTitle(_('Downloads'))
        self.setWindowIcon(QtGui.QIcon(f"{ICONFOLDER}/folder-15.png"))
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)
        self.layout_main.setContentsMargins(0, 0, 0, 0)
        self.scroll_main = QtWidgets.QScrollArea()
        self.scroll_main.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scroll_main.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_main.setWidgetResizable(True)
        self.scroll_main.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.w_items = QtWidgets.QWidget()
        self.layout_items = QtWidgets.QVBoxLayout()
        self.layout_items.setSpacing(2)
        self.layout_items.setContentsMargins(3, 3, 3, 3)
        self.l_zeroitems = QtWidgets.QLabel(_('No downloads'))
        self.l_zeroitems.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.l_zeroitems.setAlignment(QtCore.Qt.AlignCenter)
        self.layout_items.addWidget(self.l_zeroitems)
        self.w_items.setLayout(self.layout_items)
        self.scroll_main.setWidget(self.w_items)
        self.layout_main.addWidget(self.scroll_main)
        self.setLayout(self.layout_main)

    def downloadRequested(self, download: QtWebEngineWidgets.QWebEngineDownloadItem):
        if not download or download.state() != QtWebEngineWidgets.QWebEngineDownloadItem.DownloadRequested:
            return
        selected_path = QtWidgets.QFileDialog.getSaveFileName(self, _('Save As'), os.path.join(download.downloadDirectory(), download.downloadFileName()))
        if not selected_path[0]: return
        selected_path = QtCore.QFileInfo(selected_path[0])
        download.setDownloadDirectory(selected_path.path())
        download.setDownloadFileName(selected_path.fileName())
        download.accept()
        self.add(DownloadWidget(download))
        self.show()

    @QtCore.pyqtSlot(DownloadWidget)
    def add(self, wdownload):
        wdownload.removeClicked.connect(self.remove)
        self.layout_items.insertWidget(0, wdownload, 0, QtCore.Qt.AlignTop)
        self.m_numDownloads += 1
        if self.m_numDownloads == 0:
            self.l_zeroitems.hide() 

    @QtCore.pyqtSlot(QtWidgets.QFrame)
    def remove(self, wdownload):
        self.layout_items.removeWidget(wdownload)
        wdownload.deleteLater()
        self.m_numDownloads -= 1
        if self.m_numDownloads == 0:
            self.l_zeroitems.show()


##############################################################################
######          BrowserWindow
##############################################################################

class BrowserWindow(QtWidgets.QMainWindow):

    def __init__(self, browser, profile, forDevTools=False):
        super().__init__()
        self.m_browser = browser
        self.m_profile = profile
        self.m_tabWidget = TabWidget(profile, self)
        self.m_progressBar = None
        self.m_historyBackAction = QtWidgets.QAction()
        self.m_historyForwardAction = QtWidgets.QAction()
        self.m_stopAction = QtWidgets.QAction()
        self.m_reloadAction = QtWidgets.QAction()
        self.m_stopReloadAction = QtWidgets.QAction()
        self.m_favAction = QtWidgets.QAction()
        self.m_urlLineEdit = QtWidgets.QLineEdit()
        self.m_lastSearch = ''
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

        if not forDevTools:
            self.addToolBar(self.createToolBar())
            menu = self.menuBar()
            menu.addMenu(self.createFileMenu(self.m_tabWidget))
            menu.addMenu(self.createEditMenu())
            menu.addMenu(self.createViewMenu(self.tb_main))
            menu.addMenu(self.createWindowMenu(self.m_tabWidget))
            menu.addMenu(self.createHelpMenu())

        self.centralWidget = QtWidgets.QWidget(self)
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.setSpacing(0)
        self.layout_main.setContentsMargins(0, 0, 0, 0)

        if not forDevTools:
            self.addToolBarBreak()
            self.m_progressBar = QtWidgets.QProgressBar()
            self.m_progressBar.setMaximumHeight(1)
            self.m_progressBar.setTextVisible(False)
            self.m_progressBar.setStyleSheet('QProgressBar {border: 0px} QProgressBar::chunk {background-color: #da4453}')
            self.layout_main.addWidget(self.m_progressBar)

        self.layout_main.addWidget(self.m_tabWidget)
        self.centralWidget.setLayout(self.layout_main)
        self.setCentralWidget(self.centralWidget)

        self.m_tabWidget.titleChanged.connect(self.on_titleChanged)
        if not forDevTools:
            self.m_tabWidget.linkHovered.connect(QtCore.pyqtSlot(str)(lambda url: self.statusBar().showMessage(url)))
            self.m_tabWidget.loadProgress.connect(self.on_loadProgress)
            self.m_tabWidget.webActionEnabledChanged.connect(self.on_webActionEnabledChanged)
            self.m_tabWidget.urlChanged.connect(QtCore.pyqtSlot(QtCore.QUrl)(lambda url: self.m_urlLineEdit.setText(url.toDisplayString())))
            self.m_tabWidget.favIconChanged.connect(self.m_favAction.setIcon)
            self.m_tabWidget.devToolsRequested.connect(self.on_devToolsRequested)
            self.m_tabWidget.findTextFinished.connect(self.on_findTextFinished)
            self.m_urlLineEdit.returnPressed.connect(QtCore.pyqtSlot()(lambda: self.m_tabWidget.setUrl(QtCore.QUrl.fromUserInput(self.m_urlLineEdit.text()))))
            self.focusUrlLineEditAction = QtWidgets.QAction()
            self.focusUrlLineEditAction.setShortcut(QtGui.QKeySequence('Ctrl+l'))
            self.focusUrlLineEditAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.m_urlLineEdit.setFocus(QtCore.Qt.ShortcutFocusReason)))
            self.addAction(self.focusUrlLineEditAction)

        self.on_titleChanged('')
        self.m_tabWidget.createTab()

    def sizeHint(self):
        desktopRect = QtWidgets.QApplication.primaryScreen().geometry()
        return desktopRect.size() * 0.8

    def closeEvent(self, event):
        cnt = self.m_tabWidget.count()
        if cnt > 1:
            reply = MsgBox(_('Are you sure you want to close the window? There are {} tabs open.'), self, _('Confirm quit'), 'ask').format(cnt)
            if reply != QtWidgets.QMessageBox.Yes:
                event.ignore()
                return
        event.accept()
        self.deleteLater()

    def navigate(self, url, newtab=True, background=False):
        self.m_tabWidget.navigate(url, newtab, background)

    def tabWidget(self):
        return self.m_tabWidget

    def currentTab(self):
        return self.m_tabWidget.currentWebView()

    def createFileMenu(self, tabWidget):

        @QtCore.pyqtSlot()
        def on_act_new_tab():
            self.m_tabWidget.createTab()
            self.m_urlLineEdit.setFocus()

        self.fileMenu = QtWidgets.QMenu(_('&File'))

        self.fileMenu.addAction(_('&New window'), self.on_act_new_window, QtGui.QKeySequence.New)
        self.fileMenu.addAction(_('New &incognito window'), self.on_act_new_incognito_window)
        self.newTabAction = QtWidgets.QAction(_('New &tab'))
        self.newTabAction.setShortcuts(QtGui.QKeySequence.AddTab)
        self.newTabAction.triggered.connect(on_act_new_tab)
        self.fileMenu.addAction(self.newTabAction)
        self.fileMenu.addAction(_('&Open file...'), self.on_fileopen, QtGui.QKeySequence.Open)
        self.fileMenu.addSeparator()

        self.closeTabAction = QtWidgets.QAction(_('&Close tab'))
        self.closeTabAction.setShortcuts(QtGui.QKeySequence.Close)
        self.closeTabAction.triggered.connect(QtCore.pyqtSlot()(lambda: tabWidget.closeTab(tabWidget.currentIndex())))
        self.fileMenu.addAction(self.closeTabAction)

        self.closeAction = QtWidgets.QAction(_('&Quit'))
        self.closeAction.setShortcut(QtGui.QKeySequence('Ctrl+q'))
        self.closeAction.triggered.connect(self.close)
        self.fileMenu.addAction(self.closeAction)

        self.fileMenu.aboutToShow.connect(QtCore.pyqtSlot()(lambda: self.closeAction.setText(_('&Quit') if len(self.m_browser.windows()) == 1 else _('&Close window'))))
        return self.fileMenu

    def createEditMenu(self):
        self.editMenu = QtWidgets.QMenu(_('&Edit'))

        self.findAction = self.editMenu.addAction(_('&Find'))
        self.findAction.setShortcuts(QtGui.QKeySequence.Find)
        self.findAction.triggered.connect(self.on_act_find)

        self.findNextAction = self.editMenu.addAction(_('Find &next'))
        self.findNextAction.setShortcuts(QtGui.QKeySequence.FindNext)
        self.findNextAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.currentTab().findText(self.m_lastSearch) if self.currentTab() and self.m_lastSearch else None))

        self.findPreviousAction = self.editMenu.addAction(_('Find &previous'))
        self.findPreviousAction.setShortcuts(QtGui.QKeySequence.FindPrevious)
        self.findPreviousAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.currentTab().findText(self.m_lastSearch, QtWebEngineWidgets.QWebEnginePage.FindBackward) if self.currentTab() and self.m_lastSearch else None))

        return self.editMenu

    def createViewMenu(self, toolbar):

        self.viewMenu = QtWidgets.QMenu(_('&View'))

        self.stopAction = self.viewMenu.addAction(_('&Stop'))
        self.stopAction.setShortcuts([QtCore.Qt.Key_Escape, QtGui.QKeySequence(QtCore.Qt.CTRL, QtCore.Qt.Key_Period)])
        self.stopAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.m_tabWidget.triggerWebPageAction(QtWebEngineWidgets.QWebEnginePage.Stop)))

        self.reloadAction = self.viewMenu.addAction(_('&Reload'))
        self.reloadAction.setShortcuts(QtGui.QKeySequence.Refresh)
        self.reloadAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.m_tabWidget.triggerWebPageAction(QtWebEngineWidgets.QWebEnginePage.Reload)))

        self.zoomInAction = self.viewMenu.addAction(_('Zoom &in'))
        self.zoomInAction.setShortcuts(QtGui.QKeySequence.ZoomIn)
        self.zoomInAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.currentTab().setZoomFactor(self.currentTab().zoomFactor() + 0.1) if self.currentTab() else None))

        self.zoomOutAction = self.viewMenu.addAction(_('Zoom &out'))
        self.zoomOutAction.setShortcuts(QtGui.QKeySequence.ZoomOut)
        self.zoomOutAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.currentTab().setZoomFactor(self.currentTab().zoomFactor() - 0.1) if self.currentTab() else None))

        self.viewMenu.addSeparator()

        self.fullscreenAction = self.viewMenu.addAction(_('&Fullscreen'))
        self.fullscreenAction.setShortcuts(QtGui.QKeySequence.FullScreen)
        self.fullscreenAction.setCheckable(True)
        self.fullscreenAction.toggled.connect(self.on_fullscreenAction)

        self.viewMenu.addSeparator()

        self.viewToolbarAction = QtWidgets.QAction(_('Hide toolbar'))

        @QtCore.pyqtSlot()
        def on_viewToolbarAction():
            if toolbar.isVisible():
                self.viewToolbarAction.setText(_('Show toolbar'))
                toolbar.close()
            else:
                self.viewToolbarAction.setText(_('Hide toolbar'))
                toolbar.show()

        self.viewToolbarAction.setShortcut(QtGui.QKeySequence('Ctrl+|'))
        self.viewToolbarAction.triggered.connect(on_viewToolbarAction)
        self.viewMenu.addAction(self.viewToolbarAction)

        self.viewStatusbarAction = QtWidgets.QAction(_('Hide status bar'))

        @QtCore.pyqtSlot()
        def on_viewStatusbarAction():
            sb = self.statusBar()
            if sb.isVisible():
                self.viewStatusbarAction.setText(_('Show status bar'))
                sb.close()
            else:
                self.viewStatusbarAction.setText(_('Hide status bar'))
                sb.show()

        self.viewStatusbarAction.setShortcut(QtGui.QKeySequence('Ctrl+/'))
        self.viewStatusbarAction.triggered.connect(on_viewStatusbarAction)
        self.viewMenu.addAction(self.viewStatusbarAction)

        return self.viewMenu

    def createWindowMenu(self, tabWidget):
        self.windowMenu = QtWidgets.QMenu(_('&Window'))

        self.nextTabAction = QtWidgets.QAction(_('Show next tab'))
        self.nextTabAction.setShortcuts(QtGui.QKeySequence.NextChild)
        self.nextTabAction.triggered.connect(tabWidget.nextTab)

        self.previousTabAction = QtWidgets.QAction(_('Show previous tab'))
        self.previousTabAction.setShortcuts(QtGui.QKeySequence.PreviousChild)
        self.previousTabAction.triggered.connect(tabWidget.previousTab)

        @QtCore.pyqtSlot()
        def on_windowMenu_showing():
            self.windowMenu.clear()
            self.windowMenu.addAction(self.nextTabAction)
            self.windowMenu.addAction(self.previousTabAction)
            self.windowMenu.addSeparator()
            for i, window in enumerate(self.m_browser.windows()):
                actn = self.windowMenu.addAction(window.windowTitle(), self.on_act_show_window)
                actn.setData(i)
                actn.setCheckable(True)
                if window is self:
                    actn.setChecked(True)

        self.windowMenu.aboutToShow.connect(on_windowMenu_showing)

        return self.windowMenu

    def createHelpMenu(self):
        self.helpMenu = QtWidgets.QMenu(_('&Help'))
        self.helpMenu.addAction(_('&About'), QtCore.pyqtSlot()(lambda: AboutDialog(self).exec()))
        return self.helpMenu

    def createToolBar(self):
        self.tb_main = QtWidgets.QToolBar(_('Navigation'))
        self.tb_main.setMovable(False)
        self.tb_main.toggleViewAction().setEnabled(False)

        self.historyBackAction = QtWidgets.QAction()
        standard_back = QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Back) + [QtGui.QKeySequence(QtCore.Qt.Key_Back)]
        self.historyBackAction.setShortcuts([k for k in standard_back if k[0] != QtCore.Qt.Key_Backspace])
        self.historyBackAction.setIconVisibleInMenu(False)
        self.historyBackAction.setIcon(QtGui.QIcon(f"{ICONFOLDER}/rewind.png"))
        self.historyBackAction.setToolTip(_('Go back in history'))
        self.historyBackAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.m_tabWidget.triggerWebPageAction(QtWebEngineWidgets.QWebEnginePage.Back)))
        self.tb_main.addAction(self.historyBackAction)

        self.historyForwardAction = QtWidgets.QAction()
        standard_forward = QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Forward) + [QtGui.QKeySequence(QtCore.Qt.Key_Forward)]
        self.historyForwardAction.setShortcuts([k for k in standard_forward if (k[0] & QtCore.Qt.Key_unknown) != QtCore.Qt.Key_Backspace])
        self.historyForwardAction.setIconVisibleInMenu(False)
        self.historyForwardAction.setIcon(QtGui.QIcon(f"{ICONFOLDER}/fast-forward.png"))
        self.historyForwardAction.setToolTip(_('Go forward in history'))
        self.historyForwardAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.m_tabWidget.triggerWebPageAction(QtWebEngineWidgets.QWebEnginePage.Forward)))
        self.tb_main.addAction(self.historyForwardAction)

        self.stopReloadAction = QtWidgets.QAction()
        self.stopReloadAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.m_tabWidget.triggerWebPageAction(QtWebEngineWidgets.QWebEnginePage.WebAction(self.stopReloadAction.data()))))
        self.tb_main.addAction(self.stopReloadAction)

        self.m_urlLineEdit = QtWidgets.QLineEdit()
        self.m_favAction = QtWidgets.QAction()
        self.m_urlLineEdit.addAction(self.m_favAction, QtWidgets.QLineEdit.LeadingPosition)
        self.m_urlLineEdit.setClearButtonEnabled(True)
        self.tb_main.addWidget(self.m_urlLineEdit)

        self.downloadsAction = QtWidgets.QAction()
        self.downloadsAction.setIcon(QtGui.QIcon(f"{ICONFOLDER}/folder-15.png"))
        self.downloadsAction.setToolTip(_('Show downloads'))
        self.downloadsAction.triggered.connect(QtCore.pyqtSlot()(lambda: self.m_browser.downloadManagerWidget().show()))
        self.tb_main.addAction(self.downloadsAction)

        return self.tb_main

    @QtCore.pyqtSlot(bool)
    def on_fullscreenAction(self, checked):
        tb = self.tb_main
        sb = self.statusBar()
        if checked:       
            self.viewToolbarAction.setEnabled(False)     
            self.viewStatusbarAction.setEnabled(False)     
            tb.close()
            sb.close()
            self.showFullScreen()
        else:            
            self.showNormal()
            if self.viewToolbarAction.text().startswith(_('Hide')):
                tb.show()
            else:
                tb.close()
            if self.viewStatusbarAction.text().startswith(_('Hide')):
                sb.show()
            else:
                sb.close()
            self.viewToolbarAction.setEnabled(True)     
            self.viewStatusbarAction.setEnabled(True)

    @QtCore.pyqtSlot(QtWebEngineWidgets.QWebEnginePage.WebAction, bool)
    def on_webActionEnabledChanged(self, action, enabled):
        if action == QtWebEngineWidgets.QWebEnginePage.Back:
            self.m_historyBackAction.setEnabled(enabled)
        elif action == QtWebEngineWidgets.QWebEnginePage.Forward:
            self.m_historyForwardAction.setEnabled(enabled)
        elif action == QtWebEngineWidgets.QWebEnginePage.Reload:
            self.m_reloadAction.setEnabled(enabled)
        elif action == QtWebEngineWidgets.QWebEnginePage.Stop:
            self.m_stopAction.setEnabled(enabled)

    @QtCore.pyqtSlot(str)
    def on_titleChanged(self, title):
        suffix = _('pyCross Browser [incognito]') if self.m_profile.isOffTheRecord() else _('pyCross Browser')
        self.setWindowTitle(suffix if not title else f"{title} - {suffix}")

    @QtCore.pyqtSlot()
    def on_act_new_window(self):
        window = self.m_browser.createWindow()
        window.m_urlLineEdit.setFocus()

    @QtCore.pyqtSlot()
    def on_act_new_incognito_window(self):
        window = self.m_browser.createWindow(True)
        window.m_urlLineEdit.setFocus()

    @QtCore.pyqtSlot()
    def on_fileopen(self):
        (url, _) = QtWidgets.QFileDialog.getOpenFileUrl(self, _('Open web resource'), filter=_('Web Resources (*.html *.htm *.svg *.png *.gif *.svgz);;All files (*.*)'))
        if not url.isEmpty(): 
            self.navigate(url, False)

    @QtCore.pyqtSlot()
    def on_act_find(self):
        if not self.currentTab(): return
        res = UserInput(parent=self, title=_('Find'), label=_('Find:'))
        if all(res):
            self.m_lastSearch = res[0]
            self.currentTab().findText(self.m_lastSearch)

    @QtCore.pyqtSlot(int)
    def on_loadProgress(self, progress):

        stopIcon = QtGui.QIcon(f"{ICONFOLDER}/error.png")
        reloadIcon = QtGui.QIcon(f"{ICONFOLDER}/repeat-1.png")

        if progress > 0 and progress < 100:
            self.stopReloadAction.setData(QtWebEngineWidgets.QWebEnginePage.Stop)
            self.stopReloadAction.setIcon(stopIcon)
            self.stopReloadAction.setToolTip(_('Stop loading page'))
            self.m_progressBar.setValue(progress)
        else:
            self.stopReloadAction.setData(QtWebEngineWidgets.QWebEnginePage.Reload)
            self.stopReloadAction.setIcon(reloadIcon)
            self.stopReloadAction.setToolTip(_('Reload page'))
            self.m_progressBar.setValue(0)

    @QtCore.pyqtSlot()
    def on_act_show_window(self):
        action = self.sender()
        if not isinstance(action, QtWidgets.QAction): return
        offset = action.data()
        windows = self.m_browser.windows()
        windows[offset].activateWindow()
        windows[offset].currentTab().setFocus()

    @QtCore.pyqtSlot(QtWebEngineWidgets.QWebEnginePage)
    def on_devToolsRequested(self, source):
        source.setDevToolsPage(self.m_browser.createDevToolsWindow().currentTab().page())
        source.triggerAction(QtWebEngineWidgets.QWebEnginePage.InspectElement)

    @QtCore.pyqtSlot(QtWebEngineCore.QWebEngineFindTextResult)
    def on_findTextFinished(self, result):
        sb = self.statusBar()
        if not result.numberOfMatches():
            sb.showMessage(_("'{}' not found").format(self.m_lastSearch))
        else:
            sb.showMessage(_("'{}' found: {}/{}").format(self.m_lastSearch, result.activeMatch(), result.numberOfMatches()))

##############################################################################
######          Browser
##############################################################################

class Browser:

    def __init__(self):
        self.m_otrProfile = None
        self.m_windows = []
        self.m_downloadManagerWidget = DownloadManagerWidget()
        # Quit application if the download manager window is the only remaining window
        self.m_downloadManagerWidget.setAttribute(QtCore.Qt.WA_QuitOnClose, False)
        QtWebEngineWidgets.QWebEngineProfile.defaultProfile().downloadRequested.connect(self.m_downloadManagerWidget.downloadRequested)

    def navigate(self, url, newtab=True, background=False, offTheRecord=False):
        window = self.createWindow(offTheRecord) if (not self.m_windows or (offTheRecord and not self.m_windows[0].isOffTheRecord())) else self.m_windows[0]
        window.navigate(url, newtab, background)
        window.show()

    def createWindow(self, offTheRecord=False):
        if offTheRecord and not self.m_otrProfile:
            self.m_otrProfile = QtWebEngineWidgets.QWebEngineProfile() # incognito by default
            self.m_otrProfile.downloadRequested.connect(self.m_downloadManagerWidget.downloadRequested)
        profile = self.m_otrProfile if offTheRecord else QtWebEngineWidgets.QWebEngineProfile.defaultProfile()
        mainWindow = BrowserWindow(self, profile, False)
        mainWindow.destroyed.connect(QtCore.pyqtSlot()(lambda: self.m_windows.remove(mainWindow)))
        self.m_windows.append(mainWindow)
        mainWindow.show()
        return mainWindow

    def createDevToolsWindow(self):
        profile = QtWebEngineWidgets.QWebEngineProfile.defaultProfile()
        mainWindow = BrowserWindow(self, profile, True)
        mainWindow.destroyed.connect(QtCore.pyqtSlot()(lambda: self.m_windows.remove(mainWindow)))
        self.m_windows.append(mainWindow)
        mainWindow.show()
        return mainWindow

    def windows(self):
        return self.m_windows

    def downloadManagerWidget(self):
        return self.m_downloadManagerWidget

        
