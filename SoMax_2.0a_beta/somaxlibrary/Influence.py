from abc import ABC

from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Transforms import AbstractTransform


class AbstractInfluence(ABC):
    """ An influence is an event matched by a MemorySpace/influence call before it's transformed into a peak"""

    def __init__(self, event: CorpusEvent, time_of_influence: float, transforms: [AbstractTransform], **_kwargs):
        self.event: CorpusEvent = event
        self.time_of_influence: float = time_of_influence
        self.transforms: [AbstractTransform] = transforms


class ClassicInfluence(AbstractInfluence):

    def __init__(self, event: CorpusEvent, time_of_influence: float, transforms: [AbstractTransform], **_kwargs):
        super(ClassicInfluence, self).__init__(event, time_of_influence, transforms)

    def __repr__(self):
        return f"Classic Influence with onset at {self.event.onset} influenced at time {self.time_of_influence}."