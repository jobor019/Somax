import inspect
import logging
import sys
from abc import ABC, abstractmethod
from collections import deque
from typing import Tuple, ClassVar

from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Exceptions import InvalidLabelInput
from somaxlibrary.Influence import AbstractInfluence, ClassicInfluence
from somaxlibrary.Labels import AbstractLabel, MelodicLabel
from somaxlibrary.Peak import Peak
from somaxlibrary.Transforms import AbstractTransform
from somaxlibrary.Transforms import NoTransform


class AbstractMemorySpace(ABC):
    """ MemorySpaces determine how events are matched to labels """

    def __init__(self, corpus: Corpus = None, label_type: ClassVar[AbstractLabel] = AbstractLabel,
                 transforms: [AbstractTransform] = None, **_kwargs):
        """ Note: kwargs can be used if additional information is need to construct the data structure."""
        self.logger = logging.getLogger(__name__)
        self.corpus: Corpus = corpus
        self.label_type: ClassVar[AbstractLabel] = label_type
        # TODO: Should also check that they work for this label
        self.transforms: [AbstractTransform] = transforms if transforms else [NoTransform()]
        # self.available = True       # TODO: Implement if needed, save for later

    @abstractmethod
    def read(self, corpus: Corpus, **_kwargs) -> None:
        raise NotImplementedError("AbstractMemorySpace.read is abstract.")

    @abstractmethod
    def influence(self, label: AbstractLabel, time: float, **_kwargs) -> [Peak]:
        raise NotImplementedError("AbstractMemorySpace.influence is abstract.")

    @staticmethod
    def classes() -> {str: ClassVar}:
        """Returns class objects for all non-abstract classes in this module."""
        return dict(inspect.getmembers(sys.modules[__name__],
                                       lambda member: inspect.isclass(member) and not inspect.isabstract(
                                           member) and member.__module__ == __name__))

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
    def __init__(self, corpus: Corpus = None, label_type: ClassVar[AbstractLabel] = MelodicLabel,
                 transforms: [AbstractTransform] = None, history_len: int = 3, **_kwargs):
        super(NGramMemorySpace, self).__init__(corpus, label_type, transforms)
        self.logger.debug(f"[__init__] Initializing NGramMemorySpace with corpus {corpus}, "
                          f"label type {label_type}, history length {history_len} and transforms {transforms}")
        self.structured_data: {Tuple[int, ...]: [CorpusEvent]} = {}
        self.ngram_size: int = history_len
        self.influence_history: deque[AbstractLabel] = deque([], history_len)

    def __repr__(self):
        return f"NGramMemorySpace with size {self.ngram_size}, type {self.label_type} and corpus {self.corpus}."

    def read(self, corpus: Corpus, **kwargs) -> None:
        self.corpus = corpus
        self.structured_data = {}
        labels: deque = deque([], self.ngram_size)
        for event in self.corpus.events:
            label: int = event.label(self.label_type)
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

    def influence(self, label: AbstractLabel, time: float, **kwargs) -> [AbstractInfluence]:
        """ Raises: InvalidLabelInput"""
        if not type(label) == self.label_type:
            raise InvalidLabelInput(f"An atom with type {self.label_type} can't handle labels of type {type(label)}.")
        self.influence_history.append(label)
        if len(self.influence_history) < self.ngram_size:
            return []
        else:
            matches: [AbstractInfluence] = []
            # TODO (Once tested): handle transposes
            # TODO 2: Handle combinations of transforms, not just individual transforms
            for transform in self.transforms:
                # Inverse transform of input (equivalent to transform of memory)
                key: Tuple[int, ...] = tuple(transform.decode(self.influence_history))
                try:
                    matching_events: [CorpusEvent] = self.structured_data[key]
                    for event in matching_events:
                        # TODO: Sends list of single transform only rn
                        matches.append(ClassicInfluence(event, time, [transform]))
                    return matches
                except KeyError:  # no matches found
                    return []
        return matches
