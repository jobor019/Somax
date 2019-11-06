import copy
import logging
from typing import ClassVar

from somaxlibrary import MemorySpaces
from somaxlibrary.ActivityPattern import AbstractActivityPattern, ClassicActivityPattern
from somaxlibrary.Corpus import Corpus
from somaxlibrary.Influence import AbstractInfluence
from somaxlibrary.Labels import MelodicLabel, AbstractLabel
from somaxlibrary.MemorySpaces import AbstractMemorySpace
from somaxlibrary.Peak import Peak
from somaxlibrary.Transforms import AbstractTransform


class Atom(object):
    def __init__(self, name: str, weight: float, label_type: ClassVar[AbstractLabel],
                 activity_type: ClassVar[AbstractActivityPattern], memory_type: ClassVar[AbstractMemorySpace],
                 corpus: Corpus, self_influenced: bool, transforms: [(ClassVar[AbstractTransform],...)]):
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"[__init__ Creating atom '{name}'.")
        self.weight: float = weight
        self.activity_pattern: AbstractActivityPattern = activity_type()  # creates activity
        self.memory_space: AbstractMemorySpace = memory_type(corpus, label_type, transforms)
        self.name = name
        self.active = False
        self.self_influenced: bool = self_influenced
        if corpus:
            self.read(corpus, label_type)

    def read(self, corpus, label_type=ClassVar[MelodicLabel]):
        self.logger.debug(f"[read]: Reading corpus {corpus}.")
        self.memory_space.read(corpus)
        self.logger.debug(f"[read]: Corpus successfully read.")

    # set current weight of atom
    def set_weight(self, weight: float):
        self.logger.debug("[set_weight] Atom {} setting weight to {}.".format(self.name, weight))
        self.weight = weight

    # influences the memory with incoming data
    def influence(self, label: AbstractLabel, time: float, **kwargs):
        """ Raises: InvalidLabelInput"""
        matched_events: [AbstractInfluence] = self.memory_space.influence(label, time, **kwargs)
        if matched_events:
            self.activity_pattern.insert(matched_events)  # we insert the events into the activity profile

    def update_peaks(self, time: float) -> None:
        self.activity_pattern.update_peaks(time)

    def copy_peaks(self) -> [Peak]:
        """Returns shallow copies of all peaks. """
        peak_copies: [Peak] = []
        for peak in self.activity_pattern.peaks:
            peak_copies.append(copy.copy(peak))
        return peak_copies

    # TODO: Reimplement
    # external method to fetch properties of the atom
    # def get_info_dict(self):
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
