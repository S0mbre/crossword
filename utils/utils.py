# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
pass
"""

import sys, os, subprocess
from datetime import datetime
from .globalvars import *
from PyQt5 import QtGui, QtCore, QtWidgets

### ---------------------------- COMMON ---------------------------- ###

def print_err(what, file=sys.stderr):
    print(COLOR_ERR + what, file=file)

def print_dbg(what, file=sys.stdout):    
    print(COLOR_STRESS + what, file=file)
        
def print_help(what, file=sys.stdout):
    print(COLOR_HELP + what, file=file)

def walk_dir(root_path, recurse, file_types, file_process_function):
    """
    """
    for d, dirs, files in os.walk(os.path.abspath(root_path)):
        for f in files:
            ext = os.path.splitext(f)[1][1:].lower()
            if (not file_types) or (ext in file_types):
                if file_process_function:
                    if not file_process_function(os.path.join(d, f)): return
        if not recurse: break

def run_exe(args, nowait=False, capture_output=True, encoding=ENCODING, timeout=None, **kwargs):
    if nowait:
        return os.spawnl(os.P_NOWAIT, *args if isinstance(args, list) or isinstance(args, tuple) else args)
    else:
        return subprocess.run(args, capture_output=capture_output, encoding=encoding, timeout=timeout, **kwargs)

def datetime_to_str(dt=None, strformat='%Y-%m-%d %H-%M-%S'):
    if dt is None: dt = datetime.now()
    return dt.strftime(strformat)

def str_to_datetime(text, strformat='%Y-%m-%d %H-%M-%S'):
    return datetime.strptime(text, strformat)


### ---------------------------- GUI ---------------------------- ###

class QThreadStump(QtCore.QThread):

    sig_error = QtCore.pyqtSignal(QtCore.QThread, str)

    def __init__(self, default_priority=QtCore.QThread.NormalPriority, 
                 on_start=None, on_finish=None, on_run=None, on_error=None,
                 start_signal=None, stop_signal=None, 
                 free_on_finish=False, start_now=False, can_terminate=True):
        super().__init__()
        self.init(default_priority, on_start, on_finish, on_run, on_error, 
                  start_signal, stop_signal, free_on_finish, can_terminate)
        if start_now: self.start()
    
    def __del__(self):
        self.wait()

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
        self.default_priority = default_priority if default_priority != QtCore.QThread.InheritPriority else QtCore.QThread.NormalPriority 
        self.on_run = on_run
        self.mutex = QtCore.QMutex()

    def lock(self):
        self.mutex.lock()

    def unlock(self):
        self.mutex.unlock()

    def run(self):
        self.setPriority(self.default_priority)
        if self.on_run and not self.isInterruptionRequested(): 
            try:
                self.on_run()
            except Exception as err:
                self.sig_error.emit(self, str(err))
        
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
    
def MsgBox(what, parent=None, title='pyCross', msgtype=QtWidgets.QMessageBox.Information, 
           btn=QtWidgets.QMessageBox.Ok):
    QtWidgets.QMessageBox(msgtype, title, what, btn, parent).exec()
        
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

def font_weight_css2qt(weight, default=0):
    if weight == 'normal':
        weight = QtGui.QFont.Normal
    elif weight == 'bold':
        weight = QtGui.QFont.Bold
    else:
        weight = FONT_WEIGHTS.get(int(weight), default)
    return weight  

def font_weight_qt2css(weight, default=0):    
    for w in FONT_WEIGHTS:
        if FONT_WEIGHTS[w] == weight:
            return w
    return default
        
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

def font_to_stylesheet(font, style, font_unit='pt'):
    dic_style = stylesheet_load(style)
    dic_style['font-family'] = font.family()
    dic_style['font-size'] = font.pointSize() if font_unit == 'pt' else font.pixelSize()
    dic_style['font-weight'] = font_weight_qt2css(font.weight())
    dic_style['font-style'] = 'italic' if font.italic() else 'normal'
    return stylesheet_dump(dic_style, add_units={'font-size': font_unit})

def color_from_stylesheet(style, tag='background-color', default='black'):
    dic_style = stylesheet_load(style)
    return QtGui.QColor(dic_style.get(tag, default))

def color_to_stylesheet(color, style, tag='background-color'):
    dic_style = stylesheet_load(style)
    dic_style[tag] = color.name(1)
    return stylesheet_dump(dic_style)

def property_to_stylesheet(propname, propvalue, style):
    dic_style = stylesheet_load(style)
    dic_style[propname] = propvalue
    return stylesheet_dump(dic_style)

def property_from_stylesheet(propname, style, default=None):
    dic_style = stylesheet_load(style)
    return dic_style.get(propname, default)
        
