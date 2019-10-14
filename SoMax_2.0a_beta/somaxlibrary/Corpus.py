import json
from typing import Any, Dict

from somaxlibrary import Events
from somaxlibrary.Events import AbstractContents
from somaxlibrary.Exceptions import InvalidJsonFormat
from somaxlibrary.Tools import SequencedList


class Note:
    def __init__(self, pitch: int, velocity: int, channel: int, absolute_onset: float, absolute_duration: float,
                 relative_onset: float, relative_duration: float):
        self.pitch: int = pitch
        self.velocity: int = velocity
        self.channel: int = channel
        self.absolute_onset: float = absolute_onset  # in relation to CorpusEvent absolute_onset
        self.absolute_duration: float = absolute_duration
        self.relative_onset: float = relative_onset  # in relation to CorpusEvent relative_onset
        self.relative_duration: float = relative_duration

    def __repr__(self):
        return f"Note object with pitch {self.pitch}"


class CorpusState:
    def __init__(self, state_index, tempo, absolute_onset, absolute_duration, relative_onset, relative_duration, chroma,
                 pitch, notes: [{str: Any}]):
        self.state_index: int = state_index
        self.tempo: float = tempo
        self.absolute_onset: float = absolute_onset
        self.absolute_duration: float = absolute_duration
        self.relative_onset: float = relative_onset
        self.relative_duration: float = relative_duration
        self.chroma: [int] = chroma
        self.pitch: int = pitch
        self.notes: [Note] = self._parse_notes(notes)

    def __repr__(self):
        return f"CorpusState object with pitch {self.pitch}, chroma {self.chroma} and {len(self.notes)} note(s)"

    @staticmethod
    def _parse_notes(notes: [{str: Any}]) -> [Note]:
        parsed_notes: [Note] = []
        for note in notes:
            n = Note(note["pitch"], note["velocity"], note["channel"], note["time"]["absolute"][0],
                     note["time"]["absolute"][1], note["time"]["relative"][0], note["time"]["relative"][1])
            parsed_notes.append(n)
        return parsed_notes


class Corpus:

    def __init__(self, filepath: str = None, timing_type: str = "relative"):
        """
        # TODO
        :param filepath:
        :param timing_type: "relative" or "absolute"
        """
        self.events: SequencedList[float, CorpusState] = SequencedList()
        self.content_type: AbstractContents = None

        if filepath:
            self.read_file(filepath, timing_type)

    def __repr__(self):
        return f"Corpus object with content type {self.content_type} and {len(self.events)} states"

    def read_file(self, filepath: str, timing_type: str):
        self.reset()
        with open(filepath, 'r') as jfile:
            corpus_data = json.load(jfile)

        type_id: str = corpus_data["typeID"]
        if type_id == "MIDI":
            self.content_type = Events.ClassicMIDIContents
        elif type_id == "Audio":
            self.content_type = Events.ClassicAudioContents
        else:
            raise InvalidJsonFormat("Json file must have a typeID set to either 'MIDI' or 'Audio'")

        events = corpus_data["data"]
        self.events = self._parse_events(events, timing_type)

    @staticmethod
    def _parse_events(events: [Dict], timing_type: str) -> [CorpusState]:
        parsed_events: SequencedList[float, CorpusState] = SequencedList()
        for event in events:
            c = CorpusState(event["state"], event["tempo"], event["time"]["absolute"][0], event["time"]["absolute"][1],
                            event["time"]["relative"][0], event["time"]["relative"][1], event["chroma"], event["pitch"],
                            event["notes"])
            parsed_events.append(event["time"][timing_type], c)
        return parsed_events

    def reset(self):
        self.events = SequencedList()
        self.content_type = None

