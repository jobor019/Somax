import inspect
import sys
from abc import ABC, abstractmethod
from typing import Any, Union, List, ClassVar

import numpy as np

from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Exceptions import InvalidLabelInput


class AbstractLabel(ABC):

    def __init__(self, label: int):
        """
        Notes
        -----
        No label should ever be directly constructed using __init__. use `classify` and `classify_as`.
        """
        self.label: int = label

    def __repr__(self):
        return f"{self.__class__} with label {self.label}"

    @staticmethod
    @abstractmethod
    def _influence_keyword() -> str:
        """
        Notes
        -----
        This should return a for the label unique string that is used to categorize influence messages from max."""
        raise NotImplementedError("AbstractLabel._influence_keyword is abstract.")

    @classmethod
    @abstractmethod
    def classify(cls, data: Union[CorpusEvent, Any], **kwargs) -> 'AbstractLabel':
        """ # TODO
        Raises
        ------
        InvalidLabelInput

        Notes
        -----
        Must always handle CorpusState as this will always be passed upon construction of Corpus.
        """
        raise NotImplementedError("AbstractLabel.classify is abstract.")

    @classmethod
    def classify_as(cls, influence_keyword: str, data: Any, **kwargs) -> 'AbstractLabel':
        """ Raises: InvalidLabelInput """
        # TODO: [OPTIMIZATION]: ev. refactor this to own class to avoid calling `classes` continuously (if slow)
        classes: [ClassVar] = AbstractLabel.classes().values()
        for c in classes:  # type: ClassVar[AbstractLabel]
            if c._influence_keyword() == influence_keyword:
                return c.classify(data, **kwargs)
        raise InvalidLabelInput(f"No class exists that matches the influence keyword {influence_keyword}.")

    @staticmethod
    def classes() -> {str: ClassVar}:
        """Returns class objects for all non-abstract classes in this module."""
        return dict(inspect.getmembers(sys.modules[__name__],
                                       lambda member: inspect.isclass(member) and not inspect.isabstract(
                                           member) and member.__module__ == __name__))


class MelodicLabel(AbstractLabel):
    MAX_LABEL = 140

    @staticmethod
    def _influence_keyword() -> str:
        return "pitch"

    @classmethod
    def classify(cls, data: Union[int, CorpusEvent], mod12: bool = False) -> 'MelodicLabel':
        if isinstance(data, CorpusEvent):
            return MelodicLabel._label_from_event(data)
        elif isinstance(data, int):
            return MelodicLabel._label_from_pitch(data)
        else:
            raise InvalidLabelInput("Melodic Label data could not be classified due to invalid type input.")

    @classmethod
    def _label_from_event(cls, event: CorpusEvent, mod12: bool = False) -> 'MelodicLabel':
        return MelodicLabel._label_from_pitch(event.pitch, mod12)

    @classmethod
    def _label_from_pitch(cls, pitch: int, mod12: bool = False) -> 'MelodicLabel':
        if pitch < 0 or pitch > MelodicLabel.MAX_LABEL:
            raise InvalidLabelInput("Melodic Label data could not be classified due to invalid range.")
        if mod12:
            return cls(pitch % 12)
        else:
            return cls(pitch)


class HarmonicLabel(AbstractLabel):
    # Static variables
    SOM_DATA = np.loadtxt('tables/misc_hsom', dtype=float, delimiter=",")  # TODO: Optimize import
    SOM_CLASSES = np.loadtxt('tables/misc_hsom_c', dtype=int, delimiter=",")  # TODO: Optimize import
    NODE_SPECIFICITY = 2.0

    @staticmethod
    def _influence_keyword() -> str:
        return "chroma"

    @classmethod
    def classify(cls, data: Union[CorpusEvent, List[float], int], **kwargs) -> 'HarmonicLabel':
        if isinstance(data, CorpusEvent):
            return HarmonicLabel._label_from_event(data)
        elif type(data) is list or isinstance(data, np.ndarray):
            return HarmonicLabel._label_from_chroma(np.array(data))
        elif isinstance(data, int):
            return HarmonicLabel._label_from_pitch(data)
        else:
            raise InvalidLabelInput(f"Harmonic Label data could not be classified due to incorrect type.")

    @classmethod
    def _label_from_event(cls, event: CorpusEvent) -> 'HarmonicLabel':
        return HarmonicLabel._label_from_chroma(event.chroma)

    @classmethod
    def _label_from_chroma(cls, chroma: np.array) -> 'HarmonicLabel':
        # TODO: Optimize and fix idiot behaviour with indtmp weirdsort
        if len(chroma) != 12:
            raise InvalidLabelInput(f"Harmonic Label data could not be classified from content with size {len(chroma)}."
                                    f" Required size is 12.")
        chroma = np.array(chroma, dtype='float32')
        max_value = np.max(chroma)
        if max_value > 0:
            chroma /= max_value
        clust_vec = np.exp(-HarmonicLabel.NODE_SPECIFICITY
                           * np.sqrt(np.sum(np.power(chroma - HarmonicLabel.SOM_DATA, 2), axis=1)))
        indtmp = np.argsort(clust_vec)
        # pick corresponding SOM class from chroma information
        label = HarmonicLabel.SOM_CLASSES[indtmp[-1]]
        return cls(label)

    @classmethod
    def _label_from_pitch(cls, pitch: int) -> 'HarmonicLabel':
        pitch_class: int = pitch % 12
        chroma = np.zeros(12, dtype='float32')
        chroma[pitch_class] = 1.0
        return HarmonicLabel._label_from_chroma(chroma)
