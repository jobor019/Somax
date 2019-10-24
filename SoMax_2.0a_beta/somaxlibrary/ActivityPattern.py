import inspect
import logging
import sys
from abc import ABC, abstractmethod
from typing import ClassVar

import numpy as np

from somaxlibrary.Influence import AbstractInfluence
from somaxlibrary.Peak import Peak
from somaxlibrary.Transforms import AbstractTransform


class AbstractActivityPattern(ABC):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.peaks: [Peak] = []  # TODO: Ev. optimize. Was sorted in earlier implementations

    @abstractmethod
    def insert(self, influences: [AbstractInfluence]) -> None:
        raise NotImplementedError("AbstractActivityPattern.insert is abstract.")

    @abstractmethod
    def update_peaks(self, new_time: float) -> None:
        raise NotImplementedError("AbstractActivityPattern.update_peaks is abstract.")

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError("AbstractActivityPattern.reset is abstract.")

    @staticmethod
    def classes() -> {str: ClassVar}:
        """Returns class objects for all non-abstract classes in this module."""
        return dict(inspect.getmembers(sys.modules[__name__],
                                       lambda member: inspect.isclass(member) and not inspect.isabstract(
                                           member) and member.__module__ == __name__))


class ClassicActivityPattern(AbstractActivityPattern):
    TAU_MEM_DECAY: float = 2.0  # TODO: Settable param
    T_WIDTH: float = 0.1  # TODO: Settable param
    EXTINCTION_THRESH: float = 0.1  # TODO: Settable param
    DEFAULT_SCORE: float = 1.0

    def __init__(self):
        super(ClassicActivityPattern, self).__init__()
        self.logger.debug("[__init__]: ClassicActivityPattern initialized.")

    def insert(self, influences: [AbstractInfluence]) -> None:
        self.logger.debug(f"[insert]: Inserting {len(influences)} influences.")
        for influence in influences:
            onset: float = influence.event.onset
            score: float = self.DEFAULT_SCORE
            transforms: AbstractTransform = influence.transforms
            creation_time: float = influence.time_of_influence
            self.peaks.append(Peak(time=onset, score=score, transform=transforms, creation_time=creation_time))

    def update_peaks(self, new_time: float) -> None:
        for peak in self.peaks:
            peak.score *= np.exp(-np.divide(new_time - peak.last_update_time, self.TAU_MEM_DECAY))
            peak.time += new_time - peak.last_update_time
            peak.last_update_time = new_time
        self.peaks = [peak for peak in self.peaks if peak.score > self.EXTINCTION_THRESH]

    def reset(self) -> None:
        self.peaks = []
