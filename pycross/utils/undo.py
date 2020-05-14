# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.undo
# Undo / Redo history support using a simple list-based approach.
# Borrowed from [https://github.com/derdon/hodgepodge/blob/master/python/undoredomanager.py]
from .globalvars import *
# ******************************************************************************** #        

## Abstract undoable operation (action) with a do/undo callback pair.
class Operation:

    ## Constructor.
    # @param command `dict` the 'do' command (direct action) constisting  
    # of a pointer to a function/method and arguments passed to it.
    # The dictionary keys are as follows:
    #   * func `callable` pointer to the 'do' function or other callable object
    #   * args `tuple` positional arguments passed to the 'do' function (optional) 
    #   * kwargs `dict` keyword arguments passed to the 'do' function (optional)
    # @warning The first parameter passed to 'func' is always the pointer to this
    # Operation instance. So 'args' and/or 'kwargs' (if present) will start from
    # the second parameter.
    # @param undocommand `dict` the 'undo' command (reverse action undoing whatever
    # 'command' does). Its keys are the same as in 'command'.
    # @param description `str` optional description of the command (what is does).
    # The default is an empty string.
    # @param kwargs `keyword arguments` any extra objects that can be stored in
    # the Operation instance to address in the do / undo callbacks.
    # @warning Note that neither 'command' nor 'undocommand' provide means to
    # return a result -- their callback functions should therefore return nothing (`None`)
    def __init__(self, command, undocommand, description='', **kwargs):
        # 'command' must be a properly formatted dict
        if not isinstance(command, dict) or not 'func' in command:
            raise Exception(_('command must be a dictionary type with "func" and optional "args" and "kwargs" keys!'))
        ## `dict` the command that can be undone (see constructor for description)
        self.command = command
        # 'undocommand' must be a properly formatted dict
        if not isinstance(undocommand, dict) or not 'func' in undocommand:
            raise Exception(_('undocommand must be a dictionary type with "func" and optional "args" and "kwargs" keys!'))
        ## `dict` the reverse command undoing Operation::command (see constructor for description)
        self.undocommand = undocommand
        ## `str` optional description of the command (what is does)
        self.description = description
        # store extra variables
        if kwargs: self.__dict__.update(kwargs)

    ## Util method that executes the Do or the Undo command passing their arguments.
    # @param cmd `dict` either Operation::command or Operation::undocommand
    def _do_cmd(self, cmd):
        # if there are args
        if 'args' in cmd:
            # if there are keyword args
            if 'kwargs' in cmd:
                cmd['func'](self, *cmd['args'], **cmd['kwargs'])
            # no keyword args
            else:
                cmd['func'](self, *cmd['args'])
        # no args
        else:
            cmd['func'](self)

    ## operator () overload to call Operation::command from the instance directly.
    def __call__(self):
        self._do_cmd(self.command)

    ## Undoes the executed Operation::command by calling Operation::undocommand.
    def undo(self):
        self._do_cmd(self.undocommand)

# ******************************************************************************** #

## Exception raised when the Undo or Redo history exceeds its threshold size.
class HistoryOverflowError(Exception):
    pass

## Stack-like Undo / Redo history manager: lets the app manage undoable actions.
class CommandManager():

    ## Constructor.
    # @param histsize `int` Undo / Redo history size (max number of operations
    # stored in each stack); default is 10k
    # @param cyclic `bool` if `True` (default) the Undo / Redo stack will 
    # automatically remove the oldest operation when the threshold size is reached;
    # if `False`, the HistoryOverflowError excetion will be raised.
    # @param on_update `callable` callback fired when the Undo or Redo stack is updated
    # @param on_pop_undo `callable` callback fired when an operation is removed from the Undo stack
    # @param on_push_undo `callable` callback fired when an operation is added to the Undo stack
    # @param on_pop_redo `callable` callback fired when an operation is removed from the Redo stack
    # @param on_push_redo `callable` callback fired when an operation is added to the Redo stack
    def __init__(self, histsize=1e4, cyclic=True, on_update=None,
        on_pop_undo=None, on_push_undo=None, on_pop_redo=None, on_push_redo=None):
        ## `int` Undo / Redo history size
        self.histsize = histsize
        ## `bool` if `True` (default) the Undo / Redo stack will 
        # automatically remove the oldest operation when the threshold size is reached
        self.cyclic = cyclic
        ## `callable` callback fired when the Undo or Redo stack is updated
        self.on_update = on_update
        ## `callable` callback fired when an operation is removed from the Undo stack
        self.on_pop_undo = on_pop_undo
        ## `callable` callback fired when an operation is added to the Undo stack
        self.on_push_undo = on_push_undo
        ## `callable` callback fired when an operation is removed from the Redo stack
        self.on_pop_redo = on_pop_redo
        ## `callable` callback fired when an operation is added to the Redo stack
        self.on_push_redo = on_push_redo
        ## `list` Undo stack
        self._undo_commands = []
        ## `list` Redo stack
        self._redo_commands = []

    ## Checks if there are undoable operations in the Undo stack
    # @returns `bool` whether there are undoable operations in the Undo stack
    # @see CommandManager::canredo()
    def canundo(self):
        return len(self._undo_commands) > 0

    ## Checks if there are redoable operations in the Redo stack
    # @returns `bool` whether there are redoable operations in the Redo stack
    # @see CommandManager::canundo()
    def canredo(self):
        return len(self._redo_commands) > 0

    ## Returns an operation from the Undo stack.
    # @param pos `int` index of the operation
    # @returns `Command` undoable operation
    def undoable(self, pos=-1):
        return self._undo_commands[pos]

    ## Returns an operation from the Redo stack.
    # @param pos `int` index of the operation
    # @returns `Command` redoable operation
    def redoable(self, pos=-1):
        return self._redo_commands[pos]

    ## @brief Stores (appends) a new command in the Undo stack.
    # If the max stack size is reached, the history will remove the oldest 
    # operation if CommandManager::cyclic is `True` or raise the HistoryOverflowError error.
    # @param command `Operation` the new command to store
    def _push_undo_command(self, command):
        if len(self._undo_commands) == self.histsize:
            if self.cyclic:
                self._undo_commands.pop(0)
            else:
                raise HistoryOverflowError()
        self._undo_commands.append(command)
        if self.on_push_undo:
            self.on_push_undo(self, command)

    ## Removes the latest operation from the Undo stack and returns it.
    # @returns `Operation` the removed command
    def _pop_undo_command(self):
        cmd = self._undo_commands.pop() if len(self._undo_commands) else None
        if self.on_pop_undo and not cmd is None:
            self.on_pop_undo(self, cmd)
        return cmd

    ## @brief Stores (appends) a command in the Redo stack.
    # The Redo stack adds operations removed from the Undo stack (so they
    # can be redone later).
    # If the max stack size is reached, the history will remove the oldest 
    # operation if CommandManager::cyclic is `True` or raise the HistoryOverflowError error.
    # @param command `Operation` the command to store
    def _push_redo_command(self, command):
        if len(self._redo_commands) == self.histsize:
            if self.cyclic:
                self._redo_commands.pop(0)
            else:
                raise HistoryOverflowError()
        self._redo_commands.append(command)
        if self.on_push_redo:
            self.on_push_redo(self, command)

    ## Removes the latest operation from the Redo stack and returns it.
    # @returns `Operation` the removed command
    def _pop_redo_command(self):
        cmd = self._redo_commands.pop() if len(self._redo_commands) else None
        if self.on_pop_redo and not cmd is None:
            self.on_pop_redo(self, cmd)
        return cmd

    ## Executes the given command, adding it to the Undo stack so it can be undone later.
    # @param command `Operation` the command to execute
    def do(self, command):
        # check that 'command' is an Operation object
        if not isinstance(command, Operation):
            raise Exception(_('command must be an instance of Operation class!'))
        # use Operation class's () operator to call the underlying callback function
        command()
        # append the command to the Undo stack
        self._push_undo_command(command)
        # clear the redo stack since a new command was executed (can't redo the older stuff)
        self._redo_commands.clear()
        # call on_update callback
        if self.on_update: self.on_update()

    ## Undoes a given number of operations stored in the Undo stack.
    # @param n `int` number of operations to undo (rewinding the stack)
    # @returns `bool` `True` on success, `False` on failure to undo
    def undo(self, n=1):
        for _ in range(n):
            command = self._pop_undo_command()
            if command is None: return False
            command.undo()
            self._push_redo_command(command)
        if self.on_update: self.on_update()
        return True

    ## Redoes a given number of operations stored in the Redo stack.
    # @param n `int` number of operations to redo (rewinding the stack)
    # @returns `bool` `True` on success, `False` on failure to redo
    def redo(self, n=1):
        for _ in range(n):
            command = self._pop_redo_command()
            if not callable(command): return False
            command()
            self._push_undo_command(command)
        if self.on_update: self.on_update()
        return True