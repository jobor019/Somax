import inspect
import sys
from abc import ABC, abstractmethod
from typing import Any, Union, List, ClassVar

import numpy as np

from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Exceptions import InvalidLabelInput


class AbstractLabel(ABC):

    @staticmethod
    @abstractmethod
    def classify(data: Union[CorpusEvent, Any], **kwargs) -> int:
        """ # TODO
        Raises
        ------
        InvalidLabelInput

        Notes
        -----
        Must always handle CorpusState as this will always be passed upon construction of Corpus.
        """
        pass

    @staticmethod
    def classes() -> {(str, ClassVar)}:
        """Returns class objects for all non-abstract classes in this module."""
        return dict(inspect.getmembers(sys.modules[__name__],
                                       lambda member: inspect.isclass(member) and not inspect.isabstract(
                                           member) and member.__module__ == __name__))


class MelodicLabel(AbstractLabel):
    MAX_LABEL = 140

    @staticmethod
    def classify(data: Union[int, CorpusEvent], mod12: bool = False) -> int:
        if isinstance(data, CorpusEvent):
            return MelodicLabel._label_from_event(data)
        elif isinstance(data, int):
            return MelodicLabel._label_from_pitch(data)
        else:
            raise InvalidLabelInput("Melodic Label data could not be classified due to invalid type input.")

    @staticmethod
    def _label_from_event(event: CorpusEvent, mod12: bool = False) -> int:
        return MelodicLabel._label_from_pitch(event.pitch, mod12)

    @staticmethod
    def _label_from_pitch(pitch: int, mod12: bool = False) -> int:
        if pitch < 0 or pitch > MelodicLabel.MAX_LABEL:
            raise InvalidLabelInput("Melodic Label data could not be classified due to invalid range.")
        if mod12:
            return pitch % 12
        else:
            return pitch


class HarmonicLabel(AbstractLabel):
    # Static variables
    SOM_DATA = np.loadtxt('tables/misc_hsom', dtype=float, delimiter=",")  # TODO: Optimize import
    SOM_CLASSES = np.loadtxt('tables/misc_hsom_c', dtype=int, delimiter=",")  # TODO: Optimize import
    NODE_SPECIFICITY = 2.0

    @staticmethod
    def classify(data: Union[CorpusEvent, List[float], int], **kwargs) -> int:
        if isinstance(data, CorpusEvent):
            return HarmonicLabel._label_from_event(data)
        elif type(data) is list or isinstance(data, np.ndarray):
            return HarmonicLabel._label_from_chroma(np.array(data))
        elif isinstance(data, int):
            return HarmonicLabel._label_from_pitch(data)
        else:
            raise InvalidLabelInput(f"Harmonic Label data could not be classified due to incorrect type.")

    @staticmethod
    def _label_from_event(event: CorpusEvent) -> int:
        return HarmonicLabel._label_from_chroma(event.chroma)

    @staticmethod
    def _label_from_chroma(chroma: np.array) -> int:
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
        return label

    @staticmethod
    def _label_from_pitch(pitch: int) -> int:
        pitch_class: int = pitch % 12
        chroma = np.zeros(12, dtype='float32')
        chroma[pitch_class] = 1.0
        return HarmonicLabel._label_from_chroma(chroma)
