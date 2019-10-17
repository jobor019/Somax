from somaxlibrary.Transforms import AbstractTransform


class Peak:

    def __init__(self, time: float, score: float, transforms: [AbstractTransform], creation_time: float):
        """
        Notes
        -----
        A peak does not contain a corpus event, as it's not pointing to a specific event but
        a shifting position in time. """
        self.time: float = time  # absolute or relative position in the memory (in report: xi)
        self.score: float = score  # value of peak, decaying over time
        self.transforms: [AbstractTransform] = transforms  # transforms to be applied to peak
        self.creation_time: float = creation_time

    def __repr__(self):
        return f"Peak with time {self.time}, score {self.score}."
