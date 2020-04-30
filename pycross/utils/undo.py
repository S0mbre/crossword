# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.undo
# Borrowed from [https://github.com/derdon/hodgepodge/blob/master/python/undoredomanager.py]
from .globalvars import *
# ******************************************************************************** #        

class Operation:

    def __init__(self, command, undocommand, description=''):
        if not isinstance(command, dict):
            raise Exception(_('command must be a dictionary type with "func" and optional "args" and "kwargs" keys!'))
        self.command = command
        if not isinstance(undocommand, dict):
            raise Exception(_('undocommand must be a dictionary type with "func" and optional "args" and "kwargs" keys!'))
        self.undocommand = undocommand
        self.description = description

    def _do_cmd(self, cmd):
        if not 'func' in cmd:
            raise Exception(_('No "func" key in passed command!'))
        if 'args' in cmd:
            if 'kwargs' in cmd:
                cmd['func'](*cmd['args'], **cmd['kwargs'])
            else:
                cmd['func'](*cmd['args'])
        else:
            cmd['func']()

    def __call__(self):
        self._do_cmd(self.command)

    def undo(self):
        self._do_cmd(self.undocommand)

# ******************************************************************************** #

class EmptyCommandStackError(Exception):
    pass

class HistoryOverflowError(Exception):
    pass

class CommandManager():
    def __init__(self, histsize=1e4, cyclic=True, on_update=None):
        self.histsize = histsize
        self.cyclic = cyclic
        self.on_update = on_update
        self._undo_commands = []
        self._redo_commands = []

    def canundo(self):
        return len(self._undo_commands) > 0

    def canredo(self):
        return len(self._redo_commands) > 0

    def undoable(self, pos=-1):
        return self._undo_commands[pos]

    def redoable(self, pos=-1):
        return self._redo_commands[pos]

    def _push_undo_command(self, command):
        if len(self._undo_commands) == self.histsize:
            if self.cyclic:
                self._undo_commands.pop(0)
            else:
                raise HistoryOverflowError()
        self._undo_commands.append(command)

    def _pop_undo_command(self):
        return self._undo_commands.pop() if len(self._undo_commands) else None

    def _push_redo_command(self, command):
        if len(self._redo_commands) == self.histsize:
            if self.cyclic:
                self._redo_commands.pop(0)
            else:
                raise HistoryOverflowError()
        self._redo_commands.append(command)

    def _pop_redo_command(self):
        return self._redo_commands.pop() if len(self._redo_commands) else None

    def do(self, command):
        if not isinstance(command, Operation):
            raise Exception(_('command must be an instance of Operation class!'))
        command()
        self._push_undo_command(command)
        # clear the redo stack when a new command was executed
        self._redo_commands.clear()
        if self.on_update: self.on_update()

    def undo(self, n=1):
        for _ in range(n):
            command = self._pop_undo_command()
            if command is None: return False
            command.undo()
            self._push_redo_command(command)
        if self.on_update: self.on_update()
        return True

    def redo(self, n=1):
        for _ in range(n):
            command = self._pop_redo_command()
            if not callable(command): return False
            command()
            self._push_undo_command(command)
        if self.on_update: self.on_update()
        return True