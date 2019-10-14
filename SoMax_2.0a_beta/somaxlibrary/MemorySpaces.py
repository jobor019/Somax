import json
import logging
import os
from abc import ABC, abstractmethod
from collections import deque
from copy import deepcopy
from typing import TypeVar, Union, Any

from somaxlibrary import Events, Transforms, Labels, Contents
from somaxlibrary.Contents import AbstractContents
from somaxlibrary.Corpus import Corpus
from somaxlibrary.Events import AbstractEvent
from somaxlibrary.Labels import AbstractLabel
from somaxlibrary.Tools import SequencedList


# overloading Memory object, asserting a sequence of Event objects and embedding
#    a given representation, with its influence function used by Atom objects


class AbstractMemorySpace(ABC):
    def __init__(self, corpus: Corpus, label_type: Union[TypeVar, str] = AbstractLabel, *args, **kwargs):
        """ Note: args, kwargs can be used if additional information is need to construct the data structure."""
        self.logger = logging.getLogger(__name__)
        self.corpus: Corpus = corpus
        self.data: Any = None   # Abstract, defined per class

        if isinstance(label_type, str):
            self.label_type: TypeVar = getattr(Labels, label_type)
        else:
            self.label_type: TypeVar = label_type

        self._build(*args, **kwargs)
        self.available = True

    @abstractmethod
    def _build(self, *args, **kwargs) -> None:
        """Constructs self.data from loaded Corpus. By default, no parameters should be required"""

    # TODO: Make abstract. Or... Make generic so that it's not necessary to implement in subclasses.
    def influence(self, event):
        # print "here, the memory influences its internal state and returns activity peaks"
        return [], []  # returns dates and activities

    def _match(self, event: AbstractLabel) -> ????:

    def

    def is_available(self):
        return bool(self.available)

    # TODO: Remove or private/internal/part of init
    # build event from external data
    def build_event(self, *args, **kwargs):
        label = self.label_type.get_label_from_data(*args, **kwargs)
        contents = self.contents_type.get_contents_from_data(*args, **kwargs)
        event = self.event_type(label, contents)
        event.index = len(self)
        return event

    # TODO: Make abstract
    def reset(self):
        pass


class NGramMemorySpace(AbstractMemorySpace):
    def __init__(self, dates=[], states=[], \
                 label_type=AbstractLabel, content_type=AbstractContents,
                 event_type=AbstractEvent):
        AbstractMemorySpace.__init__(self, [], [], label_type, content_type, event_type)
        self.logger.debug("[__init__] Initializing new NGramMemorySpace with dates {},  states {}, label_t {},"
                          "content_t {} and event_t {}".format(dates, states, label_type, content_type, event_type))
        self.ngram_size = 3
        self.subsequences = dict()
        self.buffer = deque([], self.ngram_size)
        self.current_file = None
        self.typeID = None
        self.transforms = [Transforms.NoTransform, Transforms.TransposeTransform]
        for i in range(0, min(len(dates), len(states))):
            self.append(dates[i], states[i])

    def __repr__(self):
        return "N-Gram based memory"

    def __desc__(self):
        return str(self.ngram_size) + "-NGram based memory space"

    # 26/09 : redefinir append et definir insert
    def append(self, date, *args):
        # TODO: This should be optimized with numpy solution
        AbstractMemorySpace.append(self, date, *args)
        if len(self.orderedEventList) < self.ngram_size:
            return
        # adding n-plets to subsequences dict
        seq = self.orderedEventList[-(self.ngram_size):len(self.orderedEventList)]
        seq = tuple(map(lambda state: state.get_label(), seq))
        dic = dict(self.subsequences)
        if len(dic) == 0:
            self.subsequences[seq] = [len(self.orderedEventList) - 1]
        else:
            if seq in self.subsequences.keys():
                self.subsequences[seq].append(len(self.orderedEventList) - 1)
            else:
                self.subsequences[seq] = [len(self.orderedEventList) - 1]

    def build_subsequences(self):
        if len(self) < self.ngram_size:
            return
        self.subsequences = dict()
        bufr = deque([], self.ngram_size)
        for z, v in self:
            bufr.append(v.get_label())
            if len(bufr) >= self.ngram_size:
                seq = tuple(bufr)
                try:
                    self.subsequences[seq].append(z)
                except:
                    self.subsequences[seq] = [z]
                    pass
        self.buffer = deque([], self.ngram_size)

    def influence(self, data, **kwargs):
        event = self.build_event(*data, **kwargs)
        self.buffer.append(event.get_label())
        transforms = []
        peaks = []
        valid_transforms = self.transforms  # getting appropriate transformations
        for Transform in valid_transforms:
            transforms.extend(Transform.get_transformation_patterns())
        if len(self.buffer) >= self.ngram_size:
            for transform in transforms:
                k = tuple(map(lambda x: transform.encode(x), self.buffer))
                values = []
                c = None
                # TODO: Optimize. Takes ~20ms with a large corpus (x2 with self_influence) and 8 transforms.
                #       Size of this loop is of order O(1000) with a complicated __eq__ comparison (MelodicLabel.__eq__)
                #       Nevermind. Avg. call time per compare is just 1e-6, but in total 20k compares per influence.
                #       Numeric comparsion with matrices will generally cost <1 ms.
                #       f.ex. b = (a == (1, 2, 3)).all(axis=1).nonzero(), but this will require a radically different
                #       structure the entire NGram.
                #
                # TODO: An alternative solution would be to parallelize the operations (as entries are indep.),
                #       see https://stackoverflow.com/a/28463266
                if k in self.subsequences.keys():
                    for state in self.subsequences[k]:
                        peaks.append(tuple([self.orderedDateList[int(state)], 1.0, deepcopy(transform)]))
                # for t, z in self.subsequences.items():
                #     if k == t:
                #         c = t
                #         break
                # TODO: (Until here).
                # if c != None:
                #     for state in self.subsequences[c]:
                #         peaks.append(tuple([self.orderedDateList[int(state)], 1.0, deepcopy(transform)]))
        return peaks

    def read(self, filez, timing='relative'):
        if not os.path.isfile(filez):
            self.logger.error(f"Invalid file {filez}")
            return False
        with open(filez, 'r') as jfile:
            self.reset()
            data = json.load(jfile)
        self.available = False
        self.typeID = data['typeID']
        if self.typeID == "MIDI":
            self.contents_type = Events.ClassicMIDIContents
        elif self.typeID == "Audio":
            self.contents_type = Events.ClassicAudioContents
        self.reset()
        for i in range(1, len(data['data'])):
            self.append(data['data'][i]['time'][timing][0], data['data'][i])
        self.available = True
        self.current_file = filez
        return True

    def change_ngram(self, ngram_size):
        try:
            self.ngram_size = int(ngram_size)
        except:
            print("[ERROR memorySpace] ngram size must be an integer")
        self.ngram_size = ngram_size
        self.build_subsequences()
        print("[INFO] ngram size of", self, "set to", ngram_size)

    def reset(self):
        self.buffer = deque([], self.ngram_size)
        self.subsequences = dict()
        self.orderedDateList = list()
        self.orderedEventList = list()
