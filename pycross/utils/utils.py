# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.utils
# This package is a general container for utility functions and classes used
# across the entire application. The utilities include file operations, OS and system
# queries, multithreading and some Qt GUI methods.
import sys, os, subprocess, traceback, uuid
import tempfile, platform, re, json, shutil, inspect, builtins
import jedi
from datetime import datetime, time
from functools import wraps
from .globalvars import *
from PyQt5 import QtGui, QtCore, QtWidgets

# ---------------------------- COMMON ---------------------------- #

## Checks if a given object is iterable (i.e. contains elements like an array).
# @param obj the object to check
# @returns `bool` True if the object is iterable (array-like) and False otherwise
def is_iterable(obj):
    if isinstance(obj, str): return False
    try:
        _ = iter(obj)
        return True
    except:
        return False

## Gets the current OS (platform) name.
# @returns `str` platform name, e.g. 'Windows' or 'Linux'
def getosname():
    return platform.system()

## Generates a random UUID (alphanumeric string).
# @returns `str` UUID compliant to RFC 4122
# @see [Python docs](https://docs.python.org/3.8/library/uuid.html)
def generate_uuid():
    return uuid.uuid4().hex

## Copies a file into another location.
# @param path_from `str` the original file to copy
# @param path_to `str` the new file path or directory to copy the file to
# @returns `str` the path to the newly created (copied) file
def copy_file(path_from, path_to):
    return shutil.copy(path_from, path_to)

## Iterates the files and folder in a given folder, performing some operations
# on the found files / folders.
# @param root_path `str` the starting (root) directory path to start searching from
# @param abs_path `bool` if `True` (default), the given root path will be made absolute
# (relative to the current working directory); if `False`, it will be left as it is
# @param recurse `bool` whether to recurse into the found subdirectories (default = `True`)
# @param dir_process_function `callable` callback function for found subdirectories.
# The callback takes a single argument - the full directory path.
# @param file_process_function `callable` callback function for found files.
# The callback takes a single argument - the full file path.
# @param file_types `iterable` collection of file extensions (without the leading dot)
# that will be respected when a file is found; if `None` (default), no file type
# filtering will be done.
def walk_dir(root_path, abs_path=True, recurse=True, dir_process_function=None,
             file_process_function=None, file_types=None):
    if abs_path:
        root_path = os.path.abspath(root_path)
    for (d, dirs, files) in os.walk(root_path):
        if dir_process_function:
            for d_ in dirs:
                dir_process_function(os.path.join(d, d_))
        if file_process_function:
            for f in files:
                ext = os.path.splitext(f)[1][1:].lower()
                if (not file_types) or (ext in file_types):
                    file_process_function(os.path.join(d, f))
        if not recurse: break

## Runs an executable and optionally returns the result.
# @param args `list` | `str` arguments passed to the executable (a list of args or a single string)
# @param external `bool` whether the executable must be called as an external (detached) process;
# this basically means that the process will be created _asynchronously_, not blocking the
# main application process to wait for the result; if `False` (default), the executable
# will be called _synchronously_, waiting for the result and blocking the main process
# @param capture_output `bool` whether the console output of the executable must be captured
# @param stdout `file-like` file / stream to channel the STDOUT and STDERR streams to;
# the default value is subprocess.PIPE, meaning that the output will be returned by the method
# @param encoding `str` the string encoding to use for the executable's output (default = UTF8)
# @param timeout `float` number of seconds to wait until timeout
# (default = `None`, i.e. wait infinitely)
# @param shell `bool` whether the executable must be called via the system shell (default = `False`)
# @param kwargs `keyword arguments` additional keyword arguments passed to subprocess.Popen
# @returns `subprocess.CompletedProcess` completed process results, see [Python docs](https://docs.python.org/3.8/library/subprocess.html?highlight=subprocess#subprocess.CompletedProcess)
def run_exe(args, external=False, capture_output=True, stdout=subprocess.PIPE, encoding=ENCODING,
            timeout=None, shell=False, **kwargs):
    try:
        osname = platform.system()
        if external:
            if osname == 'Windows':
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                return subprocess.Popen(args,
                    creationflags=creationflags,
                    stdout=stdout if capture_output else None,
                    stderr=subprocess.STDOUT if capture_output else None,
                    encoding=encoding, shell=shell, **kwargs)
            else:
                return subprocess.Popen('nohup ' + (args if isinstance(args, str) else ' '.join(args)),
                    stdout=stdout if capture_output else None,
                    stderr=subprocess.STDOUT if capture_output else None,
                    encoding=encoding, shell=shell, preexec_fn=os.setpgrp,
                    **kwargs)
        else:
            return subprocess.run(args,
                capture_output=capture_output,
                encoding=encoding,
                timeout=timeout, shell=shell, **kwargs)
    except Exception as err:
        traceback.print_exc(limit=None)
        raise

## Converts a Python `datetime` object to a string.
# @param dt `datetime` Python datetime object representing a date and/or time;
# if `None` (default), the current date and time will be taken
# @param strformat `str` format string compliant to the [Python datetime formatting](https://docs.python.org/3.8/library/datetime.html?highlight=datetime#strftime-strptime-behavior)
# @returns `str` string representation of the date / time
def datetime_to_str(dt=None, strformat='%Y-%m-%d %H-%M-%S'):
    if dt is None: dt = datetime.now()
    return dt.strftime(strformat)

## Converts a timestamp (Unix time) to a string.
# @param ts `float` timestamp, i.e. number of seconds since epoch (Unix time)
# if `None` (default), the current timestamp will be taken
# @param strformat `str` format string compliant to the [Python datetime formatting](https://docs.python.org/3.8/library/datetime.html?highlight=datetime#strftime-strptime-behavior)
# @returns `str` string representation of the timestamp
def timestamp_to_str(ts=None, strformat='%Y-%m-%d %H-%M-%S'):
    if ts is None: ts = time.time()
    return datetime_to_str(datetime.fromtimestamp(ts), strformat)

## Converts a string to a Python `datetime` object.
# @param text `str` datetime string to convert
# @param strformat `str` format string compliant to the [Python datetime formatting](https://docs.python.org/3.8/library/datetime.html?highlight=datetime#strftime-strptime-behavior)
# @returns `datetime` Python datetime object
def str_to_datetime(text, strformat='%Y-%m-%d %H-%M-%S'):
    return datetime.strptime(text, strformat)

## Converts a string to a timestamp (Unix time).
# @param text `str` datetime string to convert
# @param strformat `str` format string compliant to the [Python datetime formatting](https://docs.python.org/3.8/library/datetime.html?highlight=datetime#strftime-strptime-behavior)
# @returns `float` timestamp, i.e. number of seconds since epoch (Unix time)
def str_to_timestamp(text, strformat='%Y-%m-%d %H-%M-%S'):
    return str_to_datetime(text, strformat).timestamp()

## Gets the path to the Temp directory on the system.
# @returns `str` full path to the system Temp directory
def get_tempdir():
    return os.path.abspath(tempfile.gettempdir())

## Returns a human-formatted file size as a string,
# e.g. "1Mi" (1 megabyte), "15GBi" (15 gigabytes) etc.
# @param value `float` the file size value to convert
# @param suffix `str` the size suffix, default = 'B' (bytes)
# @returns `str` string representation of the file size
def bytes_human(value, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(value) < 1024.0:
            return f"{value:3.1f}{unit}{suffix}"
        value /= 1024.0
    return f"{value:.1f}Y{suffix}"

## Restarts this app.
# @param closefunction `callable` function to close down the app (e.g. gui::MainWindow::on_act_exit)
def restart_app(closefunction):
    osname = platform.system()
    run_exe('pythonw cwordg.py' if osname == 'Windows' else 'python3 ./cwordg.py', external=True, capture_output=False, shell=True)
    closefunction()

## Checks if the given file type associations are registered in the OS.
# @param filetypes `iterable` collection of file extensions to check (without leading dot)
# @returns `bool` `True` if the file types are associated with this app, `False` otherwise
# TODO: implement for OSX (Darwin)
def file_types_registered(filetypes=('xpf', 'ipuz', 'pxjson')):
    osname = platform.system()
    if osname == 'Windows':
        import winreg
        try:
            root = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            hKey = winreg.OpenKeyEx(root, f"Software\\Classes\\{APP_NAME}\\shell\\open\\command")
            if winreg.QueryValue(hKey, '') != f'"{make_abspath(sys.executable)}" "{make_abspath(sys.argv[0])}" -o "%1"':
                winreg.CloseKey(hKey)
                return False
            winreg.CloseKey(hKey)
            for filetype in filetypes:
                ftype = ('.' + filetype.lower()) if not filetype.startswith('.') else filetype.lower()
                hKey = winreg.OpenKeyEx(root, f"Software\\Classes\\{ftype}")
                if winreg.QueryValue(hKey, '') != APP_NAME:
                    winreg.CloseKey(hKey)
                    return False
                winreg.CloseKey(hKey)
            return True
        except:
            return False

    elif osname == 'Linux':
        appname = APP_NAME.lower()
        res = run_exe(f'xdg-mime query default x-scheme-handler/{appname}', False, True, shell=True)
        return os.path.isfile(os.path.expanduser(LINUX_APP_PATH)) and \
                os.path.isfile(os.path.expanduser(LINUX_MIME_XML)) and \
                res.returncode == 0 and \
                res.stdout.strip() == f"{appname}.desktop"

    elif osname == 'Darwin':
        # see https://stackoverflow.com/a/2976711
        return False

    return False

## @brief Registers file associations in the current OS for the given file types and application.
# After a call of this method succeeds, files with the indicated extensions can be
# launched directly with the 'open' verb, that is, by double-clicking or hitting Enter on them
# in the system file browser. These files will be opened with *pycrossword* thanks to
# the system-wide permanent file associations. The mechanism uses the System Registry on
# Windows and MIME types on Linux.
# @param filetypes `iterable` collection of file extensions to check (without leading dot)
# @param register `bool` set `True` to register the associations, `False` to unregister
# TODO: implement for OSX (Darwin)
def register_file_types(filetypes=('xpf', 'ipuz', 'pxjson'), register=True):
    if not filetypes: return False
    osname = platform.system()
    if osname == 'Windows':
        import winreg
        try:
            root = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            # app entry
            if register:
                hKey = winreg.CreateKey(root, f"Software\\Classes\\{APP_NAME}\\shell\\open\\command")
                winreg.SetValueEx(hKey, '', 0, winreg.REG_SZ, f'"{make_abspath(sys.executable)}" "{make_abspath(sys.argv[0])}" -o "%1"')
                winreg.CloseKey(hKey)
                hKey = winreg.CreateKey(root, f"Software\\Classes\\{APP_NAME}\\DefaultIcon")
                winreg.SetValueEx(hKey, '', 0, winreg.REG_SZ, f"{ICONFOLDER}\\main.ico")
                winreg.CloseKey(hKey)
            else:
                try:
                    hKey = winreg.OpenKeyEx(root, f"Software\\Classes\\{APP_NAME}", 0, winreg.KEY_ALL_ACCESS)
                    winreg.DeleteKey(hKey, 'DefaultIcon')
                except:
                    pass
                try:
                    hKey = winreg.OpenKeyEx(root, f"Software\\Classes\\{APP_NAME}\\shell\\open", 0, winreg.KEY_ALL_ACCESS)
                    winreg.DeleteKey(hKey, 'command')
                    hKey = winreg.OpenKeyEx(root, f"Software\\Classes\\{APP_NAME}\\shell", 0, winreg.KEY_ALL_ACCESS)
                    winreg.DeleteKey(hKey, 'open')
                    hKey = winreg.OpenKeyEx(root, f"Software\\Classes\\{APP_NAME}", 0, winreg.KEY_ALL_ACCESS)
                    winreg.DeleteKey(hKey, 'shell')
                    hKey = winreg.OpenKeyEx(root, f"Software\\Classes", 0, winreg.KEY_ALL_ACCESS)
                    winreg.DeleteKey(hKey, APP_NAME)
                except:
                    pass
            # ext entries
            for filetype in filetypes:
                ftype = ('.' + filetype.lower()) if not filetype.startswith('.') else filetype.lower()
                if register:
                    hKey = winreg.CreateKey(root, f"Software\\Classes\\{ftype}")
                    winreg.SetValueEx(hKey, '', 0, winreg.REG_SZ, APP_NAME)
                    winreg.CloseKey(hKey)
                else:
                    try:
                        hKey = winreg.OpenKeyEx(root, f"Software\\Classes", 0, winreg.KEY_ALL_ACCESS)
                        winreg.DeleteKey(hKey, ftype)
                    except:
                        continue

            winreg.CloseKey(root)

            # fast update file icons
            run_exe('ie4uinit.exe -show', False, False, shell=True)
            return True

        except Exception as err:
            print(str(err))
            return False

    elif osname == 'Linux':
        # example at https://askubuntu.com/questions/108925/how-to-tell-chrome-what-to-do-with-a-magnet-link/133693#133693
        appname = APP_NAME.lower()
        if register:
            # create MIME app in '~/.local/share/applications'
            with open(os.path.expanduser(LINUX_APP_PATH), 'w') as f:
                f.write(LINUX_MIME_APP.format(f'python3 "{make_abspath(sys.argv[0])}" -o',
                        appname, f"{APP_NAME} launcher"))
            # add row to '~/.local/share/applications/mimeapps.list'
            res = run_exe(f"xdg-mime default {appname}.desktop x-scheme-handler/{appname}", shell=True)
            if res.returncode: return False
            # check successful assignment
            res = run_exe(f'xdg-mime query default x-scheme-handler/{appname}', shell=True)
            if res.returncode or res.stdout.strip() != f"{appname}.desktop":
                # failed to add association
                return False
            # install MIME types
            ftypes = []
            for filetype in filetypes:
                ftype = ('.' + filetype.lower()) if not filetype.startswith('.') else filetype.lower()
                ftypes.append(f'<glob pattern="*{ftype}"/>')
            with open(os.path.expanduser(LINUX_MIME_XML), 'w') as f:
                f.write(LINUX_MIME_TYPES.format(f"x-scheme-handler/{appname}",
                        f"{APP_NAME} settings and cw files", '\n    '.join(ftypes)))
            res = run_exe(f'xdg-mime install {LINUX_MIME_XML}', shell=True)
            if res.returncode: return False
            # install icon
            res = run_exe(f'xdg-icon-resource install --context mimetypes --size 64 {ICONFOLDER}/main.png x-scheme-handler-{appname}', shell=True)
            return not res.returncode and not res.stdout.strip()

        else:
            try:
                # uninstall icon
                run_exe(f'xdg-icon-resource uninstall --size 64 {ICONFOLDER}/main', capture_output=False, shell=True)
                # uninstall MIME types
                run_exe(f'xdg-mime uninstall {LINUX_MIME_XML}', capture_output=False, shell=True)
                # delete MIME XML
                run_exe(f'rm {LINUX_MIME_XML}', capture_output=False, shell=True)
                # delete MIME app
                run_exe(f'rm {LINUX_APP_PATH}', capture_output=False, shell=True)
                return True
            except:
                return False

    elif osname == 'Darwin':
        # see https://stackoverflow.com/a/2976711
        return False

    # some oddball os...
    return False

## @brief Plugin decorator for custom plugins.
# Searches the Plugin manager for methods (function) in the given category
# having the same name as the wrapped method and calls the plugin methods in
# the order as stored in the Plugin manager for that category.
# Plugin methods can be called:
#   * _before_ the original method
#   * _after_ the original method
#   * _instead of_ the original method,
# depending on the `wraptype` attribute of the plugin method ('before', 'after' or 'replace').
# @param category `str` name of the plugin category (e.g. 'general')
# @see utils.pluginmanager, utils.pluginbase
def pluggable(category):
    def plugin_general(func):
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            plugin_methods = self.plugin_mgr.get_plugin_methods(category, func.__name__)
            cnt = len(plugin_methods)
            for i in range(cnt):
                wraptype = getattr(plugin_methods[i], 'wraptype', None)
                #if DEBUGGING: print(f"WRAP TYPE OF FUNC '{func.__name__}' is '{wraptype}'")
                res = None
                if wraptype == 'before':
                    try:
                        plugin_methods[i](*args, **kwargs)
                    except:
                        traceback.print_exc(limit=None)
                    res = func(self, *args, **kwargs)
                elif wraptype == 'after':
                    res = func(self, *args, **kwargs)
                    try:
                        res = plugin_methods[i](*args, **kwargs)
                    except:
                        traceback.print_exc(limit=None)
                elif wraptype == 'replace':
                    try:
                        plugin_methods[i](*args, **kwargs)
                    except:
                        traceback.print_exc(limit=None)
                        res = None
                else:
                    continue
                if i == (cnt - 1):
                    return res
            return func(self, *args, **kwargs)
        return wrapped
    return plugin_general

## @brief Collects the names and signatures of wrapped methods from a class instance.
# Used in this app to generate the list of pycross::gui::MainWindow methods
# that can be overridden in user plugin classes.
# @param parent_object `Python object` object that defines wrapped methods.
# @warning Only decorated methods will be retrieved by this function! This is done
# on purpose so that the object may expose only specific methods for plugins.
# @param indent `str` indentation for method docs, if present
# @returns `list of str` list of wrapped method signatures, e.g.:
# ```
# ['def foo(arg1, arg2):',
#  'def bar():',
#  'def commentedfunc():\n    This is comment']
# ```
def collect_pluggables(parent_object, indent='    '):
    methods = []
    for itemname in dir(parent_object):
        if itemname.startswith('_'): continue
        obj = getattr(parent_object, itemname, None)
        obj = getattr(obj, '__wrapped__', None)
        if not obj or not callable(obj): continue
        m = 'def ' + itemname
        try:
            sig = str(inspect.signature(obj))
            if sig: m += sig + ':'
        except:
            m += '():'
        comments = inspect.getcomments(obj)
        if comments:
            for row in [comment.strip().replace('##', '#') for comment in comments.split('\n')]:
                m += '\n' + indent + row
        else:
            if not m.endswith('\n'): m += '\n'
            m += indent
        m += 'return None'
        methods.append(m)
    methods.sort()
    return methods

## Collects the names and signatures of builtin Python functions.
# @returns `list of str` list of names and signatures, e.g. 'sort(iterable, key)'
# @see collect_pluggables()
def get_builtins():
    res = []
    for elname in dir(builtins):
        obj = getattr(builtins, elname)
        if callable(obj):
            try:
                res.append(f"{elname}{str(inspect.signature(obj))}")
            except:
                res.append(elname)
        else:
            res.append(elname)
    return res

## @brief Retrieves the names of all variables in the given Python script.
# This function collects all variables (builtin, global, local) that the given
# script references or creates using the [Jedi autocompletion package](https://jedi.readthedocs.io/en/latest/).
# The resulting list of names can be then used for autocompletion. This app uses
# this function in the user plugin script editor.
# @param script `str` source script in Python
# @returns `list of str` list of referenced variables (functions also have signatures,
# i.e. arguments in brackets)
def get_script_members(script):
    #jscript = jedi.Script(script, _project=jedi.api.Project(os.path.abspath('utils')))
    jscript = jedi.Script(script, sys_path=sys.path + [os.path.abspath(os.path.dirname(__file__))])
    res = get_builtins()
    for d in jscript.get_names(all_scopes=True, definitions=True, references=True):
        if d.type == 'function':
            for ds in d.get_signatures():
                res.append(ds.to_string().replace('(self)', '()').replace('(self, ', '('))
        else:
            res.append(d.name)
    return res

# ---------------------------- GUI ---------------------------- #

## Customized thread class (based on QThread) that adds
# progress, error etc. signals and mutex locking to avoid thread racing.
class QThreadStump(QtCore.QThread):

    ## Error signal (args are: instance of this thread and the error message)
    sig_error = QtCore.pyqtSignal(QtCore.QThread, str)

    ## Constructor.
    # @param default_priority `int` thread default priority (default = normal)
    # @param on_start `callable` callback function called before the main
    # operation is executed (callback has no args or returned result)
    # @param on_finish `callable` callback function called after the main
    # operation completes (callback has no args or returned result)
    # @param on_run `callable` callback function for the main
    # operation (callback has no args or returned result)
    # @param on_error `callable` callback function to handle exceptions
    # raised during the thread operation (see QThreadStump::sig_error)
    # @param start_signal `QtCore.pyqtSignal` signal that can be connected to
    # the `start` slot (if not `None`)
    # @param stop_signal `QtCore.pyqtSignal` signal that can be connected to
    # the `terminate` slot (if not `None`)
    # @param free_on_finish `bool` whether the thread instance will be deleted
    # from memory after it completes its operation (default = `False`)
    # @param start_now `bool` whether to start the thread upon creation (default = `False`)
    # @param can_terminate `bool` whether the thread can be terminated (default = `True`)
    def __init__(self, default_priority=QtCore.QThread.NormalPriority,
                 on_start=None, on_finish=None, on_run=None, on_error=None,
                 start_signal=None, stop_signal=None,
                 free_on_finish=False, start_now=False, can_terminate=True):
        super().__init__()
        self.init(default_priority, on_start, on_finish, on_run, on_error,
                  start_signal, stop_signal, free_on_finish, can_terminate)
        if start_now: self.start()

    ## Destructor: waits for the thread to complete.
    def __del__(self):
        try:
            self.wait()
        except:
            pass

    ## Initializes signals binding them to callbacks and other members.
    # @param default_priority `int` thread default priority (default = normal)
    # @param on_start `callable` callback function called before the main
    # operation is executed (callback has no args or returned result)
    # @param on_finish `callable` callback function called after the main
    # operation completes (callback has no args or returned result)
    # @param on_run `callable` callback function for the main
    # operation (callback has no args or returned result)
    # @param on_error `callable` callback function to handle exceptions
    # raised during the thread operation (see QThreadStump::sig_error)
    # @param start_signal `QtCore.pyqtSignal` signal that can be connected to
    # the `start` slot (if not `None`)
    # @param stop_signal `QtCore.pyqtSignal` signal that can be connected to
    # the `terminate` slot (if not `None`)
    # @param free_on_finish `bool` whether the thread instance will be deleted
    # from memory after it completes its operation (default = `False`)
    # @param start_now `bool` whether to start the thread upon creation (default = `False`)
    # @param can_terminate `bool` whether the thread can be terminated (default = `True`)
    def init(self, default_priority=QtCore.QThread.NormalPriority,
             on_start=None, on_finish=None, on_run=None, on_error=None,
             start_signal=None, stop_signal=None,
             free_on_finish=False, can_terminate=True):
        try:
            self.started.disconnect()
            self.finished.disconnect()
            self.sig_error.disconnect()
        except:
            pass

        self.setTerminationEnabled(can_terminate)
        if on_start: self.started.connect(on_start)
        if on_finish: self.finished.connect(on_finish)
        if free_on_finish: self.finished.connect(self.deleteLater)
        if start_signal: start_signal.connect(self.start)
        if stop_signal: stop_signal.connect(self.terminate)
        if on_error: self.sig_error.connect(on_error)
        ## `int` thread default priority (default = normal)
        self.default_priority = default_priority if default_priority != QtCore.QThread.InheritPriority else QtCore.QThread.NormalPriority
        ## `callable` callback function for the main operation
        self.on_run = on_run
        ## `QtCore.QMutex` mutex lock used by QThreadStump::lock() and QThreadStump::unlock()
        self.mutex = QtCore.QMutex()

    ## Locks the internal mutex to preclude data racing.
    def lock(self):
        self.mutex.lock()

    ## Releases the mutex lock.
    def unlock(self):
        self.mutex.unlock()

    ## Executes the worker function pointed to by QThreadStump::on_run.
    def run(self):
        self.setPriority(self.default_priority)
        if self.on_run and not self.isInterruptionRequested():
            try:
                self.on_run()
            except Exception as err:
                traceback.print_exc(limit=None)
                self.sig_error.emit(self, str(err))

# ------------------------------------------------------------------------ #

class TaskSignals(QtCore.QObject):

    sigstart = QtCore.pyqtSignal(int)
    sigfinish = QtCore.pyqtSignal(int, 'PyQt_PyObject')
    sigerror = QtCore.pyqtSignal(int, tuple)
    sigprogress = QtCore.pyqtSignal(int, 'PyQt_PyObject')

class Task(QtCore.QRunnable):

    def __init__(self, on_run, run_args=(), run_kwargs={}, id=0):
        super().__init__()
        #self.setAutoDelete(False)
        self.signals = TaskSignals()
        self.id = id
        self.on_run = on_run
        self.run_args = run_args
        self.run_kwargs = run_kwargs

    def run(self):
        self.signals.sigstart.emit(self.id)
        if not self.on_run: return
        res = None
        try:
            res = self.on_run(*self.run_args, **self.run_kwargs)
        except Exception as err:
            #traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sigerror.emit(self.id, (exctype, value, str(err)))
        except:
            #traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sigerror.emit(self.id, (exctype, value, traceback.format_exc()))
        else:
            self.signals.sigfinish.emit(self.id, res)

# ------------------------------------------------------------------------ #

## Constructs a `QtGui.QFont` object from given font parameters.
# @param family `str` font familty name, e.g. 'Arial'
# @param size `int` font size in points or pixels (default = -1: default size)
# @param weight `int` font weight (default = -1: default size).
# The following constants can be used:
#   * QFont::Thin	0
#   * QFont::ExtraLight	12
#   * QFont::Light	25
#   * QFont::Normal	50
#   * QFont::Medium	57
#   * QFont::DemiBold	63
#   * QFont::Bold	75
#   * QFont::ExtraBold	81
#   * QFont::Black	87
# @param italic `bool` `True` to set the italic style
# @param font_unit `str` font size unit: 'pt' = points (default), 'px' = pixels
# @returns `QtGui.QFont` created font object
def make_font(family, size=-1, weight=-1, italic=False, font_unit='pt'):
    font = QtGui.QFont(family)
    if font_unit == 'pt':
        font.setPointSize(size)
    else:
        font.setPixelSize(size)
    font.setWeight(weight)
    font.setItalic(italic)
    #print(f"make_font: font_unit={font_unit}, family={font.family()}, size(pt) = {font.pointSize()}, size(px)={font.pixelSize()}")
    return font

## Button names, their localized names and roles used in MsgBox() function
MSGBOX_BUTTONS = {'ok': (_('OK'), QtWidgets.QMessageBox.AcceptRole), 'yes': (_('Yes'), QtWidgets.QMessageBox.YesRole),
                  'no': (_('No'), QtWidgets.QMessageBox.NoRole), 'cancel': (_('Cancel'), QtWidgets.QMessageBox.RejectRole),
                  'yesall': (_('Yes to All'), QtWidgets.QMessageBox.YesRole), 'noall': (_('No to All'), QtWidgets.QMessageBox.NoRole),
                  'apply': (_('Apply'), QtWidgets.QMessageBox.ApplyRole), 'reset': (_('Reset'), QtWidgets.QMessageBox.ResetRole),
                  'open': (_('Open'), QtWidgets.QMessageBox.AcceptRole), 'save': (_('Save'), QtWidgets.QMessageBox.AcceptRole),
                  'close': (_('Close'), QtWidgets.QMessageBox.RejectRole), 'discard': (_('Discard'), QtWidgets.QMessageBox.DestructiveRole),
                  'restoredefaults': (_('Restore Defaults'), QtWidgets.QMessageBox.ResetRole), 'help': (_('Help'), QtWidgets.QMessageBox.HelpRole),
                  'saveall': (_('Save All'), QtWidgets.QMessageBox.AcceptRole), 'abort': (_('Abort'), QtWidgets.QMessageBox.RejectRole),
                  'retry': (_('Retry'), QtWidgets.QMessageBox.AcceptRole), 'ignore': (_('Ignore'), QtWidgets.QMessageBox.AcceptRole)}
## Types of MsgBox dialogs used in MsgBox() function
MSGBOX_TYPES = {'error': (QtWidgets.QMessageBox.Critical, ['ok']), 'warn': (QtWidgets.QMessageBox.Warning, ['ok']), 'ask': (QtWidgets.QMessageBox.Question, ['yes', 'no']),
                'info': (QtWidgets.QMessageBox.Information, ['ok']), '-': (QtWidgets.QMessageBox.NoIcon, ['ok'])}

## Displays a GUI message dialog and returns the user's reply.
# @param what `str` message dialog text (body)
# @param parent `QtWidgets.QWidget` parent widget for the dialog or `None` if no parent is required
# @param title `str` dialog title (caption)
# @param msgtype `str` dialog type affecting the icon: 'error', 'info', 'ask', 'warn' or '-' (no icon)
# @param btn `list of str` list of button names to be placed in the dialog -- see MSGBOX_BUTTONS
# @param detailedText `str` additional text below the dialog text to be used for extra explanations, notes etc.
# @param infoText `str` additional text below the dialog text to be used for extra explanations, notes etc.
# @param execnow `bool` if `True` (default), the dialog will be executed (displayed) on creation
# @returns `str` | `QtWidgets.QMessageBox` user's reply (if `execnow` is `True`) as
# the name of the clicked button or an empty string if cancelled; or the dialog object
# if `execnow` is `False`
def MsgBox(what, parent=None, title='pyCross', msgtype='info', btn=None,
           detailedText='', infoText='', execnow=True):
    msgtype = MSGBOX_TYPES.get(msgtype, MSGBOX_TYPES['-'])
    msgbox = QtWidgets.QMessageBox(parent)
    msgbox.setIcon(msgtype[0])
    msgbox.setWindowTitle(title)
    msgbox.setText(what)
    msgbox.setDetailedText(detailedText)
    msgbox.setInformativeText(infoText)
    if not btn: btn = msgtype[1]
    for bt in btn:
        if bt in MSGBOX_BUTTONS:
            msgbox.addButton(MSGBOX_BUTTONS[bt][0], MSGBOX_BUTTONS[bt][1])
    if execnow:
        msgbox.exec()
        clk = msgbox.clickedButton()
        if not clk: return ''
        clktxt = clk.text()
        for bt in MSGBOX_BUTTONS:
            if MSGBOX_BUTTONS[bt][0] == clktxt:
                return bt
        return ''
    else:
        return msgbox

## Displays a GUI user input dialog and returns the user's input.
# @param dialogtype `str` input result type; can be any of:
#   * 'text' (default) usual one-line text string
#   * 'multitext' multi-line text string
#   * 'int' integer numeric value
#   * 'float' floating-point numeric value
#   * 'item' an item string chosen from a drop-down menu
# @param parent `QtWidgets.QWidget` parent widget for the dialog or `None` if no parent is required
# @param title `str` dialog title (caption)
# @param label `str` optional label for the input field
# @param value `str` | `int` | `float` default value set in the input field (default = `None`: empty field)
# @param textmode `str` text masking; any of:
#   * 'normal' (default) no text masking
#   * 'noecho' no text will appear in the input field when typed
#   * 'password' masked text (with bullet placeholders)
#   * 'passwordonedit' masked text when editing, otherwise normal
# @param valrange `2-tuple` min/max range of the numerical value, e.g. (1, 100)
# @param decimals `int` number of decimals after the floating point, default = 1
# @param step `int` step value for the int / float spinbox, default = 1
# @param comboeditable `bool` if `True`, the item selection combobox for the 'item' mode
# will be editable, otherwise non-editable
# @param comboitems `list` list of items to choose from in the 'item' input mode
# @returns `str` | `int` | `float` the user's input
def UserInput(dialogtype='text', parent=None, title='pyCross', label='', value=None, textmode='normal',
              valrange=None, decimals=1, step=1, comboeditable=True, comboitems=[]):
    modes = {'normal': QtWidgets.QLineEdit.Normal, 'noecho': QtWidgets.QLineEdit.NoEcho,
             'password': QtWidgets.QLineEdit.Password, 'passwordonedit': QtWidgets.QLineEdit.PasswordEchoOnEdit}
    if dialogtype == 'text':
        mode = modes[textmode]
        return QtWidgets.QInputDialog.getText(parent, title, label,
                echo=mode, text=str(value) if value else '')
    elif dialogtype == 'multitext':
        return QtWidgets.QInputDialog.getMultiLineText(parent, title, label,
                text=str(value) if value else '')
    elif dialogtype == 'int':
        return QtWidgets.QInputDialog.getInt(parent, title, label,
                value=int(value) if value else 0, min=valrange[0] if valrange else -2147483647,
                max=valrange[1] if valrange else 2147483647, step=step)
    elif dialogtype == 'float':
        return QtWidgets.QInputDialog.getDouble(parent, title, label,
                value=float(value) if value else 0, min=valrange[0] if valrange else -2147483647,
                max=valrange[1] if valrange else 2147483647, decimals=decimals)
    elif dialogtype == 'item':
        return QtWidgets.QInputDialog.getMultiLineText(parent, title, label,
                comboitems, current=value if value else 0, editable=comboeditable)

## Copies a given value / object to the system clipboard.
# @param value `str` | `QtCore.QMimeData` | `QtGui.QPixmap` | `QtGui.QImage` value to copy
# @param valtype `str` type of the value, any of:
#   * 'text' (default): text string
#   * 'mime': MIME data as a `QtCore.QMimeData` object
#   * 'pixmap': bitmap (pixmap) as a `QtGui.QPixmap` object
#   * 'image': image as a `QtGui.QImage` object
def clipboard_copy(value, valtype='text'):
    clip = QtWidgets.qApp.clipboard()
    if valtype == 'text':
        clip.setText(value)
    elif valtype == 'mime':
        clip.setMimeData(value)
    elif valtype == 'pixmap':
        clip.setPixmap(value)
    elif valtype == 'image':
        clip.setImage(value)

## Retrieves the contents of the system clipboard.
# @param valtype `str` type of the value, any of:
#   * 'text' (default): text string
#   * 'mime': MIME data as a `QtCore.QMimeData` object
#   * 'pixmap': bitmap (pixmap) as a `QtGui.QPixmap` object
#   * 'image': image as a `QtGui.QImage` object
# @returns `str` | `QtCore.QMimeData` | `QtGui.QPixmap` | `QtGui.QImage` the clipboard contents as a single object
def clipboard_get(valtype='text'):
    clip = QtWidgets.qApp.clipboard()
    if valtype == 'text':
        return clip.text()
    elif valtype == 'mime':
        return clip.mimeData()
    elif valtype == 'pixmap':
        return clip.pixmap()
    elif valtype == 'image':
        return clip.image()
    return None

## Clears the system clipboard.
def clipboard_clear():
    QtWidgets.qApp.clipboard().clear()

## @brief Returns a Qt widget's [stylesheet](https://doc.qt.io/qt-5/stylesheet-reference.html)
# as a Python dictionary.
# This is the reverse of stylesheet_dump().
# @param style `str` the widget style sheet that is retrieved with the styleSheet() method
# of `QtWidgets.QWidget` derived classes
# @param dequote `bool` whether to dequote (strip quotation symbols from) values
# found in the style sheet (default = `True`)
# @param strip_sz `bool` whether to drop size units like 'pt' or 'px' and return just
# the numerical values (default = `True`)
# @param units `iterable` unit names that can be stripped with the `strip_sz` option
# @returns `dict` Python dictionary with style sheet attributes, e.g.
# `{'font-family': 'Arial', 'font-size': 12, ...}`
# @see stylesheet_dump()
def stylesheet_load(style, dequote=True, strip_sz=True, units=('pt', 'px')):
    ls_style = [s.strip() for s in style.split(';')]
    d = {}
    def unq(s):
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]
        return s
    for pair in ls_style:
        st = [s.strip() for s in pair.split(':')]
        if len(st) != 2: continue
        if dequote: st[1] = unq(st[1])
        if strip_sz:
            for unit in units:
                if st[1].endswith(unit):
                    st[1] = int(st[1][:-2].strip())
                    break
        if st[1] == 'true': st[1] = True
        if st[1] == 'false': st[1] = False
        d[st[0]] = st[1]
    #print(f"_stylesheet_load: {d}")
    return d

## @brief Serializes a Python dictionary representing a widget's style sheet into a string.
# This is the reverse of stylesheet_load(). The resulting string is compatible
# with the [Qt style sheets](https://doc.qt.io/qt-5/stylesheet-reference.html).
# @param quoted_keys `iterable` attribute names whose values must be quoted
# @param add_units `dict` attribute names and their corresponding size units that
# will be appended to numerical values of those attributes
# @returns `str` Qt5-compatible style sheet string
# @see stylesheet_load()
def stylesheet_dump(d, quoted_keys=('font-family',), add_units={'font-size': 'pt', 'border': 'px', 'border-width': 'px'}):
    l = []
    for key in d:
        val = d[key]
        for qk in quoted_keys:
            if key == qk and not (val.startswith('"') and val.endswith('"')):
                val = f'"{val}"'
                break
        unit = add_units.get(key, '')
        if unit: val = f'{val}{unit}'
        if isinstance(val, bool): val = str(val).lower()
        l.append(f'{key}: {str(val)}')
    s = '; '.join(l)
    #print(f"_stylesheet_dump: {s}")
    return s

## Converts CSS font weight constants to Qt font weight constants.
# @param weight `int` font weight in CSS style sheet
# @param default `int` default Qt font weight used on failure to get the
# corresponding Qt weight value
# @returns `int` Qt font weight constant, such as `QtGui.QFont.Normal` or `QtGui.QFont.Bold`
# @see globalvars::FONT_WEIGHTS, font_weight_qt2css()
def font_weight_css2qt(weight, default=0):
    if weight == 'normal':
        weight = QtGui.QFont.Normal
    elif weight == 'bold':
        weight = QtGui.QFont.Bold
    else:
        weight = FONT_WEIGHTS.get(int(weight), default)
    return weight

## Converts Qt font weight constants to CSS font weight constants.
# @param weight `int` font weight Qt constant, such as `QtGui.QFont.Normal` or `QtGui.QFont.Bold`
# @param default `int` default CSS stylesheet font weight used on failure to get the
# corresponding CSS weight value
# @returns `int` CSS font weight constant
# @see globalvars::FONT_WEIGHTS, font_weight_css2qt()
def font_weight_qt2css(weight, default=0):
    for w in FONT_WEIGHTS:
        if FONT_WEIGHTS[w] == weight:
            return w
    return default

## Constructs a Qt font object (`QtGui.QFont`) from a Qt style sheet string.
# @param style `str` the widget style sheet that is retrieved with the styleSheet() method
# of `QtWidgets.QWidget` derived classes
# @param font_unit `str` font size unit: either 'pt' (points) or 'px' (pixels)
# @param default_font `QtGui.QFont` default font used in case of failure
# @returns `QtGui.QFont` Qt font object
# @see stylesheet_load(), make_font(), font_to_stylesheet()
def font_from_stylesheet(style, font_unit='pt', default_font=None):
    dic_style = stylesheet_load(style)
    if not 'font-family' in dic_style:
        if not default_font:
            return None
        else:
            dic_style['font-family'] = default_font.family()
    if not 'font-size' in dic_style:
        if not default_font:
            return None
        else:
            dic_style['font-size'] = default_font.pointSize() if font_unit == 'pt' else default_font.pixelSize()
    if not 'font-weight' in dic_style:
        if not default_font:
            return None
        else:
            dic_style['font-weight'] = font_weight_qt2css(default_font.weight())
    if not 'font-style' in dic_style:
        dic_style['font-style'] = 'normal'

    font =  make_font(dic_style['font-family'], dic_style['font-size'], font_weight_css2qt(dic_style['font-weight']), (dic_style['font-style'] == 'italic'), font_unit)
    #print(f"FONT: font_unit={font_unit}, family={font.family()}, size(pt)={font.pointSize()}, size(px)={font.pixelSize()}, weight={font.weight()}")
    return font

## Stores a give Qt font in a style sheet string and returns the modified style sheet.
# @param font `QtGui.QFont` Qt font object
# @param style `str` the widget style sheet that is retrieved with the styleSheet() method
# of `QtWidgets.QWidget` derived classes
# @param font_unit `str` font size unit: either 'pt' (points) or 'px' (pixels)
# @returns `str` updated style sheet string
# @see stylesheet_load(), stylesheet_dump(), font_from_stylesheet()
def font_to_stylesheet(font, style, font_unit='pt'):
    dic_style = stylesheet_load(style)
    dic_style['font-family'] = font.family()
    dic_style['font-size'] = font.pointSize() if font_unit == 'pt' else font.pixelSize()
    dic_style['font-weight'] = font_weight_qt2css(font.weight())
    dic_style['font-style'] = 'italic' if font.italic() else 'normal'
    return stylesheet_dump(dic_style, add_units={'font-size': font_unit})

## Returns a Qt color object from a Qt style sheet string.
# @param style `str` the widget style sheet that is retrieved with the styleSheet() method
# of `QtWidgets.QWidget` derived classes
# @param tag `str` the specific color attribute name in the style sheet
# @param default `str` default color name used in case of failure
# @returns `QtGui.QColor` Qt color object constructed from the style sheet
# @see stylesheet_load(), color_to_stylesheet()
def color_from_stylesheet(style, tag='background-color', default='black'):
    dic_style = stylesheet_load(style)
    return QtGui.QColor(dic_style.get(tag, default))

## Stores a Qt color object in a style sheet string and returns the modified style sheet.
# @param style `str` the widget style sheet that is retrieved with the styleSheet() method
# of `QtWidgets.QWidget` derived classes
# @param tag `str` the specific color attribute name in the style sheet
# @returns `str` updated style sheet string
# @see stylesheet_load(), stylesheet_dump(), color_from_stylesheet()
def color_to_stylesheet(color, style, tag='background-color'):
    dic_style = stylesheet_load(style)
    dic_style[tag] = color.name(1)
    return stylesheet_dump(dic_style)

## Stores a property (attribute) in a style sheet string and returns the modified style sheet.
# @param propname `str` name of the property to store, e.g. 'background-color'
# @param propvalue `str` value of the property to store, e.g. 'black'
# @param style `str` the widget style sheet that is retrieved with the styleSheet() method
# of `QtWidgets.QWidget` derived classes
# @returns `str` updated style sheet string
# @see stylesheet_load(), stylesheet_dump(), property_from_stylesheet()
def property_to_stylesheet(propname, propvalue, style):
    dic_style = stylesheet_load(style)
    dic_style[propname] = propvalue
    return stylesheet_dump(dic_style)

## Reads a property from a style sheet string and returns its value.
# @param propname `str` name of the property to store, e.g. 'background-color'
# @param style `str` the widget style sheet that is retrieved with the styleSheet() method
# of `QtWidgets.QWidget` derived classes
# @param default `str` | `int` | `float` default value used in case of failure
# @returns `str` | `int` | `float` the value of the queried property
def property_from_stylesheet(propname, style, default=None):
    dic_style = stylesheet_load(style)
    return dic_style.get(propname, default)

# ------------------------------------------------------------------------ #

## @brief Syntax highlighter class for JSON.
# Used in pycross::forms::WordSrcDialog (DB table definition).
# @see [QSyntaxHighlighter docs](https://doc.qt.io/qt-5/qsyntaxhighlighter.html)
class JsonHiliter(QtGui.QSyntaxHighlighter):

    ## @brief Regex-based patterns and their corresponding color values.
    # Each record has 3 elements:
    #   1. `Python regex object` compiled regex pattern
    #   2. `int` group number in regex match results to highlight
    #   (0 = whole match, 1 = first expression in parentheses, etc...)
    #   3. `QtGui.QColor` color to apply to matched text
    PATTERNS = [
        # operators (dot, comma, colon)
        (re.compile(r'([\.,\:])'), 1, QtGui.QColor(QtCore.Qt.red)),
        # brackets
        (re.compile(r'([\{\}\[\]\(\)])'), 1, QtGui.QColor(QtCore.Qt.gray)),
        # numbers
        (re.compile(r'([\s,\:\{\[\(])([\-\+]?[\d\.]+)([\s,\:\}\]\)]?)'), 2, QtGui.QColor(QtCore.Qt.blue)),
        (re.compile(r'([\s,\:\{\[\(])([\-\+]?[\d\.]+$)'), 2, QtGui.QColor(QtCore.Qt.blue)),
        (re.compile(r'(^[\-\+]?[\d\.]+)([\s,\:\}\]\)]?)'), 1, QtGui.QColor(QtCore.Qt.blue)),
        (re.compile(r'(^[\-\+]?[\d\.]+$)'), 1, QtGui.QColor(QtCore.Qt.blue)),
        # boolean
        (re.compile(r'([\s,\:\{\[\(])(true|false)([\s,\:\}\]\)])'), 2, QtGui.QColor(QtCore.Qt.magenta)),
        (re.compile(r'([\s,\:\{\[\(])(true$|false$)'), 2, QtGui.QColor(QtCore.Qt.magenta)),
        (re.compile(r'(^true|^false)([\s,\:\}\]\)])'), 1, QtGui.QColor(QtCore.Qt.magenta)),
        (re.compile(r'(^true$|^false$)'), 1, QtGui.QColor(QtCore.Qt.magenta)),
        # null values
        (re.compile(r'([\s,\:\{\[\(])(null)([\s,\:\}\]\)])'), 2, QtGui.QColor(QtCore.Qt.gray)),
        (re.compile(r'([\s,\:\{\[\(])(null$)'), 2, QtGui.QColor(QtCore.Qt.gray)),
        (re.compile(r'(^null)([\s,\:\}\]\)])'), 1, QtGui.QColor(QtCore.Qt.gray)),
        (re.compile(r'(^null$)'), 1, QtGui.QColor(QtCore.Qt.gray)),
        # string values
        (re.compile(r'([\s,\:\[\(])(\".*?\")'), 2, QtGui.QColor(QtCore.Qt.darkCyan)),
        (re.compile(r'(^\".*?\")'), 1, QtGui.QColor(QtCore.Qt.darkCyan)),
        # key names
        (re.compile(r'(\".*?\")(\s*\:)'), 1, QtGui.QColor(QtCore.Qt.darkGreen))
    ]

    ## @brief Qt signal emitted on a syntax parser error.
    # Arguments:
    #   * `QtGui.QSyntaxHighlighter` this instance
    #   * `str` error message string
    #   * `str` error docs string
    #   * `int` absolute position of the error in the source code
    #   * `int` line number in the source code
    #   * `int` column number in the source code
    sig_parse_error = QtCore.pyqtSignal(QtGui.QSyntaxHighlighter, str, str, int, int, int)
    ## @brief Qt signal emitted on a syntax parser success.
    # Arguments:
    #   * `QtGui.QSyntaxHighlighter` this instance
    sig_parse_success = QtCore.pyqtSignal(QtGui.QSyntaxHighlighter)

    ## @param parent `QtGui.QTextDocument` parent document that the highlighter binds to
    # @param decode_errors `bool` whether to highlight and process JSON decode errors
    # @param on_decode_error `QtCore.pyQtSlot` slot for the `JsonHiliter::sig_parse_error` signal
    # @param on_decode_success `QtCore.pyQtSlot` slot for the `JsonHiliter::sig_parse_success` signal
    def __init__(self, parent: QtGui.QTextDocument, decode_errors=False,
        on_decode_error=None, on_decode_success=None):
        super().__init__(parent)
        ## `bool` whether to highlight and process JSON decode errors
        self.decode_errors = decode_errors
        if on_decode_error: self.sig_parse_error.connect(on_decode_error)
        if on_decode_success: self.sig_parse_success.connect(on_decode_success)
        ## `QtGui.QTextCharFormat` error highlighting text format
        self._error_format = QtGui.QTextCharFormat()
        self._error_format.setBackground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.darkRed)))
        self._error_format.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.yellow)))
        ## `json.JSONDecoder` JSON decoder
        self.decoder = json.JSONDecoder()

    ## Override of `QtGui.QSyntaxHighlighter::highlightBlock()` method: does the syntax highlighting.
    # @param text `str` the text string to be parsed and highlighted
    def highlightBlock(self, text):
        # clear format
        length = self.currentBlock().length()
        #self.setFormat(0, length, QtGui.QTextCharFormat())
        # syntax highlighting
        for pattern in JsonHiliter.PATTERNS:
            gr = pattern[1]
            for m in pattern[0].finditer(text):
                try:
                    self.setFormat(m.start(gr), m.end(gr) - m.start(gr), pattern[2])
                except:
                    pass
        # error highlighting
        if not self.decode_errors: return
        doc = self.document()
        offset = self.currentBlock().position()
        try:
            self.decoder.decode(doc.toPlainText())
        except json.JSONDecodeError as err:
            if err.pos >= offset and err.pos < (offset + length):
                self.setFormat(err.pos - offset, 1, self._error_format)
            self.sig_parse_error.emit(self, err.msg, err.doc, err.pos, err.lineno, err.colno)
        else:
            self.sig_parse_success.emit(self)
