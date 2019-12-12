from collections import deque

from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Transforms import AbstractTransform


class ImprovisationMemory:
    MAX_HISTORY_LEN = 100

    def __init__(self):
        self._history: deque[(CorpusEvent, float, (AbstractTransform, ...))] = deque('', self.MAX_HISTORY_LEN)

    def append(self, event: CorpusEvent, trigger_time: float, transforms: (AbstractTransform, ...)) -> None:
        self._history.append((event, trigger_time, transforms))

    def get(self, index: int) -> (CorpusEvent, float, (AbstractTransform, ...)):
        return self._history[index]

    def get_latest(self) -> (CorpusEvent, float, (AbstractTransform, ...)):
        return self._history[len(self._history) - 1]
