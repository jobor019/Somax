import logging
from abc import ABC, abstractmethod

import numpy as np

from somaxlibrary.Influence import AbstractInfluence
from somaxlibrary.Peak import Peak
from somaxlibrary.Transforms import AbstractTransform


class AbstractActivityPattern(ABC):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def insert(self, influences: [AbstractInfluence]) -> None:
        raise NotImplementedError("AbstractActivityPattern.insert is abstract.")

    @abstractmethod
    def update(self, new_time: float) -> None:
        raise NotImplementedError("AbstractActivityPattern.update is abstract.")

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError("AbstractActivityPattern.reset is abstract.")


class ClassicActivityPattern(AbstractActivityPattern):
    TAU_MEM_DECAY: float = 2.0
    T_WIDTH: float = 0.1
    EXTINCTION_THRESH: float = 0.1
    DEFAULT_SCORE: float = 1.0

    def __init__(self):
        super(ClassicActivityPattern, self).__init__()
        self.logger.debug("[__init__]: ClassicActivityPattern initialized.")
        self.peaks: [Peak] = []  # TODO: Ev. optimize. Was sorted in earlier implementations

    def insert(self, influences: [AbstractInfluence]) -> None:
        self.logger.debug(f"[insert]: Inserting {len(influences)} influences.")
        for influence in influences:
            onset: float = influence.event.onset
            score: float = self.DEFAULT_SCORE
            transforms: [AbstractTransform] = influence.transforms
            creation_time: float = influence.time_of_influence
            self.peaks.append(Peak(time=onset, score=score, transforms=transforms, creation_time=creation_time))

    def update(self, new_time: float) -> None:
        for peak in self.peaks:
            peak.score *= np.exp(-np.divide(new_time - peak.creation_time, self.TAU_MEM_DECAY))
            peak.time += new_time - peak.creation_time
        self.peaks = [peak for peak in self.peaks if peak.score > self.EXTINCTION_THRESH]

    def reset(self) -> None:
        self.peaks = []
