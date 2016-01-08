"""
module undo provides class definitions useful for undo/redo functionality in catan.
"""
import logging


class UndoManager(object):
    """
    class UndoManager manages a stack of Command objects for the purpose of
    implementing undo/redo functionality.

    Usage:
        undo_manager = UndoManager()
        undo_manager.do(CmdXYZ(params...))
        undo_manager.undo()
    """
    def __init__(self):
        self.command_stack = list()

    def do(self, command):
        self.command_stack.append(command)
        command.do()
        logging.debug('{}.do() called, stack now={}'.format(type(command), self.command_stack))

    def can_undo(self):
        return len(self.command_stack) > 0

    def undo(self):
        if len(self.command_stack) < 1:
            raise Exception('Cannot perform undo, command stack is empty')
        command = self.command_stack.pop()
        command.undo()
        logging.debug('{}.undo() called, stack now={}'.format(type(command), self.command_stack))


class Command(object):
    """
    class Command describes an interface which all commands must implement.

    Commands must be doable and undoable. The actual method of do/undo is left
    up to the implementing class.
    """
    def do(self):
        raise NotImplemented()

    def undo(self):
        raise NotImplemented()

