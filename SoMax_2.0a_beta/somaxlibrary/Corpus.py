import json
import logging
from enum import Enum
from typing import Dict, ClassVar

from somaxlibrary.CorpusEvent import NoteCorpusEvent, PulseCorpusEvent
from somaxlibrary.Exceptions import InvalidJsonFormat
from somaxlibrary.Labels import AbstractLabel
from somaxlibrary.Tools import SequencedList


class ContentType(Enum):
    MIDI = "MIDI"
    AUDIO = "Audio"


class Corpus:
    DEFAULT_TIMING = "relative"

    def __init__(self, filepath: str = None, timing_type: str = DEFAULT_TIMING):
        """
        # TODO
        :param filepath:
        :param timing_type: "relative" or "absolute"
        """
        self.logger = logging.getLogger(__name__)
        self.ordered_events: SequencedList[float, NoteCorpusEvent] = SequencedList()
        self.pulse_events: SequencedList[float, PulseCorpusEvent] = SequencedList()
        self.content_type: ContentType = None

        if filepath:
            self.read_file(filepath, timing_type)

    def __repr__(self):
        return f"Corpus(content_type={self.content_type}, len={len(self.ordered_events)})."

    def read_file(self, filepath: str, timing_type: str = DEFAULT_TIMING):
        """" Raises: OSError """
        self.reset()
        with open(filepath, 'r') as jfile:
            corpus_data: Dict = json.load(jfile)
        try:
            self.content_type: ContentType = ContentType(corpus_data["typeID"])
        except ValueError as e:
            # TODO: Raise. catch at top level
            self.logger.debug(e)
            self.logger.error(f"Could not read json file. typeID should be either 'MIDI' or 'Audio'.")
            return

        try:
            note_events = corpus_data["note_segmented"]["data"]
            self.ordered_events = self._parse_note_events(note_events, timing_type)
            self._classify_events()
            pulse_events = corpus_data["beat_segmented"]["data"]
            self.pulse_events = self._parse_pulse_events(pulse_events, timing_type)
            self.logger.debug(f"[read_file] Corpus {self} successfully read.")
        except KeyError:
            raise InvalidJsonFormat("The file uses an old formatting standard. Try rebuilding the corpus.")

    @staticmethod
    def _parse_note_events(events: [Dict], timing_type: str) -> [NoteCorpusEvent]:
        parsed_events: SequencedList[float, NoteCorpusEvent] = SequencedList()
        for event in events:
            c = NoteCorpusEvent(event["state"], event["tempo"], event["time"][timing_type][0],
                                event["time"][timing_type][1], event["chroma"], event["pitch"], event["notes"], timing_type)
            parsed_events.append(event["time"][timing_type][0], c)
        return parsed_events

    @staticmethod
    def _parse_pulse_events(events: [Dict], timing_type: str):
        parsed_events: SequencedList[float, PulseCorpusEvent] = SequencedList()
        for event in events:
            c = PulseCorpusEvent(event["state"], event["tempo"], event["time"][timing_type][0],
                                event["time"][timing_type][1], event["chroma"], event["pitch"])
            parsed_events.append(event["time"][timing_type][0], c)
        return parsed_events

    def _classify_events(self):
        valid_label_classes: {str, ClassVar[AbstractLabel]} = AbstractLabel.classes()
        for _time, event in self.ordered_events:
            event.classify(valid_label_classes)

    def reset(self):
        self.ordered_events = SequencedList()
        self.content_type = None

    def length(self) -> int:
        return len(self.ordered_events)

    def event_at(self, index: int):
        return self.ordered_events.orderedEventList[index]

    def event_closest(self, time: float):
        # TODO: Very unoptimized
        return self.ordered_events.get_events(time)[0][0]

    @property
    def events(self):
        return self.ordered_events.orderedEventList
