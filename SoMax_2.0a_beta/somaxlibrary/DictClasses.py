from typing import Dict, List, Union, Tuple, Any

""" Temporary module for documenting all the content represented as nested dicts instead of proper classes. """

"""PlayerDict: Format:
    { playername: 
        {'player':          somaxlibrary.Player,
         'output_activity': None or ??,
         'triggering':      'automatic' or 'manual'
        }
    }
"""
PlayerDict = Dict[str, Dict[str, Any]]

