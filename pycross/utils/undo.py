# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

import copy
## ******************************************************************************** ##        
        
class History:
    
    
    def __init__(self):
        self.history = []
        self.index = -1
        self.histsize = 500
    
    def save(self, obj):
        if self.history and (not type(self.history[-1]) is type(obj)):
            raise Exception('At least one history item is an object of a different type than the one '
                            'you are attempting to add. Please consider either '
                            'clearing the history first or adding items of the same type.')
        
        if self.history and self.index < len(self.history) - 1:
            self.history = self.history[:self.index + 1] 
        excess = len(self.history) - self.histsize
        if excess > 0: self.history = self.history[excess:]
            
        self.history.append(copy.deepcopy(obj))
        self.index = len(self.history) - 1 
        
    def clear(self):
        self.history = []
        self.index = -1
        
    def undo(self, obj, times=1):
        if self.index < 1: return
        if times > self.index: times = self.index
        obj.__dict__.update(self.history[self.index - times].__dict__)
        self.index -= times
        
    def redo(self, obj, times=1):
        l = len(self.history)
        if self.index == l - 1: return
        if times > (l - self.index - 1): times = l - self.index - 1
        obj.__dict__.update(self.history[self.index + times].__dict__)
        self.index += times