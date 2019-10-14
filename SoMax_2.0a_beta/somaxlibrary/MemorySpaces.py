import logging
from abc import ABC, abstractmethod
from collections import deque
from typing import TypeVar, Any, Tuple

from somaxlibrary import Transforms
from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Exceptions import InvalidLabelInput
from somaxlibrary.Peak import Peak
from somaxlibrary.ProperLabels import ProperAbstractLabel
from somaxlibrary.Transforms import AbstractTransform


class AbstractMemorySpace(ABC):
    def __init__(self, corpus: Corpus, label_type: TypeVar = ProperAbstractLabel, history_len: int = 3,
                 transforms: [AbstractTransform] = None, **kwargs):
        """ Note: args, kwargs can be used if additional information is need to construct the data structure."""
        self.logger = logging.getLogger(__name__)
        self.corpus: Corpus = corpus
        self.label_type: TypeVar = label_type
        self.influence_history: deque = deque([], history_len)
        # TODO: Should also check that they work for this label
        self.transforms: [TypeVar] = transforms if transforms else [Transforms.NoTransform()]
        # self.available = True       # TODO: Implement if needed, save for later

    @abstractmethod
    def build(self, **kwargs) -> None:
        pass

    def influence(self, event_data: Any, **kwargs) -> [Peak]:
        try:
            label: int = self.label_type.classify(event_data, **kwargs)
        except InvalidLabelInput:
            self.logger.error(f"Could not match input {event_data} with a label of type {self.label_type}.")
            raise  # TODO: Maybe remove
        self.influence_history.append(label)
        peaks = self._matches(**kwargs)
        return peaks

    @abstractmethod
    def _matches(self, **kwargs) -> [Peak]:
        pass

    # TODO: Implement if needed
    # def is_available(self):
    #     return bool(self.available)

    def reset(self):
        self.influence_history.clear()


class NGramMemorySpace(AbstractMemorySpace):
    def __init__(self, corpus: Corpus, label_type: TypeVar = ProperAbstractLabel, history_len: int = 3,
                 transforms: [TypeVar] = None, **kwargs):
        super(NGramMemorySpace, self).__init__(corpus, label_type, history_len, transforms, **kwargs)
        self.logger.debug(f"[__init__] Initializing (TEMP)NGramMemorySpace with corpus {corpus}, "
                          f"label type {label_type}, history length {history_len} and transforms {transforms}")
        self.structured_data: {Tuple[int, ...]: [CorpusEvent]} = {}
        self.ngram_size: int = history_len

    def __repr__(self):
        return f"NGramMemorySpace with size {self.ngram_size}, type {self.label_type} and corpus {self.corpus}."

    def build(self, **kwargs) -> None:
        self.structured_data = {}
        labels: deque = deque([], self.ngram_size)
        for event in self.corpus.events:
            label: int = event.get_label(self.label_type)
            labels.append(label)
            if len(labels) < self.ngram_size:
                continue
            else:
                key: Tuple[int, ...] = tuple(labels)
                value: CorpusEvent = event
                if key in self.structured_data:
                    self.structured_data[key].append(value)
                else:
                    self.structured_data[key] = [value]

    def _matches(self, **kwargs) -> [Peak]:
        if len(self.influence_history) < self.ngram_size:
            return []
        else:
            peaks: [Peak] = []
            # TODO (Once tested): handle transposes
            for transform in self.transforms:
                # Inverse transform of input (equivalent to transform of memory)
                key: Tuple[int, ...] = tuple(transform.decode(self.influence_history))
                try:
                    events: [CorpusEvent] = self.structured_data[key]
                    for event in events:
                        peaks.append(Peak(event.onset, 1.0, event, transform))
                    return peaks
                except KeyError:
                    return []
