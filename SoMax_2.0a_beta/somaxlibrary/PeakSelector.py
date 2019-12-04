import logging
import random
from abc import abstractmethod

import numpy as np

from somaxlibrary.ActivityPattern import AbstractActivityPattern
from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.ImprovisationMemory import ImprovisationMemory
from somaxlibrary.Parameter import Parametric

from somaxlibrary.Transforms import AbstractTransform, NoTransform


class AbstractPeakSelector(Parametric):
    TIME_IDX: int = AbstractActivityPattern.TIME_IDX
    SCORE_IDX: int = AbstractActivityPattern.SCORE_IDX
    TRANSFORM_IDX: int = AbstractActivityPattern.TRANSFORM_IDX
    def __init__(self):
        super(AbstractPeakSelector, self).__init__()
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def decide(self, peaks: np.ndarray, influence_history: [(CorpusEvent, (AbstractTransform, ...))],
               corpus: Corpus, **kwargs) -> [CorpusEvent, AbstractTransform]:
        raise NotImplementedError("AbstractPeakSelector.decide is abstract.")

    # def update_parameter_dict(self) -> Dict[str, Union[Parametric, Parameter, Dict]]:
    #     parameters: Dict = {}
    #     for name, parameter in self._parse_parameters().items():
    #         parameters[name] = parameter.update_parameter_dict()
    #     self.parameter_dict = {"parameters": parameters}
    #     return self.parameter_dict


class MaxPeakSelector(AbstractPeakSelector):
    def decide(self, peaks: np.ndarray, influence_history: [(CorpusEvent, (AbstractTransform, ...))],
               corpus: Corpus, **_kwargs) -> [CorpusEvent, int]:
        self.logger.debug("[decide] MaxPeakSelector called.")
        if peaks.size == 0:
            return None
        max_peak_value: float = np.max(peaks[:, self.SCORE_IDX])
        max_peaks_idx: [int] = np.argwhere(peaks[:, self.SCORE_IDX] == max_peak_value)
        peak_idx: int = random.choice(max_peaks_idx)
        return corpus.event_closest(peaks[peak_idx, self.TIME_IDX]), peaks[peak_idx, self.TRANSFORM_IDX]


class DefaultPeakSelector(AbstractPeakSelector):
    def decide(self, _peaks: np.ndarray, influence_history: ImprovisationMemory,
               corpus: Corpus, **_kwargs) -> [CorpusEvent, AbstractTransform]:
        self.logger.debug("[decide] DefaultPeakSelector called.")
        try:
            last_event, _, last_transform = influence_history.get_latest()
            next_state_idx: int = (last_event.state_index + 1) % corpus.length()
            return corpus.event_at(next_state_idx), last_transform
        except IndexError:
            return corpus.event_at(0), (NoTransform(),)
