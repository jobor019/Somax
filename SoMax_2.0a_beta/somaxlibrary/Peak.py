from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Transforms import AbstractTransform


class Peak:

    def __init__(self, time: float, score: float, event: CorpusEvent, transforms: [AbstractTransform]):
        self.time: float = time      # absolute or relative position in the memory, shifting over time
        self.score: float = score    # value of peak, decaying over time
        self.event: CorpusEvent = event
        self.transforms: [AbstractTransform] = transforms   # transforms to be applied to peak

    def __repr__(self):
        return f"Peak with time {self.time}, score {self.score} and event with index {self.event.state_index}"
