# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
This file is part of the ycaptcha project hosted at https://github.com/S0mbre/ycaptcha

This module provides a base class for the command-line interface (CLI).
"""

import fire
from .utils import *

COMMAND_PROMPT = COLOR_PROMPT + '\nCOMMAND? [' + COLOR_STRESS + 'w' + COLOR_PROMPT + ' to quit] > '
WRONG_CMD_MSG = COLOR_ERR + 'Wrong command! Type ' + COLOR_STRESS + 'h' + COLOR_ERR + ' for help.'
EMPTY_CMD_MSG = COLOR_ERR + 'Empty command!'
QUIT_CMD = 'w'
       
## ******************************************************************************** ## 
class CLIBase:
    
    def __init__(self):
        self.commands = {f[4:].lower(): getattr(self, f) for f in dir(self) if callable(getattr(self, f)) and f.startswith('cmd_')}        
        self.commands[QUIT_CMD] = None
        self.usage = COLOR_HELP + COLOR_BRIGHT + '\nUSAGE:\t[{}] [value1] [value2] ... [--param3=value3] [--param4=value4] ...'.format('|'.join(sorted(self.commands.keys())))
        self.usage2 = COLOR_HELP + '\t' + '\n\t'.join([(COLOR_STRESS + fn + ':\n' + COLOR_HELP + (self.commands[fn].__doc__ if self.commands[fn].__doc__ else '')) for fn in self.commands if fn != QUIT_CMD])
           
    def cmd_help(self, detail=1):
        """
        Show CLI help.        
        PARAMS:
            - detail [int]: if == 1: show the "USAGE [...]" string; 
                            if == 2: show comprehensive docs for each command / function
        RETURNS:
            None
        """
        print(self.usage)
        print(COLOR_HELP + 'Enter "h 2" to show more detail.' if detail < 2 else self.usage2)
        
    def beforeRun(self):
        """
        Runs before processing any commands in CLI.
        """
        pass
    
    def beforeQuit(self):
        """
        Runs before quitting CLI.
        """
        pass
        
    def run(self):
        """
        Provides a continuously running commandline shell.        
        The one-letter commands used are listed in the commands dict.
        """
        self.beforeRun()
        entered = ''
        while True:
            try:
                print(COMMAND_PROMPT, end='')
                entered = str(input()).lower()
                if not entered:
                    print(EMPTY_CMD_MSG)
                    continue
                cmds = entered.split(' ')
                if cmds[0] in self.commands:
                    if self.commands[cmds[0]] is None: 
                        self.beforeQuit()
                        break                    
                    fire.Fire(self.commands[cmds[0]], ' '.join(cmds[1:]) if len(cmds) > 1 else '-') 
                else:
                    print(WRONG_CMD_MSG)
                    self.cmd_help()
                    continue    
                
            except KeyboardInterrupt:
                self.beforeQuit()
                break
            
            except fire.core.FireExit:
                continue
            
            except Exception as err:
                print_err(str(err))
                continue