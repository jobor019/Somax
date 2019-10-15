import logging
# The StreamView object is a container that manages several atoms, whose activity
#   patterns are taken and then mixed. This is mainly motivated to modulate the diverse
#   activity patterns depending on the transformations.
from copy import deepcopy
from functools import reduce
from typing import Callable, Tuple, ClassVar

from somaxlibrary import Tools
from somaxlibrary.ActivityPatterns import AbstractActivityPattern
from somaxlibrary.Atom import Atom
from somaxlibrary.Corpus import Corpus
from somaxlibrary.Exceptions import InvalidPath
from somaxlibrary.Labels import AbstractLabel
from somaxlibrary.MemorySpaces import NGramMemorySpace
from somaxlibrary.Tools import SequencedList


class StreamView(object):
    def __init__(self, name: str, weight: float = 1.0, merge_actions: Tuple[Callable, ...] = None):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("[__init__] Creating streamview {} with weight {} and merge actions {}"
                          .format(name, weight, merge_actions))

        self.name = name
        self._merge_actions = [cls() for cls in merge_actions] if merge_actions else []
        self._atoms: {str: Atom} = dict()
        self._streamviews: {str: StreamView} = {}
        self.weight = weight

    def __repr__(self):
        return "Streamview with name {0} and atoms {1}.".format(self.name, self._atoms)

    def create_atom(self, path: [str], weight: float, label_type: ClassVar[AbstractLabel],
                    activity_type: ClassVar[AbstractActivityPattern], memory_type: ClassVar[NGramMemorySpace],
                    self_influenced: bool) -> Atom:
        """creating an atom at required path
        Raises: KeyError, InvalidPath"""
        self.logger.debug("[create_atom] Attempting to create atom with path {}.".format(path))
        target_name: str = path.pop(0)
        if path:  # Path is not empty: create atom within a child streamview
            self._streamviews[target_name].create_atom(path, weight, label_type, activity_type, memory_type, self_influenced)
        elif target_name in self._atoms.keys():
            raise InvalidPath(f"An atom with the name {target_name} already exists in streamview {self.name}.")
        else:
            atom = Atom(target_name, weight, label_type, activity_type, memory_type, self_influenced)
            self._atoms[target_name] = atom
            return atom  # TODO: Not sure about this return here....

    def create_streamview(self, path: [str], weight: float, merge_actions: (ClassVar, ...)):
        """creating a streamview at required path
        Raises: KeyError, InvalidPath"""
        self.logger.debug("[create_streamview] Attempting to create streamview with path {}.".format(path))
        target_name: str = path.pop(0)
        if path:  # Path is not empty: create streamview within a child streamview
            self._streamviews[target_name].create_streamview(path, weight, merge_actions)
        elif target_name in self._streamviews.keys():
            raise InvalidPath(f"A streamview with the name {target_name} already exists in streamview {self.name}.")
        else:
            self._streamviews[target_name] = StreamView(path, weight, merge_actions)


    # TODO: Only used at one place. Consider replacing/streamlining behaviour
    def add_atom(self, atom, name=None, copy=False, replace=False):
        '''add an existing atom in the current streamview'''
        if name == None:
            name = atom.name
        if name in self._atoms.keys():
            if not replace:
                raise Exception("{0} already exists in {1}".format(atom.name, self.name))
        if copy:
            # TODO: Why? ~~~
            new_atom: Atom = deepcopy(atom)
            new_atom.name = name
            self.atoms[name] = new_atom
        else:
            self._atoms[name] = atom

    def get_atom(self, name, copy=False):
        '''fetching an atom'''
        path, path_bottom = Tools.parse_path(name)
        if path_bottom != None and path in self._atoms.keys():
            return self._atoms[path].get_atom(path_bottom)
        elif path_bottom == None and path in self._atoms.keys():
            return self._atoms[path]
        else:
            return None

    def delete_atom(self, name):
        '''deleting an atom'''
        if not ":" in name:
            del self._atoms[name]
        else:
            head, tail = Tools.parse_path(name)
            self._atoms[name].delete_atom(tail)

    def influence(self, path, time, *data, **kwargs):
        '''influences all sub-atoms with data'''
        self.logger.debug("[influence] Call to influence in streamview {} with path {}, time {}, args {} and kwargs {}"
                          .format(self.name, path, time, data, kwargs))
        if path == None or path == "":
            for atom in self._atoms.values():
                atom.influence(time, *data)
        else:
            pf, pr = Tools.parse_path(path)
            if pf in self._atoms.keys():
                if isinstance(self._atoms[pf], Atom.Atom):
                    self._atoms[pf].influence(time, *data, **kwargs)
                elif isinstance(self._atoms[pf], StreamView):
                    self._atoms[pf].influence(pr, time, *data, **kwargs)
        self.logger.debug("[influence] Influence in streamview {} terminated successfully.".format(self.name))

    def read(self, corpus: Corpus):
        '''read all sub-atoms with data'''
        self.logger.debug(f"[read] Init read in streamview {self.name} with corpus {corpus}")
        for atom in self._atoms.values():
            atom.read(corpus)

    def get_activities(self, date, path=None, weighted=True):
        '''get separated activities of children'''
        if path != None:
            if ':' in path:
                head, tail = Tools.split_path(head, tail)
                activities = self._atoms[head].get_activities(date, path=tail)
            else:
                activities = self._atoms[path].get_activities(date)
        else:
            activities = dict()
            for name, atom in self._atoms.iteritems():
                activities[name] = atom.get_merged_activity(date, weighted=weighted)
        if issubclass(type(activities), Tools.SequencedList):
            activities = {path: activities}
        return activities

    def get_merged_activity(self, date, weighted=True):
        '''get merged activities of children'''
        weight_sum = float(reduce(lambda x, y: x + y.weight, self._atoms.values(), 0.0))  # TODO: Not used
        merged_activity = SequencedList()
        for atom in self._atoms.values():
            w = atom.weight if weighted else 1.0
            merged_activity = merged_activity + atom.get_activity(date).mul(w, 0)
        for merge_action in self._merge_actions:
            merged_activity = merge_action.merge(merged_activity)
        self.logger.debug("[get_merged_activity] In streamview {}, returning merged activity {}."
                          .format(self.name, merged_activity))
        return merged_activity

    def set_weight(self, path, weight):
        '''set weight of atom addressed at path'''
        if not ":" in path:
            self._atoms[path].set_weight(weight)
        else:
            head, tail = Tools.parse_path(path)
            self._atoms[head].set_weight(tail, weight)

    def get_info_dict(self):
        '''returns info dictionary'''
        infodict = {"activity type": str(type(self)), "weight": self.weight, "type": "Streamview"}
        infodict["atoms"] = dict()
        for a, v in self._atoms.items():
            infodict["atoms"][a] = v.get_info_dict()
        return infodict

    def reset(self, time):
        for f in self.atoms.values():
            f._reset(time)
