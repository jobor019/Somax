from abc import ABC, abstractmethod

from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Peak import Peak
from somaxlibrary.Transforms import AbstractTransform, NoTransform


class AbstractPeakSelector(ABC):

    @abstractmethod
    def decide(self, peaks: [Peak], influence_history: [(CorpusEvent, AbstractTransform)],
               corpus: Corpus, **kwargs) -> [CorpusEvent, AbstractTransform]:
        raise NotImplementedError("AbstractPeakSelector.decide is abstract.")


class MaxPeakSelector(AbstractPeakSelector):
    def decide(self, peaks: [Peak], influence_history: [(CorpusEvent, AbstractTransform)],
               corpus: Corpus, **_kwargs) -> [CorpusEvent, AbstractTransform]:
        if not peaks:
            return None
        max_peak: Peak = max(peaks, lambda p: p.score)
        raise NotImplementedError("Not implemented???") # TODO. Return None if empty!!


class DefaultPeakSelector(AbstractPeakSelector):
    def decide(self, _peaks: [Peak], influence_history: (CorpusEvent, AbstractTransform),
               corpus: Corpus, **_kwargs) -> [CorpusEvent, AbstractTransform]:
        if not influence_history:
            return corpus.event_at(0), NoTransform()
        last_event, last_transform = influence_history[-1]
        next_state_idx: int = last_event.state_index + 1 % corpus.length()
        return corpus.event_at(next_state_idx), last_transform
