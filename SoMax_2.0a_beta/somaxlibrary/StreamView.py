import logging
# The StreamView object is a container that manages several atoms, whose activity
#   patterns are taken and then mixed. This is mainly motivated to modulate the diverse
#   activity patterns depending on the transformations.
from functools import reduce
from typing import Callable, Tuple

from somaxlibrary.Atom import Atom
from somaxlibrary import Events, ActivityPatterns, MemorySpaces, Tools
from somaxlibrary.Exceptions import InvalidPath
from somaxlibrary.MergeActions import DistanceMergeAction
from somaxlibrary.Tools import SequencedList


class StreamView(object):
    def __init__(self, name: str, weight: float = 1.0, atoms: {str: Atom} = None,
                 merge_actions: Tuple[Callable, ...] = None):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("[__init__] Creating streamview {} with weight {}, atoms {} and merge actions {}"
                          .format(name, weight, atoms, merge_actions))

        self.name = name
        self._merge_actions = [cls() for cls in merge_actions] if merge_actions else []
        self._atoms = atoms if atoms else dict()
        self.weight = weight

    def __repr__(self):
        return "Streamview with name {0} and atoms {1}.".format(self.name, self._atoms)

    def create_atom(self, name: str = "atom", weight: float = 1.0, label_type=Events.AbstractLabel,
                    contents_type=Events.AbstractContents, event_type=Events.AbstractEvent,
                    activity_type=ActivityPatterns.ClassicActivityPattern, memory_type=MemorySpaces.NGramMemorySpace,
                    memory_file=None):
        """creating an atom at required path"""
        self.logger.debug("[create_atom] Attempting to create atom with path {}.".format(name))
        if name in self._atoms.keys():
            raise InvalidPath(f"An atom with the name {name} already exists in streamview {self.name}.")
        else:
            atom = Atom(name, weight, label_type, contents_type, event_type, activity_type, memory_type, memory_file)
            self._atoms[name] = atom
            return atom

        # atom = None
        # if ":" in name:
        #     head, tail = Tools.parse_path(name)  # if atom in a sub-streamview
        #     atom = self.atoms[head].add_atom(tail, weight, label_type, contents_type, event_type, activity_type,
        #                                      memory_type)
        #     self.logger.error("Could not add atom {0} in streamview {1}".format(name, self.name))
        #
        # else:
        #     # if atom is directly in current streamview
        #     if name in self.atoms:
        #         self.logger.error("Atom {0} already existing in {1}".format(name, self.name))
        #     else:
        #         atom = Atom.Atom(name, weight, label_type, contents_type, event_type, activity_type, memory_type,
        #                          memory_file)
        #         self.atoms[name] = atom
        # return atom

    # TODO: No longer supported with current implementation. Handle later
    # def create_streamview(self, path="streamview", weight=1.0, atoms=dict(), merge_actions=[DistanceMergeAction]):
    #     '''creating a streamview at required path'''
    #     # TODO: Either remove this behaviour entirely or clean up intent
    #     if ":" in path:
    #         # if streamview in sub-streamview
    #         head, tail = Tools.parse_path(path)
    #         st = self.atoms[head].create_streamview(tail, weight, atoms, merge_actions)
    #     else:
    #         # if streamview directly in current streamview
    #         st = StreamView(path, weight, atoms, merge_actions)
    #         self.atoms[path] = st
    #     return st

    # TODO: Only used at one place. Consider replacing/streamlining behaviour
    def add_atom(self, atom, name=None, copy=False, replace=False):
        '''add an existing atom in the current streamview'''
        if name == None:
            name = atom.name
        if name in self._atoms.keys():
            if not replace:
                raise Exception("{0} already exists in {1}".format(atom.name, self.name))
        if copy:
            self._atoms[name] = atom.copy(name)
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

    def read(self, path, filez):
        '''read all sub-atoms with data'''
        self.logger.debug(
            "[read] Init read in streamview {} with path {} and filepath {}".format(self.name, path, filez))
        if path == None:
            for n, a in self._atoms.items():
                if issubclass(type(a), Atom.Atom):
                    a.read(filez)
                else:
                    a.read(None, filez)
        else:
            path, path_follow = Tools.parse_path(path)
            if path_follow == None:
                for atom in self._atoms.values():
                    atom.read(filez)
            elif path in self._atoms.keys():
                if isinstance(self._atoms[path_follow], StreamView):
                    self._atoms[path_follow].read(path_follow, filez)
                else:
                    self._atoms[path_follow].read(filez)
            else:
                # TODO: Should this actually be an exception - where to catch it if that's the case?
                #       (should it terminate the entire parent call or just ignore the specific streamview?)
                raise Exception("Atom or streamview {0} missing!".format(path))

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
        for f in self._atoms.values():
            f.reset(time)
