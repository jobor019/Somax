import logging
from abc import ABC
from copy import deepcopy, copy

import numpy as np

from somaxlibrary import Transforms


###############################################################################
# AbstractLabel is the abstract pattern for a SoMax Label.
#   it defines mandatory functions that the label subclasses must handle

class AbstractLabel(ABC):
    def __init__(self, label=None):
        self.logger = logging.getLogger(__name__)
        self.available_transforms = self.get_available_transforms()
        if not label is None and label != []:
            self.set_label(label)

    def __repr__(self):
        return "Abstract Label with label " + str(self.label)

    def __hash__(self):
        return hash(self.label)

    @classmethod
    def __desc__(self):
        return "Abstract label"

    def set_label(self, label):
        self.label = deepcopy(label)

    def get_label(self):
        '''accessors for label'''
        return copy(self.label)

    # custom equality function for customized comparison
    def __eq__(self, a):
        if isinstance(a, AbstractLabel):
            return self.label == a.label
        else:
            try:
                return self.label == a
            except:
                raise TypeError("Failed comparing AbstractLabel with object ", type(a))

    def get_available_transforms(self):
        '''returns transforms compatible with current label class'''
        return [Transforms.NoTransform]

    @classmethod
    def get_label_from_data(cls, data, *args, **kwargs):
        '''class method constructing a label object from raw data'''
        label = data
        return AbstractLabel(label)


class MelodicLabel(AbstractLabel):
    '''Label object carrying pitch information. Can be set octave (in)dependant with mod12 attribute.'''

    def __init__(self, label=-1, mod12=False):
        AbstractLabel.__init__(self, label)
        self.mod12 = mod12  # is equality dependant of the octave

    def __repr__(self):
        return "Melodic Label with pitch " + str(self.label)

    def __hash__(self):
        return hash(self.label)

    @classmethod
    def __desc__(self):
        return "Melodic label"

    def set_label(self, label):
        try:
            self.label = int(label)
        except:
            raise TypeError("Failed creating Melodic Label from ", label)

    def __eq__(self, other):
        # TODO: Optimize or move modulo to json construction.
        if self.mod12:
            return isinstance(other, MelodicLabel) and self.label % 12 == other.label % 12
        else:
            return isinstance(other, MelodicLabel) and self.label == other.label
        # if a == None:
        #     return False
        # elif issubclass(type(a), MelodicLabel):
        #     if self.mod12:
        #         return self.label % 12 == a.label % 12
        #     else:
        #         return self.label == a.label
        # elif issubclass(type(a), AbstractLabel):
        #     try:
        #         a_i = int(a)
        #         if self.mod12:
        #             return self.label % 12 == a.label % 12
        #         else:
        #             return self.label == a.label
        #     except:
        #         raise TypeError("Failed comparing", self.label, " to abstract label ", a.__repr__())
        # elif isinstance(a, AbstractEvent):
        #     return self.__eq__(a.label)
        # elif type(a) == int:
        #     return self.label == a
        # else:
        #     raise TypeError("Failed comparing Melodic Label with ", a.__repr__())

    def get_available_transforms(self):
        return [Transforms.NoTransform, Transforms.TransposeTransform]

    @classmethod
    def get_label_from_data(cls, data, *args, **kwargs):
        # creates melodic label from data
        mod12 = kwargs['mod12'] if "mod12" in kwargs else False
        label = None
        if type(data) == str:
            data = data.split(" ")  # split string with subspaces in case of list
        if issubclass(type(data), AbstractEvent):
            label = cls.get_label_from_data(data.get_label(), mod12)
        elif issubclass(type(data), AbstractLabel):
            if issubclass(type(data), MelodicLabel):
                label = deepcopy(data)
            else:
                # try to make object from label's label
                label = cls.get_label_from_data(data.get_label(), mod12)
        elif type(data) == list or type(data) == tuple:
            influence_type = str(data[0])
            # midi == [[0, 127], vel, channel]
            if influence_type == 'midi':
                try:
                    note = int(float(data[1]))
                    label = cls(note)
                except:
                    raise Exception("midi pitch identifier must be an integer")
            # classic pitch, [[0, 140], vel, channel
            elif influence_type == 'pitch':
                note = int(data[1])
                if type(note) == int:
                    label = cls(note)
                else:
                    raise Exception("pitch identifier must be an integer")
            # TODO: elif influence_type=='chroma':
            else:
                print("streamview", cls, "doesn't understand type", influence_type)
        elif type(data) == int or type(data) == float:
            label = cls(int(data), mod12)
        elif type(data) == dict:
            label = cls(data["pitch"], mod12)
        if label is None:
            raise Exception("MelodicLabel can't make label from data ", data)
        label.mod12 = mod12
        return label


class HarmonicLabel(AbstractLabel):
    '''Label object carrying harmonic information.'''
    node_specificity = 2.0
    som = [];
    som_c = [];

    # an harmonic label contains both chroma and label information
    def __init__(self, label=None):
        # importing SOM parameters
        if HarmonicLabel.som == []:
            HarmonicLabel.som = np.loadtxt('tables/misc_hsom', dtype=float, delimiter=",")
        if HarmonicLabel.som_c == []:
            HarmonicLabel.som_c = np.loadtxt('tables/misc_hsom_c', dtype=int, delimiter=",")
        AbstractLabel.__init__(self, label)

    def __repr__(self):
        return "Harmonic Label with label " + str(self.label)

    def __hash__(self):
        return hash(self.label)

    @classmethod
    def __desc__(self):
        return "Harmonic label"

    def set_label(self, data):
        if type(data) == list or type(data) == type(np.array(0)):
            # initialized with chroma information
            self.chroma = np.array(data, dtype='float32')
            max_chroma = np.max(self.chroma)
            if max_chroma > 0:
                self.chroma /= max_chroma
            clust_vec = np.exp(
                -self.node_specificity * np.sqrt(np.sum(np.power(self.chroma - HarmonicLabel.som, 2), axis=1)))
            indtmp = np.argsort(clust_vec)
            # pick corresponding SOM class from chroma information
            self.label = HarmonicLabel.som_c[indtmp[-1]]
            self.logger.debug(f"[set_label] Harmonic label assigned to class {self.label} with "
                              f"corresponding index {indtmp[-1]}.")
        else:
            try:
                self.label = int(data)
                self.chroma = np.zeros(12)
            except:
                raise TypeError("Failed to make chromatic label from label ", self.label.__repr__())

    def get_label(self, ctype="chroma"):
        if ctype == 'id':
            return self.label
        elif ctype == 'chroma':
            return self.chroma

    def __eq__(self, a):
        # return isinstance(a, HarmonicLabel) and self.label == a.label
        if type(a) == type(None):
            return False
        elif type(a) == int or type(a) == float:
            return self.label == a
        elif issubclass(type(a), HarmonicLabel):
            return self.label == a.label
        elif issubclass(type(a), MelodicLabel):
            return np.amax(self.chroma) == a.label  # replace by virtual fundamental?
        elif type(a) == list or type(a) == tuple:
            clust_vec = np.exp(-self.node_specificity * np.sqrt(np.sum(np.power(a - HarmonicLabel.som, 2), axis=1)))
            indtmp = np.argsort(clust_vec)
            id_c = HarmonicLabel.som_c[indtmp[-1]]
            return self.label == id_c
        else:
            raise TypeError("Failed comparing Harmonic Label with ", a.__repr__())

    def get_available_transforms(self):
        return [Transforms.NoTransform, Transforms.TransposeTransform]

    @classmethod
    def get_label_from_data(cls, data, *args, **kwargs):
        label = None
        if type(data) == str:
            data = data.split(" ")
        if issubclass(type(data), AbstractEvent):
            label = cls.get_label_from_data(data.get_label())
        elif issubclass(type(data), AbstractLabel):
            if type(data) == MelodicLabel:
                pitch = data.label
                chroma = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                chroma[pitch % 12] = 1.0
                label = cls(chroma)
            elif type(data) == cls:
                label = cls()
                label.label = deepcopy(data.label)
                label.chroma = deepcopy(data.chroma)
            else:
                pitch = data.label
                try:
                    data = int(data)
                except:
                    raise Exception("Could not make Harmonic Label from Abstract Label with label ", data.label)
                chroma = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                chroma[pitch % 12] = 1.0
                label = cls(chroma)
        elif type(data) == list or type(data) == tuple:
            if len(data) == 1:
                cls.get_label_from_data(data[0], args)
            influence_type = str(data[0])
            if influence_type == 'chroma':
                if len(data) == 13:
                    try:
                        data = list(map(lambda x: float(x), data[1:]))
                    except TypeError:
                        print("problem with incoming chromas")
                    label = cls(data)
                else:
                    print("chroma events must contain 12 values!")
            elif influence_type == 'midi' or influence_type == 'pitch':
                note = data[1]
                print(note)
                if type(note) == type(int()):
                    chroma = list(np.zeros(12))
                    chroma[note % 12] = 1.
                    label = HarmonicLabel(chroma)
                else:
                    print("midi or pitch identifier must be an integer")
            else:
                print("event doesn't understand type", influence_type)
        elif type(data) == dict:
            label = cls(data["chroma"])
        if label is None:
            raise Exception("HarmonicLabel can't make label from data ", data)
        return label