import json
import logging
from typing import Dict, TypeVar

from somaxlibrary import Contents
from somaxlibrary.Contents import AbstractContents
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Exceptions import InvalidJsonFormat
from somaxlibrary.ProperLabels import ProperAbstractLabel
from somaxlibrary.Tools import SequencedList


class Corpus:

    def __init__(self, filepath: str = None, timing_type: str = "relative"):
        """
        # TODO
        :param filepath:
        :param timing_type: "relative" or "absolute"
        """
        self.logger = logging.getLogger(__name__)
        self.ordered_events: SequencedList[float, CorpusEvent] = SequencedList()
        self.content_type: AbstractContents = None

        if filepath:
            self.read_file(filepath, timing_type)

    def __repr__(self):
        return f"Corpus object with content type {self.content_type} and {len(self.ordered_events)} states"

    def read_file(self, filepath: str, timing_type: str):
        self.reset()
        with open(filepath, 'r') as jfile:
            corpus_data = json.load(jfile)

        type_id: str = corpus_data["typeID"]
        if type_id == "MIDI":
            self.content_type = Contents.ClassicMIDIContents
        elif type_id == "Audio":
            self.content_type = Contents.ClassicAudioContents
        else:
            raise InvalidJsonFormat("Json file must have a typeID set to either 'MIDI' or 'Audio'")

        events = corpus_data["data"]
        self.ordered_events = self._parse_events(events, timing_type)
        self._classify_events()

    @staticmethod
    def _parse_events(events: [Dict], timing_type: str) -> [CorpusEvent]:
        parsed_events: SequencedList[float, CorpusEvent] = SequencedList()
        for event in events:
            c = CorpusEvent(event["state"], event["tempo"], event["time"][timing_type][0],
                            event["time"][timing_type][1], event["chroma"], event["pitch"], event["notes"], timing_type)
            parsed_events.append(event["time"][timing_type], c)
        return parsed_events

    def _classify_events(self):
        valid_label_classes: [(str, TypeVar)] = ProperAbstractLabel.label_classes()
        for _time, event in self.ordered_events:
            event.classify(valid_label_classes)

    def reset(self):
        self.ordered_events = SequencedList()
        self.content_type = None

    @property
    def events(self):
        return self.ordered_events.orderedEventList
