import copy
import logging
from typing import ClassVar, Dict, Union

import numpy as np

from somaxlibrary.ActivityPattern import AbstractActivityPattern
from somaxlibrary.Corpus import Corpus
from somaxlibrary.Influence import AbstractInfluence
from somaxlibrary.Labels import MelodicLabel, AbstractLabel
from somaxlibrary.MemorySpaces import AbstractMemorySpace
from somaxlibrary.Parameter import Parametric, Parameter, ParamWithSetter

from somaxlibrary.Transforms import AbstractTransform


class Atom(Parametric):
    def __init__(self, name: str, weight: float, label_type: ClassVar[AbstractLabel],
                 activity_type: ClassVar[AbstractActivityPattern], memory_type: ClassVar[AbstractMemorySpace],
                 corpus: Corpus, self_influenced: bool, transforms: [(ClassVar[AbstractTransform], ...)]):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"[__init__ Creating atom '{name}'.")
        self.name = name
        self._weight: Parameter = Parameter(weight, 0.0, None, 'float', "Relative scaling of atom peaks.")
        self.enabled: Parameter = Parameter(True, False, True, "bool", "Enables this Atom.")
        self.activity_pattern: AbstractActivityPattern = activity_type()  # creates activity
        self.memory_space: AbstractMemorySpace = memory_type(corpus, label_type, transforms)
        self._self_influenced: Parameter = Parameter(self_influenced, 0, 1, 'bool',
                                                     "Whether new events creates by player should influence this atom or not.")
        if corpus:
            self.read(corpus)

        self._parse_parameters()

    def update_parameter_dict(self) -> Dict[str, Union[Parametric, Parameter, Dict]]:
        parameters = {}
        for name, parameter in self._parse_parameters().items():
            parameters[name] = parameter.update_parameter_dict()
        self.parameter_dict = {"memory_space": self.memory_space.update_parameter_dict(),
                               "activity_pattern": self.activity_pattern.update_parameter_dict(),
                               "parameters": parameters}
        return self.parameter_dict

    def read(self, corpus):
        self.logger.debug(f"[read]: Reading corpus {corpus}.")
        self.memory_space.read(corpus)
        self.activity_pattern.corpus = corpus

    # TODO: Legacy?
    # set current weight of atom
    def set_weight(self, weight: float):
        self.logger.debug("[set_weight] Atom {} setting weight to {}.".format(self.name, weight))
        self.weight = weight

    # influences the memory with incoming data
    def influence(self, label: AbstractLabel, time: float, **kwargs):
        """ Raises: InvalidLabelInput"""
        matched_events: [AbstractInfluence] = self.memory_space.influence(label, time, **kwargs)
        if matched_events:
            self.activity_pattern.update_peaks(time)
            self.activity_pattern.insert(matched_events)  # we insert the events into the activity profile

    def set_label(self, label: ClassVar[AbstractLabel]):
        self.memory_space.set_label(label)

    def update_peaks(self, time: float) -> None:
        self.activity_pattern.update_peaks(time)


    @property
    def weight(self) -> float:
        return self._weight.value

    @weight.setter
    def weight(self, value: float):
        self._weight.value = value

    @property
    def self_influenced(self) -> float:
        return self._self_influenced.value

    @self_influenced.setter
    def self_influenced(self, self_influenced: bool):
        self._self_influenced.value = self_influenced

    def clear(self):
        self.activity_pattern.clear()
        self.memory_space.clear()

    def is_enabled(self):
        return self.enabled.value

    # TODO: Reimplement
    # external method to fetch properties of the atom
    # def get_parameter_dict(self):
    #     infodict = {"activity": self.activityPattern.__desc__(), "memory": self.memory_space.__desc__(),
    #                 "event_type": self.memory_space.event_type.__desc__(),
    #                 "label_type": self.memory_space.label_type.__desc__(),
    #                 "contents_type": self.memory_space.contents_type.__desc__(), "name": self.name,
    #                 "weight": self.weight, "type": "Atom", "active": self.active}
    #     if self.current_file != None:
    #         infodict["current_file"] = str(self.current_file)
    #         infodict["length"] = len(self.memory_space)
    #     else:
    #         infodict["current_file"] = "None"
    #         infodict["length"] = 0
    #     return infodict

    # def isAvailable(self):
    #     return self.activityPattern.isAvailable() and self.memory_space.is_available()

    # TODO: Reimplement
    # def reset(self, time):
    #     self.activity_pattern.reset(time)
