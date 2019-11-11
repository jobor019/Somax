import logging
import random
from abc import abstractmethod
from typing import Dict, Union

from somaxlibrary import Parameter
from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Parameter import Parametric, Parameter
from somaxlibrary.Peak import Peak
from somaxlibrary.Transforms import AbstractTransform, NoTransform


class AbstractPeakSelector(Parametric):
    def __init__(self):
        super(AbstractPeakSelector, self).__init__()
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def decide(self, peaks: [Peak], influence_history: [(CorpusEvent, (AbstractTransform, ...))],
               corpus: Corpus, **kwargs) -> [CorpusEvent, AbstractTransform]:
        raise NotImplementedError("AbstractPeakSelector.decide is abstract.")

    # def update_parameter_dict(self) -> Dict[str, Union[Parametric, Parameter, Dict]]:
    #     parameters: Dict = {}
    #     for name, parameter in self._parse_parameters().items():
    #         parameters[name] = parameter.update_parameter_dict()
    #     self.parameter_dict = {"parameters": parameters}
    #     return self.parameter_dict


class MaxPeakSelector(AbstractPeakSelector):
    def decide(self, peaks: [Peak], influence_history: [(CorpusEvent, (AbstractTransform, ...))],
               corpus: Corpus, **_kwargs) -> [CorpusEvent, AbstractTransform]:
        self.logger.debug("[decide] MaxPeakSelector called.")
        if not peaks:
            return None
        max_peak: Peak = max(peaks, key=lambda p: p.score)
        max_peaks: [Peak] = [p for p in peaks if p.score == max_peak.score]
        selected_peak: Peak = random.choice(max_peaks)
        return corpus.event_closest(selected_peak.time), selected_peak.transforms


class DefaultPeakSelector(AbstractPeakSelector):
    def decide(self, _peaks: [Peak], influence_history: (CorpusEvent, (AbstractTransform, ...)),
               corpus: Corpus, **_kwargs) -> [CorpusEvent, AbstractTransform]:
        self.logger.debug("[decide] DefaultPeakSelector called.")
        if not influence_history:
            return corpus.event_at(0), (NoTransform(),)
        last_event, last_transform = influence_history[-1]
        next_state_idx: int = (last_event.state_index + 1) % corpus.length()
        return corpus.event_at(next_state_idx), last_transform
