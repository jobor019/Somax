from enum import Enum

from somaxlibrary.CorpusEvent import Note
from somaxlibrary.Parameter import Parametric


class TriggerMode(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class ScheduledObject(Parametric):
    def __init__(self, trigger_mode: TriggerMode):
        super(ScheduledObject, self).__init__()
        self.trigger_mode: trigger_mode = trigger_mode


class ScheduledMidiObject(ScheduledObject):
    def __init__(self, trigger_mode: TriggerMode):
        super(ScheduledMidiObject, self).__init__(trigger_mode)
        self.held_notes: [Note] = []
