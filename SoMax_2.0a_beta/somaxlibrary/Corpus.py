import json
import logging
from enum import Enum
from typing import Dict, ClassVar

from somaxlibrary.CorpusEvent import CorpusEvent
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
        self.ordered_events: SequencedList[float, CorpusEvent] = SequencedList()
        self.content_type: ContentType = None

        if filepath:
            self.read_file(filepath, timing_type)

    def __repr__(self):
        return f"Corpus object with content type {self.content_type} and {len(self.ordered_events)} states"

    def read_file(self, filepath: str, timing_type: str = DEFAULT_TIMING):
        """" Raises: OSError """
        self.reset()
        with open(filepath, 'r') as jfile:
            corpus_data = json.load(jfile)
        try:
            self.content_type = ContentType(corpus_data["typeID"])
        except ValueError as e:
            self.logger.debug(e)
            self.logger.error(f"Could not read json file. typeID should be either 'MIDI' or 'Audio'.")

        events = corpus_data["data"]
        self.ordered_events = self._parse_events(events, timing_type)
        self._classify_events()

    @staticmethod
    def _parse_events(events: [Dict], timing_type: str) -> [CorpusEvent]:
        parsed_events: SequencedList[float, CorpusEvent] = SequencedList()
        for event in events:
            c = CorpusEvent(event["state"], event["tempo"], event["time"][timing_type][0],
                            event["time"][timing_type][1], event["chroma"], event["pitch"], event["notes"], timing_type)
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

    @property
    def events(self):
        return self.ordered_events.orderedEventList
