from typing import Union, List

import numpy as np


class Peaks:

    def __init__(self, scores: np.ndarray, times: np.ndarray, transform_hashes: np.ndarray):
        """ scores, times and transform_hashes should have the same sizes. TODO: Assert if performance allows"""
        self.scores: np.ndarray = scores  # shape: 1d, dtype: float
        self.times: np.ndarray = times  # shape: 1d, dtype: float
        self.transform_hashes: np.ndarray = transform_hashes  # shape: 1d, dtype: int

    @classmethod
    def create_empty(cls):
        return cls(np.empty((0, 1), dtype=np.float), np.empty((0, 1), dtype=np.float), np.empty((0, 1), dtype=np.int32))

    @classmethod
    def concatenate(cls, peaks: ['Peaks']):
        scores: np.ndarray = np.concatenate([peak.scores for peak in peaks])
        times: np.ndarray = np.concatenate([peak.times for peak in peaks])
        transform_hashes: np.ndarray = np.concatenate([peak.transform_hashes for peak in peaks])
        return cls(scores, times, transform_hashes)

    def append(self, scores: [float], times: [float], transform_hashes: [int]):
        self.scores = np.concatenate((self.scores, scores))
        self.times = np.concatenate((self.times, times))
        self.transform_hashes = np.concatenate((self.transform_hashes, transform_hashes))

    def remove(self, indices: np.ndarray):
        """ mask: 1d boolean array with same size as scores/times/transforms """
        self.scores = np.delete(self.scores, indices)
        self.times = np.delete(self.times, indices)
        self.transform_hashes = np.delete(self.transform_hashes, indices)

    def size(self) -> int:
        return self.scores.size

    def reorder(self, indices: np.ndarray):
        self.scores = self.scores[indices]
        self.times = self.times[indices]
        self.transform_hashes = self.transform_hashes[indices]

    def empty(self) -> bool:
        return self.scores.size == 0

    def dump(self) -> (np.ndarray, np.ndarray, np.ndarray):
        return self.scores, self.times, self.transform_hashes


