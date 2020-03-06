# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.api
from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManager
from PyQt5 import QtGui, QtCore, QtWidgets

# http://yapsy.sourceforge.net/FilteredPluginManager.html
# https://stackoverflow.com/questions/5333128/yapsy-minimal-example
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class PxAPI:

    def __init__(self, mainwindow):
        self.__mainwindow = mainwindow

    def trigger_action(self, action_name, display_name=True):
        actn = None
        if not display_name:
            actn = getattr(self.__mainwindow, action_name, None)
            if not actn:
                raise AttributeError(f"MainWindow has no '{action_name}' member!")
            if isinstance(actn, QtWidgets.QAction):
                actn.trigger()
        else:
            for _, actn in self.__mainwindow.__dict__.items():
                if isinstance(actn, QtWidgets.QAction) and actn.text() == action_name:
                    actn.trigger()
                    return
            raise AttributeError(f"MainWindow has no '{action_name}' action!")
            

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class PxPluginManager(PluginManager):

    def __init__(self, mainwindow, categories_filter=None, directories_list=None, plugin_info_ext=None, plugin_locator=None):
        super().__init__(categories_filter, directories_list, plugin_info_ext, plugin_locator)
        self.mainwin = PxAPI(mainwindow)

    def instanciateElementWithImportInfo(self, element, element_name, plugin_module_name, candidate_filepath):
        return element(self.mainwin)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class PxPluginBase(IPlugin):

    def __init__(self, mainwin):
        self.mainwin = mainwin

    ## Called at plugin activation
    def activate(self):
        super().activate()

    ## Called the plugin is disabled
    def deactivate(self):
        super().deactivate()