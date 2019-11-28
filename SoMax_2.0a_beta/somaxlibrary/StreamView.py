import logging
from functools import reduce
from typing import Callable, Tuple, ClassVar

from somaxlibrary.ActivityPattern import AbstractActivityPattern
from somaxlibrary.Atom import Atom
from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Exceptions import DuplicateKeyError
from somaxlibrary.Labels import AbstractLabel
from somaxlibrary.MemorySpaces import NGramMemorySpace
from somaxlibrary.MergeActions import AbstractMergeAction
from somaxlibrary.Parameter import Parameter
from somaxlibrary.Parameter import Parametric
from somaxlibrary.Peak import Peak
from somaxlibrary.Transforms import AbstractTransform


class StreamView(Parametric):
    def __init__(self, name: str, weight: float = 1.0, merge_actions: Tuple[Callable, ...] = ()):
        super(StreamView, self).__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("[__init__] Creating streamview {} with weight {} and merge actions {}"
                          .format(name, weight, merge_actions))

        self.name = name
        self._merge_actions: {str: AbstractMergeAction} = {}
        self.atoms: {str: Atom} = dict()
        self.streamviews: {str: StreamView} = {}
        self._weight: Parameter = Parameter(weight, 0.0, None, 'float', "Relative scaling of streamview peaks.")
        self.enabled: Parameter = Parameter(True, False, True, "bool", "Enables this Streamview.")
        self._parse_parameters()

        for merge_action in merge_actions:
            self.add_merge_action(merge_action())

    def __repr__(self):
        return "Streamview with name {0} and atoms {1}.".format(self.name, self.atoms)

    def add_merge_action(self, merge_action: AbstractMergeAction, override: bool = False):
        name: str = type(merge_action).__name__
        if name in self._merge_actions and not override:
            raise DuplicateKeyError("A merge action of this type already exists.")
        else:
            self._merge_actions[name] = merge_action

    # def update_parameter_dict(self) -> Dict[str, Union[Parametric, Parameter, Dict]]:
    #     streamviews = {}
    #     atoms = {}
    #     merge_actions = {}
    #     parameters = {}
    #     for name, streamview in self.streamviews.items():
    #         streamviews[name] = streamview.update_parameter_dict()
    #     for name, atom in self.atoms.items():
    #         atoms[name] = atom.update_parameter_dict()
    #     for merge_action in self._merge_actions:
    #         key: str = type(merge_action).__name__
    #         merge_actions[key] = merge_action.update_parameter_dict()
    #     for name, parameter in self._parse_parameters().items():
    #         parameters[name] = parameter.update_parameter_dict()
    #     self.parameter_dict = {"streamviews": streamviews,
    #                            "atoms": atoms,
    #                            "merge_actions": merge_actions,
    #                            "parameters": parameters}
    #     return self.parameter_dict

    def get_streamview(self, path: [str]) -> 'StreamView':
        """ Raises: KeyError. Technically also IndexError, but should not occur if input is well-formatted (expected)"""
        if not path:
            return self
        target_name: str = path.pop(0)
        if path:  # Path is not empty: descend recursively
            return self.streamviews[target_name]._get_streamview(path)
        else:
            return self.streamviews[target_name]

    def get_atom(self, path: [str]) -> Atom:
        """ Raises: KeyError. Technically also IndexError, but should not occur if input is well-formatted (expected)"""
        target_name: str = path.pop(0)
        if path:  # Path is not empty: descend recursively
            return self.streamviews[target_name]._get_atom(path)
        else:
            return self.atoms[target_name]

    def create_atom(self, path: [str], weight: float, label_type: ClassVar[AbstractLabel],
                    activity_type: ClassVar[AbstractActivityPattern], memory_type: ClassVar[NGramMemorySpace],
                    corpus: Corpus, self_influenced: bool, transforms: [(ClassVar[AbstractTransform], ...)]):
        """creating an atom at required path
        Raises: KeyError, InvalidPath, DuplicateKeyError"""
        self.logger.debug("[create_atom] Attempting to create atom with path {}.".format(path))

        new_atom_name: str = path.pop(-1)
        parent_streamview: 'StreamView' = self.get_streamview(path)
        if new_atom_name in parent_streamview.atoms.keys():
            raise DuplicateKeyError(f"An atom with the name '{new_atom_name}' already exists in "
                                    f"streamview '{parent_streamview.name}'.")
        parent_streamview.atoms[new_atom_name] = Atom(new_atom_name, weight, label_type, activity_type, memory_type,
                                                      corpus, self_influenced, transforms)

    def create_streamview(self, path: [str], weight: float, merge_actions: (ClassVar, ...)):
        """creating a streamview at required path
        Raises: KeyError, InvalidPath, DuplicateKeyError"""
        self.logger.debug("[create_streamview] Attempting to create streamview with path {}.".format(path))

        new_streamview_name: str = path.pop(-1)
        parent_streamview: 'StreamView' = self.get_streamview(path)
        if new_streamview_name in parent_streamview.streamviews.keys():
            raise DuplicateKeyError(f"A streamview with the name {new_streamview_name} already exists in "
                                    f"streamview {parent_streamview.name}.")
        parent_streamview.streamviews[new_streamview_name] = StreamView(new_streamview_name, weight, merge_actions)

    def update_peaks(self, time: float) -> None:
        for streamview in self.streamviews.values():
            streamview.update_peaks(time)
        for atom in self.atoms.values():
            atom.update_peaks(time)

    def merged_peaks(self, time: float, influence_history: [CorpusEvent], corpus: Corpus, **kwargs) -> [Peak]:
        peaks: [Peak] = []

        # Peaks from child streamviews
        for streamview in self.streamviews.values():
            peaks.extend(streamview.merged_peaks(time, influence_history, corpus, **kwargs))

        # TODO: Code duplication from player
        # Peaks from atoms
        weight_sum: float = 0.0
        for atom in self.atoms.values():
            weight_sum += atom.weight if atom.is_enabled() else 0.0
        for atom in self.atoms.values():
            peak_copies: [Peak] = atom.copy_peaks()
            normalized_weight = atom.weight / weight_sum
            for peak in peak_copies:
                peak.score *= normalized_weight
                peaks.append(peak)

        # Apply merge actions on this level and return
        for merge_action in self._merge_actions.values():
            if merge_action.is_enabled():
                peaks = merge_action.merge(peaks, time, influence_history, corpus, **kwargs)
        return peaks

    def read(self, corpus: Corpus):
        self.logger.debug(f"[read] Init read in streamview {self.name} with corpus {corpus}")
        for atom in self.atoms.values():
            atom.read(corpus)

    @property
    def weight(self) -> float:
        return self._weight.value

    @weight.setter
    def weight(self, value: float):
        self._weight.value = value

    def is_enabled(self):
        return self.enabled.value

    def clear(self):
        for streamview in self.streamviews.values():
            streamview.clear()
        for atom in self.atoms.values():
            atom.clear()

    # TODO: Reimplement
    # def delete_atom(self, name):
    #     '''deleting an atom'''
    #     if not ":" in name:
    #         del self.atoms[name]
    #     else:
    #         head, tail = Tools.parse_path(name)

    # TODO: Reimplement or remove
    # def get_activities(self, date, path=None, weighted=True):
    #     '''get separated activities of children'''
    #     if path != None:
    #         if ':' in path:
    #             head, tail = Tools.split_path(head, tail)
    #             activities = self.atoms[head].get_activities(date, path=tail)
    #         else:
    #             activities = self.atoms[path].get_activities(date)
    #     else:
    #         activities = dict()
    #         for name, atom in self.atoms.iteritems():
    #             activities[name] = atom.merged_peaks(date, weighted=weighted)
    #     if issubclass(type(activities), Tools.SequencedList):
    #         activities = {path: activities}
    #     return activities

    # TODO: Reimplement
    # def set_weight(self, path, weight):
    #     '''set weight of atom addressed at path'''
    #     if not ":" in path:
    #         self.atoms[path].set_weight(weight)
    #     else:
    #         head, tail = Tools.parse_path(path)
    #         self.atoms[head].set_weight(tail, weight)

    # TODO: Reimplement
    # def get_parameter_dict(self):
    #     '''returns info dictionary'''
    #     infodict = {"activity type": str(type(self)), "weight": self.weight, "type": "Streamview"}
    #     infodict["atoms"] = dict()
    #     for a, v in self.atoms.items():
    #         infodict["atoms"][a] = v.get_parameter_dict()
    #     return infodict

    # TODO: reimplement
    # def reset(self, time):
    #     for f in self.atoms.values():
    #         f._reset(time)
