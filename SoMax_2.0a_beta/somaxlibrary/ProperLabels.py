from abc import ABC, abstractmethod
from typing import Any, Union, List

import numpy as np


class ProperAbstractLabel(ABC):

    @staticmethod
    @abstractmethod
    def classify(data: Any, **kwargs) -> int:
        pass


class ProperMelodicLabel(ProperAbstractLabel):

    @staticmethod
    def classify(data: int, mod12: bool = False) -> int:
        if mod12:
            return data % 12
        else:
            return data


class ProperHarmonicLabel(ProperAbstractLabel):
    # Static variables
    SOM_DATA = np.loadtxt('tables/misc_hsom', dtype=float, delimiter=",")  # TODO: Optimize
    SOM_CLASSES = np.loadtxt('tables/misc_hsom_c', dtype=int, delimiter=",")  # TODO: Optimize

    NODE_SPECIFICITY = 2.0

    @staticmethod
    def classify(data: Union[List[float], int], **kwargs) -> int:
        if isinstance(data, list) or isinstance(data, np.ndarray):
            return ProperHarmonicLabel._label_from_chroma(np.array(data))

    @staticmethod
    def _label_from_chroma(chroma: np.array) -> int:
        # TODO: Optimize and fix idiot behaviour with indtmp weirdsort
        chroma = np.array(chroma, dtype='float32')
        max_value = np.max(chroma)
        if max_value > 0:
            chroma /= max_value
        clust_vec = np.exp(-ProperHarmonicLabel.NODE_SPECIFICITY * np.sqrt(
            np.sum(np.power(chroma - ProperHarmonicLabel.SOM_DATA, 2), axis=1)))
        indtmp = np.argsort(clust_vec)
        # pick corresponding SOM class from chroma information
        label = ProperHarmonicLabel.SOM_CLASSES[indtmp[-1]]
        return label

    @staticmethod
    def _label_from_pitch(pitch: int) -> int:
        pitch_class: int = pitch % 12
        chroma = np.zeros(12, dtype='float32')
        chroma[pitch_class] = 1.0
        return ProperHarmonicLabel._label_from_chroma(chroma)
