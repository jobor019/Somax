import os

# Formats
MIDI_FILE = ['.mid', '.midi']

# Default settings
DEFAULT_CORPUS_PATH = os.getcwd()
CORPUS_FOLDER_NAME = 'corpus'
DEFAULT_FOREGROUND = [1]
DEFAULT_SELF_BACKGROUND = list(range(2, 17))
DEFAULT_MEL_BACKGROUND = list(range(2, 17))
DEFAULT_HARM_BACKGROUND = list(range(2, 17))

# File extension keys
STANDARD_FILE_EXT = ''
MELODIC_FILE_EXT = 'm'
HARMONIC_FILE_EXT = 'h'

# Logs
MAIN_LOGGER = 'main_log'
DEBUG_INDENT = ' ' * 9
CRITICAL_INDENT = ' ' * 12
INFO_INDENT = ' ' * 8