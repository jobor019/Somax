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
from somaxlibrary.Peaks import Peaks


class AbstractActivityPattern(Parametric):
    SCORE_IDX = 0
    TIME_IDX = 1
    TRANSFORM_IDX = 2

    def __init__(self, corpus: Corpus = None):
        super(AbstractActivityPattern, self).__init__()
        self.logger = logging.getLogger(__name__)
        self._peaks: Peaks = Peaks.create_empty()
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
    def peaks(self) -> Peaks:
        """ Returns a copy of peaks"""
        return self._peaks

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
        self._peaks: Peaks = Peaks.create_empty()
        self.last_update_time: float = 0.0
        self._parse_parameters()

    def insert(self, influences: [AbstractInfluence]) -> None:
        self.logger.debug(f"[insert]: Inserting {len(influences)} influences.")
        scores: [float] = []
        times: [float] = []
        transform_hashes: [int] = []
        for influence in influences:
            times.append(influence.event.onset)
            scores.append(self.default_score.value)
            transform_hashes.append(influence.transform_hash)
        self._peaks.append(scores, times, transform_hashes)

    def update_peaks(self, new_time: float) -> None:
        self._peaks.scores *= np.exp(-np.divide(new_time - self.last_update_time, self.tau_mem_decay.value))
        self._peaks.times += new_time - self.last_update_time
        self.last_update_time = new_time
        indices_to_remove: np.ndarray = np.where((self._peaks.scores <= self.extinction_threshold.value)
                                                 | (self._peaks.times >= self.corpus.duration()))
        self._peaks.remove(indices_to_remove)

    def clear(self) -> None:
        self._peaks = Peaks.create_empty()
