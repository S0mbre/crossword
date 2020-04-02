# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.pluginbase
# User plugin platform to extend pyCrossword functionality based on [Yapsy](http://yapsy.sourceforge.net/).
# @see [example 1](http://yapsy.sourceforge.net/FilteredPluginManager.html), 
# [example 2](https://stackoverflow.com/questions/5333128/yapsy-minimal-example)
import PyQt5
from yapsy.IPlugin import IPlugin
from .pluginmanager import PxPluginManager

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## @brief Decorator adds the `wraptype` attribute set to 'before' to a given function.
# Use this decorator for plugin methods that override those of pycross::gui::MainWindow.
# The `before` decorator will make the app first call the plugin method, then the original one.
# For example:
# ```python
# class MyPlugin(PxPluginGeneral):
#     @before
#     def on_act_new(self, checked):
#         print('hey!')
# ```
# With this code (provided that the plugin is active), when the user triggers the `act_new`
# action of the main window, the app will first call the plugin method and print 'hey!', then
# proceed with the original method handler (`on_act_new`). 
#
# Note that when using `before`, the result returned will be that of the original function,
# since it will be called last.
# @see after(), replace()
def before(func):        
    func.wraptype = 'before'
    return func

## @brief Decorator adds the `wraptype` attribute set to 'after' to a given function.
# Contrary to before(), it will call the wrapped plugin method after the original one.
# @see before(), replace()
def after(func):        
    func.wraptype = 'after'
    return func

## @brief Decorator adds the `wraptype` attribute set to 'replace' to a given function.
# Contrary to before() and after(), it will call the wrapped plugin method instead of the original one,
# that is, the original method will not be called at all, and will be replaced by the 
# corresponding plugin method.
# @see before(), after()
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

    ## References a member of the main window class.
    def get_prop(self, propname):
        return getattr(self.plugin_manager.mainwin, propname)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## @brief Base class General user plugins (placed in the 'general' category).
# A bare-bones plugin source module would look like this:
# ```python
# from pycross.utils.pluginbase import *
#
# class MyPlugin(PxPluginGeneral):
#    pass # do whatever...
# ```
class PxPluginGeneral(PxPluginBase):
    pass