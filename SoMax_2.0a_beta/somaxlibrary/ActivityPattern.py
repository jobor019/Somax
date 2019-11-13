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
from somaxlibrary.Peak import Peak
from somaxlibrary.Transforms import AbstractTransform


class AbstractActivityPattern(Parametric):
    def __init__(self, corpus: Corpus = None):
        super(AbstractActivityPattern, self).__init__()
        self.logger = logging.getLogger(__name__)
        self.peaks: [Peak] = []
        self.corpus: Corpus = corpus

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
        self.peaks: [Peak] = []
        self._parse_parameters()

    def insert(self, influences: [AbstractInfluence]) -> None:
        self.logger.debug(f"[insert]: Inserting {len(influences)} influences.")
        for influence in influences:
            onset: float = influence.event.onset
            score: float = self.default_score.value
            transforms: AbstractTransform = influence.transforms
            creation_time: float = influence.time_of_influence
            self.peaks.append(Peak(time=onset, score=score, transform=transforms, creation_time=creation_time))

    def update_peaks(self, new_time: float) -> None:
        for peak in self.peaks:
            peak.score *= np.exp(-np.divide(new_time - peak.last_update_time, self.tau_mem_decay.value))
            peak.time += new_time - peak.last_update_time
            peak.last_update_time = new_time
        self.peaks = [peak for peak in self.peaks if peak.score > self.extinction_threshold.value
                      and peak.time < self.corpus.duration()]

    def reset(self) -> None:
        self.peaks = []
