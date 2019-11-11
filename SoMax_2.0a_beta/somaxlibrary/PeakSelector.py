import logging
import random
from abc import ABC, abstractmethod
from typing import Dict

from Parametric import Parametric
from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.HasInfoDict import HasInfoDict
from somaxlibrary.Peak import Peak
from somaxlibrary.Transforms import AbstractTransform, NoTransform


class AbstractPeakSelector(Parametric, HasInfoDict):
    def __init__(self):
        super(AbstractPeakSelector, self).__init__()
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def decide(self, peaks: [Peak], influence_history: [(CorpusEvent, (AbstractTransform, ...))],
               corpus: Corpus, **kwargs) -> [CorpusEvent, AbstractTransform]:
        raise NotImplementedError("AbstractPeakSelector.decide is abstract.")

    def info_dict(self) -> Dict:
        parameters: Dict = {}
        for name, parameter in self.parameters.items():
            parameters[name] = parameter.info_dict()
        return {"parameters": parameters}


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
