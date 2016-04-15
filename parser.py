class Parser(object):
    """
    The Parser class returns corresponding
    functions for matching keywords.
    """

    def __init__(self):
        """Creates an empty self._commands dictionary"""
        self._commands = {}

    def add_command(self, command, function):
        """Associates a command with a corresponding function""" 
        self._commands[command] = function

    def add_default(self, function):
        """Adds a default function which is called when
        no other function fits the input of self.get_function"""
        self._default = function

    def get_function(self, command):
        """Searches for registered commands in the parser's memory
        and returns their associated function"""
        command = command.strip().lower()
        for key, value in self._commands.items():
            if command.startswith(key):
                return self._commands[key]
        else:
            return self._default