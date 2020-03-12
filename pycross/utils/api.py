# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.api
# User plugin platform to extend pyCrossword functionality based on [Yapsy](http://yapsy.sourceforge.net/).
# @see [example 1](http://yapsy.sourceforge.net/FilteredPluginManager.html), 
# [example 2](https://stackoverflow.com/questions/5333128/yapsy-minimal-example)
from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManager
from PyQt5 import QtWidgets
from .globalvars import *

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## @brief Wrapper class for the application main window (pycross::gui::MainWindow).
# Adds a few convenience methods to call the main app actions, query and set global settings, etc.
# TODO: Must think of a more protected way to expose the main window's methods and members.
class PxAPI:

    ## Constructor takes a single parameter - the instance of pycross::gui::MainWindow (main window).
    def __init__(self, mainwindow):
        ## `pycross::gui::MainWindow` internal pointer to app main window instance
        self.__mainwindow = mainwindow        
        # iterate and add 'safe' methods to this wrapper class
        for objname in dir(self.__mainwindow):
            obj = getattr(self.__mainwindow, objname)
            if callable(obj) and not objname.startswith('_'):
                setattr(self, objname, obj)
        
    ## Triggers an action of the app main window.
    # @param action_name `str` object name or display text of the action to be called
    # @param display_name `bool` True if the display text is passed, otherwise, the action will be
    # located by its object (variable) name
    def trigger_action(self, action_name, display_name=True):
        actn = None
        if not display_name:
            actn = self.get_prop(action_name)
            if not actn or not isinstance(actn, QtWidgets.QAction):
                raise AttributeError(_("MainWindow has no '{}' action!").format(action_name))            
            actn.trigger()
        else:
            for objname in dir(self.__mainwindow):
                actn = self.get_prop(objname)
                if actn and isinstance(actn, QtWidgets.QAction) and (actn.text() == action_name):
                    actn.trigger()
                    break
            else:
                raise AttributeError(_("MainWindow has no '{}' action!").format(action_name))

    ## Sets a global option value.
    # @param option `str` an option search string delimited by 'option_sep', e.g. 'plugins/thirdparty/git/active'
    # @param value value written to the option
    # @param option_sep `str` the option key string delimiter (default = '/')
    # @param apply `bool` if True, the new settings will be applied straightforward
    # @param save_settings `bool` if True, the settings file will be updated (saved)
    def set_option(self, option, value, option_sep='/', apply=True, save_settings=True):
        keys = option.split(option_sep)
        op = self.__mainwindow.options()
        for key in keys:
            op = op[key]
        op = value
        if apply: self.__mainwindow.apply_config(save_settings, False)

    ## Gets a global option value or the whole global settings dictionary.
    # @param option `str`|`None` an option search string delimited by 'option_sep', 
    # e.g. 'plugins/thirdparty/git/active'. If `None`, the whole 
    # guisettings::CWSettings::settings dictionary is returned.
    # @param option_sep `str` the option key string delimiter (default = '/')
    # @returns value of the located option
    # @exception `KeyError` unable to locate option in guisettings::CWSettings::settings
    def get_option(self, option=None, option_sep='/'):       
        op = self.__mainwindow.options()
        if not option: return op
        keys = option.split(option_sep)
        for key in keys:
            op = op[key]
        return op

    ## Getter method for the main window members by their name.
    # @param propname `str` member name (property or method)
    # @param default the default value if the member wasn't found (default = `None`)
    def get_prop(self, propname, default=None):
        return getattr(self.__mainwindow, propname, default)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## @brief Reimplemented PluginManager class to enable plugins' access to the main window.
class PxPluginManager(PluginManager):

    ## Adds 'mainwindow' to the PluginManager default constructor.
    # @param mainwindow `pycross.gui.MainWindow` pointer to the app main window
    # @param categories_filter `dict` categories of plugins to be looked for as well as the way to recognise them
    # @param directories_list `iterable` list of search directories for plugins (relative or absolute paths)
    # @param plugin_info_ext `str` extension of plugin info files (without dot)
    # @param plugin_locator `yapsy::IPluginLocator::IPluginLocator` plugin locator instance
    def __init__(self, mainwindow, categories_filter=None, directories_list=None, plugin_info_ext=None, plugin_locator=None):
        super().__init__(categories_filter, directories_list, plugin_info_ext, plugin_locator)
        ## `PxAPI` wrapper instance for app main window
        #self.__mainwindow = mainwindow
        self.mainwin = PxAPI(mainwindow)

    ## Reimplemented method that creates plugin objects passing 'self' in constructor.
    def instanciateElementWithImportInfo(self, element, element_name, plugin_module_name, candidate_filepath):
        return element(self)

    def call_plugin_method(self, plugin_name, method_name, category='Default', *args, **kwargs):
        plugin = self.getPluginByName(plugin_name, category)
        if plugin is None:
            raise Exception(_("Unable to locate plugin '{}' in category '{}'!").format(plugin_name, category))
        if not plugin.is_activated:
            raise Exception(_("Plugin '{}' is not active. Cannot call method of inactive plugin!").format(plugin_name))
        meth = getattr(plugin.plugin_object, method_name, None)
        if meth is None:
            raise Exception(_("Unable to locate method '{}' in plugin '{}'!").format(method_name, plugin_name))
        return meth(*args, **kwargs)

    def get_plugins_of_category(self, category, active_only=True):
        plugins = []
        settings = self.mainwin.get_option('plugins/custom')
        for pl in settings[category]:
            if not active_only or pl['active']:
                plugin = self.getPluginByName(pl, category)
                if not plugin is None: 
                    plugins.append(plugin)
        print(f"FOUND PLUGINS: {[plugin.name for plugin in plugins]}")
        return plugins

    def get_plugin_methods(self, category, method_name):
        methods = []
        for plugin in self.get_plugins_of_category(category, False):
            m = getattr(plugin.plugin_object, method_name, None)
            if m and callable(m):
                methods.append(m)
        print(f"FOUND METHODS: {methods}")
        return methods

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def before(func):        
    func.wraptype = 'before'
    return func

def after(func):        
    func.wraptype = 'after'
    return func

def replace(func):        
    func.wraptype = 'replace'
    return func  

## @brief Base class for category-specific user plugins (extensions) written in Python.
# This class *must not* be subclassed directly; instead, inherit from `PxPluginGeneral` declared below.
# A plugin must consist of two items in the 'plugins' directory:
#   1. The plugin info file named 'PLUGIN-NAME.pxplugin' that contains the basic plugin info
#   used for locating and loading the plugin.
#   2. The plugin file named 'PLUGIN-NAME.py' (if a single module is enough) or plugin subdirectory
#   named simply 'PLUGIN-NAME', which contains '__init__.py' and an arbitrary number of source files.
# A bare-bones plugin source module would look like this:
# ```python
# from utils.api import *
#
# class MyPlugin(PxPluginBase):
#    pass # do whatever...
# ```
# @see [Yapsy docs](http://yapsy.sourceforge.net/index.html)
class PxPluginBase(IPlugin):

    ## Constructor initializes a pointer to the PxPluginManager object.
    def __init__(self, plugin_manager):
        super().__init__()
        if not isinstance(plugin_manager, PxPluginManager):
            raise TypeError(_("'plugin_manager' agrument must be an instance of PxPluginManager!"))
        self.plugin_manager = plugin_manager

    ## Called at plugin activation.
    def activate(self):
        super().activate()

    ## Called the plugin is disabled.
    def deactivate(self):
        super().deactivate()

    ## Testing method: prints the plugin's class name by default.
    def test(self):
        print(type(self).__name__)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## @brief Base class General user plugins (placed in the 'general' category).
class PxPluginGeneral(PxPluginBase):
    pass

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## Global function: creates and returns an instance of the Plugin Manager.
# @param mainwindow `pycross::gui::MainWindow` pointer to the app main window
# @returns `PxPluginManager` instance of created Plugin Manager
def create_plugin_manager(mainwindow):
    pm = PxPluginManager(mainwindow, directories_list=[PLUGINS_FOLDER], plugin_info_ext=PLUGIN_EXTENSION) 
    pm.setCategoriesFilter({'general': PxPluginGeneral})   
    pm.collectPlugins()
    return pm