import inspect
import logging
import sys
from abc import abstractmethod
from typing import ClassVar, Dict, Union

import numpy as np

from somaxlibrary.Corpus import Corpus
from somaxlibrary.Influence import AbstractInfluence
from somaxlibrary.Parameter import Parameter
from somaxlibrary.Parameter import Parametric


class AbstractActivityPattern(Parametric):
    SCORE_IDX = 0
    TIME_IDX = 1
    TRANSFORM_IDX = 2

    def __init__(self, corpus: Corpus = None):
        super(AbstractActivityPattern, self).__init__()
        self.logger = logging.getLogger(__name__)
        self._peaks: np.ndarray = np.empty((0, 3))  # shape: (N, 3) with columns: time, score, transformation_hash
        self.corpus: Corpus = corpus

    @abstractmethod
    def insert(self, influences: [AbstractInfluence]) -> None:
        raise NotImplementedError("AbstractActivityPattern.insert is abstract.")

    @abstractmethod
    def update_peaks(self, new_time: float) -> None:
        raise NotImplementedError("AbstractActivityPattern.update_peaks is abstract.")

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError("AbstractActivityPattern.reset is abstract.")

    @staticmethod
    def classes() -> {str: ClassVar}:
        """Returns class objects for all non-abstract classes in this module."""
        return dict(inspect.getmembers(sys.modules[__name__],
                                       lambda member: inspect.isclass(member) and not inspect.isabstract(
                                           member) and member.__module__ == __name__))

    @property
    def peaks(self) -> np.ndarray:
        """ Returns a copy of peaks"""
        return np.copy(self.peaks)

    def update_parameter_dict(self) -> Dict[str, Union[Parametric, Parameter, Dict]]:
        parameters: Dict = {}
        for name, parameter in self._parse_parameters().items():
            parameters[name] = parameter.update_parameter_dict()
        self.parameter_dict = {"parameters": parameters}
        return self.parameter_dict




class ClassicActivityPattern(AbstractActivityPattern):

    def __init__(self):
        super(ClassicActivityPattern, self).__init__()
        self.logger.debug("[__init__]: ClassicActivityPattern initialized.")
        self.tau_mem_decay: Parameter = Parameter(2.0, 0.0, None, 'float', "Very unclear param")  # TODO
        self.extinction_threshold: Parameter = Parameter(0.1, 0.0, None, 'float', "Score below which peaks are removed")
        self.default_score: Parameter = Parameter(1.0, None, None, 'float', "Value of a new peaks upon creation.")
        self.peaks: np.ndarray = np.empty((0, 3))  # shape: (N, 3) with columns: time, score, transformation_hash
        self.last_update_time: float = 0.0
        self._parse_parameters()

    def insert(self, influences: [AbstractInfluence]) -> None:
        self.logger.debug(f"[insert]: Inserting {len(influences)} influences.")
        peaks_to_insert: [float, float, int] = []
        for influence in influences:
            onset: float = influence.event.onset
            score: float = self.default_score.value
            transform_hash: int = influence.transform_hash
            peaks_to_insert.append([onset, score, transform_hash])
        self.peaks = np.concatenate((self.peaks, peaks_to_insert))

    def update_peaks(self, new_time: float) -> None:
        self.peaks[:, self.SCORE_IDX] *= np.exp(-np.divide(new_time - self.last_update_time, self.tau_mem_decay.value))
        self.peaks[:, self.TIME_IDX] += new_time - self.last_update_time
        self.last_update_time = new_time
        idx_to_keep: np.ndarray = (self.peaks[:, self.SCORE_IDX] > self.extinction_threshold.value) \
                                    & (self.peaks[:, self.TIME_IDX] < self.corpus.duration())
        self.peaks = self.peaks[idx_to_keep, :]

    def clear(self) -> None:
        self.peaks = []
