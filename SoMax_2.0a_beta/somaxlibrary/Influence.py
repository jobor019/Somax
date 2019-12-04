from abc import ABC

from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Transforms import AbstractTransform


class AbstractInfluence(ABC):
    """ An influence is an event matched by a MemorySpace/influence call before it's transformed into a peak"""

    def __init__(self, event: CorpusEvent, transform_hash: int, **_kwargs):
        self.event: CorpusEvent = event
        self.transform_hash: int = transform_hash


class ClassicInfluence(AbstractInfluence):

    def __init__(self, event: CorpusEvent, transform_hash: int, **_kwargs):
        super(ClassicInfluence, self).__init__(event, transform_hash)

    # def __repr__(self):
    #     return f"ClassicInfluence(onset={self.event.onset},time={self.time_of_influence})"
