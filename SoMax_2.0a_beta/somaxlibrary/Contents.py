from copy import deepcopy

from somaxlibrary.Events import AbstractEvent
from somaxlibrary.Transforms import TransposeTransform, NoTransform


###############################################################################
# AbstractContents is the abstract pattern for a SoMax Label.
#   it defines mandatory functions that the contents subclasses must handle

class AbstractContents(object):
    def __init__(self, contents={}):
        self.set_contents(contents)
        self.type = "abstract"

    @classmethod
    def __desc__(self):
        return "Abstract contents"

    def set_contents(self, contents):
        self.contents = contents;

    def get_contents(self):
        '''returns state length'''
        return self.contents, 120.0

    def get_available_transforms(self):
        '''returns available transforms'''
        return [NoTransform]

    def get_state_length(self, timing_type="relative", factor=None):
        '''returns state length'''
        return 0.0

    def get_tempo(self):
        return 60.0

    @classmethod
    def get_contents_from_data(cls, contents):
        return cls(contents)


class ClassicMIDIContents(AbstractContents):
    def __init__(self, contents={}):
        AbstractContents.__init__(self, contents)
        self.type = "midi"

    def __repr__(self):
        return str(self.contents["notes"])

    @classmethod
    def __desc__(self):
        return "MIDI Contents"

    def set_contents(self, contents):
        if type(contents) == dict:
            if not "notes" in contents:
                raise Exception("Failed to build MIDI Contents from ", contents)
            self.contents = contents

    def get_contents(self, timing="relative", factor=None):
        content = []
        for i in self.contents["notes"]:
            if factor == None:
                length = i["time"][timing][1]
            else:
                if timing == "relative":
                    length = i["time"][timing][1] * self.contents["tempo"] / factor
                else:
                    length = i["time"][timing][1] / factor
            note = {'time': [i["time"][timing][0], length, self.contents["tempo"]],
                    'content': ["midi", i["pitch"], i["velocity"], length]}
            content.append(note)
        return content

    def get_state_length(self, timing="relative", factor=None):
        length = None
        if factor == None:
            length = self.contents["time"][timing][1]
        else:
            if timing == "relative":
                length = self.contents["time"][timing][1] * self.contents["tempo"] / factor
            else:
                length = self.contents["time"][timing][1] / factor
        return length

    def get_zeta(self, timing="relative"):
        return self.contents["time"][timing][0]

    def get_available_transforms(self):
        return [NoTransform, TransposeTransform]

    def get_tempo(self):
        return self.contents["tempo"]

    @classmethod
    def get_contents_from_data(cls, data, *args, **kwargs):
        contents = None
        if issubclass(type(data), AbstractEvent):
            contents = cls.get_contents_from_data(data.get_contents())
        elif issubclass(type(data), AbstractContents):
            if issubclass(type(data), ClassicMIDIContents):
                contents = deepcopy(data)
        elif type(data) == dict:
            contents = cls(data)
        elif type(data) == str:
            s = data.split(" ")
            style = s[0]
            if style == "pitch":
                contents = cls({"notes": [{"pitch": float(s[1]), "velocity": int(80)}]})
            elif style == "midi":
                contents = cls({"notes": [{"pitch": float(s[1]), "velocity": int(float(s[2]))}]})
        return contents


class ClassicAudioContents(AbstractContents):
    def __init__(self, contents={}):
        AbstractContents.__init__(self, contents)
        self.type = "audio"
        self.transpose = 0.0  # transposition in cents

    def get_contents(self, timing="relative", factor=None):
        length = None
        if factor == None:
            length = self.contents["time"]["absolute"][1]
        else:
            if timing == "relative":
                length = self.contents["time"]["absolute"][1] * self.contents["tempo"] / factor
                stretch = self.contents["tempo"] / factor
            else:
                length = self.contents["time"][timing][1] / factor
                stretch = factor
        content = {'time': [0., length, self.contents["tempo"]],
                   'content': ["audio", self.contents["time"]["absolute"][0], length, stretch, self.transpose]}
        return [content]

    def get_state_length(self, timing="relative", factor=None):
        length = None
        if factor == None:
            length = self.contents["time"][timing][1]
        else:
            if timing == "relative":
                length = self.contents["time"][timing][1] * self.contents["tempo"] / factor
            else:
                length = self.contents["time"][timing][1] / factor
        return length

    def get_zeta(self, timing="relative"):
        return self.contents["time"][timing][0]

    def get_available_transforms(self):
        return [NoTransform, TransposeTransform]

    @classmethod
    def get_contents_from_data(cls, data, *args, **kwargs):
        contents = None
        if issubclass(type(data), AbstractEvent):
            contents = cls.get_contents_from_data(data.get_contents())
        elif issubclass(type(data), AbstractContents):
            if issubclass(type(data), ClassicAudioContents):
                contents = deepcopy(data)
        elif type(data) == dict:
            contents = cls(data)
        elif type(data) == str:
            s = data.split(" ")
            style, beg, end = s[0], s[1], s[2]
            if style == "audio":
                contents = cls({"time": [beg, end - beg], "content": ["audio", 1.0, 0.0]})
        return contents
