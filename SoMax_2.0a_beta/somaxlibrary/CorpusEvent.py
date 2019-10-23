import logging
from typing import Any, ClassVar

from somaxlibrary.Exceptions import InvalidLabelInput


class Note:
    def __init__(self, pitch: int, velocity: int, channel: int, onset: float, duration: float):
        self.logger = logging.getLogger(__name__)
        self.pitch: int = pitch
        self.velocity: int = velocity
        self.channel: int = channel
        self.onset: float = onset  # in relation to CorpusEvent onset
        self.duration: float = duration

    def __repr__(self):
        return f"Note object with pitch {self.pitch}"


class CorpusEvent:
    def __init__(self, state_index, tempo, onset, duration, chroma, pitch, notes: [{str: Any}],
                 timing_type: str):
        self.logger = logging.getLogger(__name__)
        self.state_index: int = state_index
        self.tempo: float = tempo
        self.onset: float = onset
        self.duration: float = duration
        self.chroma: [float] = chroma
        self.pitch: int = pitch
        self.notes: [Note] = self._parse_notes(notes, timing_type)
        self.labels: {ClassVar: int} = {}  # ClassVar[AbstractLabel]

    @staticmethod
    def _parse_notes(notes: [{str: Any}], timing_type: str) -> [Note]:
        parsed_notes: [Note] = []
        for note in notes:
            n = Note(note["pitch"], note["velocity"], note["channel"], note["time"][timing_type][0],
                     note["time"][timing_type][1])
            parsed_notes.append(n)
        return parsed_notes

    def classify(self, label_classes: {str: ClassVar}) -> None:
        for _class_name, label_class in label_classes.items():
            try:
                label: int = label_class.classify(self)
            except InvalidLabelInput:
                self.logger.error(f"Classification failed for label class {label_class} with input {self}.")
                raise
            self.labels[label_class] = label

    def get_label(self, label_type: ClassVar) -> int:
        # TODO: Update docstring when renaming ProperLabel
        """Valid keys are any class objects (note: object, not instance) existing in ProperLabel

        Raises
        ------
        KeyError if label is invalid
        """
        return self.labels[label_type]

    def __repr__(self):
        return f"CorpusEvent object with labels {self.labels}."
