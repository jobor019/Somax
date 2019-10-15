import logging
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Tuple, ClassVar

from somaxlibrary import Transforms
from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Exceptions import InvalidLabelInput
from somaxlibrary.Peak import Peak
from somaxlibrary.ProperLabels import ProperAbstractLabel, ProperMelodicLabel
from somaxlibrary.Transforms import AbstractTransform


class AbstractMemorySpace(ABC):
    def __init__(self, corpus: Corpus = None, label_type: ClassVar[ProperAbstractLabel] = ProperAbstractLabel,
                 history_len: int = 3, transforms: [AbstractTransform] = None, **kwargs):
        """ Note: args, kwargs can be used if additional information is need to construct the data structure."""
        self.logger = logging.getLogger(__name__)
        self.corpus: Corpus = corpus
        self.label_type: ClassVar[ProperAbstractLabel] = label_type
        self.influence_history: deque = deque([], history_len)
        # TODO: Should also check that they work for this label
        self.transforms: [AbstractTransform] = transforms if transforms else [Transforms.NoTransform()]
        # self.available = True       # TODO: Implement if needed, save for later

    @abstractmethod
    def read(self, corpus: Corpus, **kwargs) -> None:
        pass

    @abstractmethod
    def influence(self, influence_type: str, influence_data: Any, **kwargs) -> [Peak]:
        pass

    # TODO: Implement if needed
    # def is_available(self):
    #     return bool(self.available)

    # TODO: Implement when needed
    # @abstractmethod
    # def _reset(self) -> None:
    #     pass

    # TODO: Implement when needed
    # def add_transform(self, transform: [AbstractTransform]) -> None:
    #     pass


class NGramMemorySpace(AbstractMemorySpace):
    def __init__(self, corpus: Corpus = None, label_type: ClassVar[ProperAbstractLabel] = ProperMelodicLabel,
                 history_len: int = 3, transforms: [AbstractTransform] = None, **kwargs):
        super(NGramMemorySpace, self).__init__(corpus, label_type, history_len, transforms, **kwargs)
        self.logger.debug(f"[__init__] Initializing NGramMemorySpace with corpus {corpus}, "
                          f"label type {label_type}, history length {history_len} and transforms {transforms}")
        self.structured_data: {Tuple[int, ...]: [CorpusEvent]} = {}
        self.ngram_size: int = history_len

    def __repr__(self):
        return f"NGramMemorySpace with size {self.ngram_size}, type {self.label_type} and corpus {self.corpus}."

    def read(self, corpus: Corpus, **kwargs) -> None:
        self.corpus = corpus
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

    def influence(self, influence_type: str, influence_data: Any, **kwargs) -> [Peak]:
        try:
            label: int = self.label_type.classify(influence_data, **kwargs)
        except InvalidLabelInput:
            self.logger.error(f"Could not match input {influence_data} with a label of type {self.label_type}.")
            raise  # TODO: Maybe remove/replace with a return
        self.influence_history.append(label)

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
                        peaks.append(Peak(time=event.onset, score=1.0, event=event, transforms=transform))
                    return peaks
                except KeyError:
                    return []
        return peaks
