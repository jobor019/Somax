from abc import ABC
from enum import Enum

from Parameter import Parameter
from Parametric import Parametric
from somaxlibrary.CorpusEvent import Note


class TriggerMode(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class ScheduledObject(ABC, Parametric):
    def __init__(self, trigger_mode: TriggerMode):
        super(ScheduledObject, self).__init__()
        self._trigger_mode: Parameter = Parameter(trigger_mode, None, None, 'manual|automatic', "TODO")     # TODO

    @property
    def trigger_mode(self):
        return self._trigger_mode.value

    @trigger_mode.setter
    def trigger_mode(self, value):
        self._trigger_mode.value = value


class ScheduledMidiObject(ScheduledObject):
    def __init__(self, trigger_mode: TriggerMode):
        super(ScheduledMidiObject, self).__init__(trigger_mode)
        self.held_notes: [Note] = []
