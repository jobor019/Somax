from abc import ABC
from enum import Enum

from somaxlibrary.CorpusEvent import Note


class TriggerMode(Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class ScheduledObject(ABC):
    def __init__(self, trigger_mode: TriggerMode):
        self.trigger_mode: TriggerMode = trigger_mode


class ScheduledMidiObject(ScheduledObject):
    def __init__(self, trigger_mode: TriggerMode):
        super(ScheduledMidiObject, self).__init__(trigger_mode)
        self.held_notes: [Note] = []
