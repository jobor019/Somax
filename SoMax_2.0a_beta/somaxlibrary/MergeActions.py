import inspect
import logging
import math
import sys
from abc import abstractmethod
from typing import ClassVar, Dict, Union

import numpy as np

from somaxlibrary.ActivityPattern import AbstractActivityPattern
from somaxlibrary.Corpus import Corpus
from somaxlibrary.ImprovisationMemory import ImprovisationMemory
from somaxlibrary.Parameter import Parametric, Parameter



class AbstractMergeAction(Parametric):
    TIME_IDX: int = AbstractActivityPattern.TIME_IDX
    SCORE_IDX: int = AbstractActivityPattern.SCORE_IDX
    TRANSFORM_IDX: int = AbstractActivityPattern.TRANSFORM_IDX

    def __init__(self):
        super().__init__()
        self.enabled: Parameter = Parameter(True, False, True, "bool", "Enables this MergeAction.")

    @abstractmethod
    def merge(self, peaks: np.ndarray, time: float, history: ImprovisationMemory = None, corpus: Corpus = None,
              **kwargs) -> np.ndarray:
        raise NotImplementedError("AbstractMergeAction.peaks is abstract.")

    @staticmethod
    def classes() -> {str: ClassVar}:
        return dict(inspect.getmembers(sys.modules[__name__],
                                       lambda member: inspect.isclass(member) and not inspect.isabstract(
                                           member) and member.__module__ == __name__))

    def update_parameter_dict(self) -> Dict[str, Union[Parametric, Parameter, Dict]]:
        parameters: Dict = {}
        for name, parameter in self._parse_parameters().items():
            parameters[name] = parameter.update_parameter_dict()
        self.parameter_dict = {"parameters": parameters}
        return self.parameter_dict

    def is_enabled(self):
        return self.enabled.value


class DistanceMergeAction(AbstractMergeAction):

    # TODO: Clean up constructor
    def __init__(self, t_width: float = 0.1, transform_merge_mode='OR'):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("[__init__] Creating DistanceMergeAction with width {} and merge mode {}."
                          .format(t_width, transform_merge_mode))
        self._t_width: Parameter = Parameter(t_width, 0.0, None, 'float', "Very unclear parameter")  # TODO
        self.transform_merge_mode = transform_merge_mode  # can 'AND' or 'OR'   # TODO Merge modes. Make parametric
        self._parse_parameters()

    def __repr__(self):
        return f"DistanceMergeAction(t_width={self.t_width}, merge_mode={self.transform_merge_mode})"

    def merge(self, peaks: np.ndarray, _time: float, _history: ImprovisationMemory = None, _corpus: Corpus = None,
              **_kwargs) -> np.ndarray:
        self.logger.debug(f"[merge] Merging activity with {len(peaks)} peaks.")
        # Sort by primary axis transforms, secondary axis time
        peaks = np.lexsort(
            (peaks[:, AbstractActivityPattern.TIME_IDX], peaks[:, AbstractActivityPattern.TRANSFORM_IDX]))
        self.logger.debug(f"[merge] Sorting completed.")
        if len(peaks) <= 1:
            return peaks
        idx_to_delete: [int] = []
        i = 1
        while i < peaks.shape[0]:
            prev: np.ndarray = peaks[i - 1, :]
            cur: np.ndarray = peaks[i, :]
            # TODO: magic nr
            if abs(cur[self.TIME_IDX] - prev[self.TIME_IDX]) < 0.9 * self.t_width and cur[self.TRANSFORM_IDX] == prev[
                self.TRANSFORM_IDX]:
                # self.logger.debug(f"Merging peak '{prev}' with peak '{cur}'.")
                merged_time: float = (prev[self.TIME_IDX] * prev[self.SCORE_IDX] + cur[self.TIME_IDX] * cur[
                    self.SCORE_IDX]) / (prev[self.SCORE_IDX] + cur[self.SCORE_IDX])
                merged_score: float = prev[self.SCORE_IDX]+ cur[self.SCORE_IDX]
                peaks[i - 1, :] = [merged_time, merged_score, cur[self.TRANSFORM_IDX]]
                idx_to_delete.append(i)
            # TODO: Handle different merge modes
            else:
                i += 1
        self.logger.debug(f"[merge] Merge successful. Number of peaks after merge: {len(peaks)}.")
        peaks = np.delete(peaks, i, axis=0)
        return peaks

    @property
    def t_width(self):
        return self._t_width.value

    @t_width.setter
    def t_width(self, value):
        self._t_width.value = value


class PhaseModulationMergeAction(AbstractMergeAction):
    DEFAULT_SELECTIVITY = 1.0

    def __init__(self, selectivity=DEFAULT_SELECTIVITY):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("[__init__] Creating PhaseMergeAction with selectivity {}".format(selectivity))
        self._selectivity: Parameter = Parameter(selectivity, None, None, 'float', "Very unclear parameter.")  # TODO
        self._parse_parameters()

    def merge(self, peaks: np.ndarray, time: float, _history: ImprovisationMemory = None, _corpus: Corpus = None,
              **_kwargs) -> np.ndarray:
        peaks[:, self.SCORE_IDX] *= np.exp(self.selectivity * (np.cos(2 * np.pi * (time - peaks[:, self.TIME_IDX])) - 1))
        return peaks

    @property
    def selectivity(self):
        return self._selectivity.value

    @selectivity.setter
    def selectivity(self, value):
        self._selectivity.value = value


class NextStateMergeAction(AbstractMergeAction):

    def __init__(self, factor: float = 1.5, t_width: float = 0.5):
        """ t_width in bars """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("[__init__] Creating NextStateMergeAction with width {} and merge mode {}.")
        self.factor: Parameter = Parameter(factor, 0.0, None, 'float',
                                           "Scaling factor for peaks close to previous output.")
        self._t_width: Parameter = Parameter(t_width, 0.0, None, 'float', "Very unclear parameter")  # TODO

    def merge(self, peaks: np.ndarray, time: float, history: ImprovisationMemory = None, corpus: Corpus = None,
              **kwargs) -> np.ndarray:
        try:
            last_event, trigger_time, _ = history.get_latest()
            next_state_time: float = last_event.onset + time - trigger_time
            next_state_idx: np.ndarray = np.abs(peaks[:, self.TIME_IDX] - next_state_time) < self._t_width.value
            peaks[next_state_idx, self.SCORE_IDX] *= self.factor.value
            return peaks
        except IndexError:  # Thrown if history is empty
            return peaks

# TODO: Reimplement!!!
# class StateMergeAction(AbstractMergeAction):
#     def __init__(self, memory_space, t_width=0.1, transform_merge_mode='AND'):
#         self.logger = logging.getLogger(__name__)
#         self.logger.debug("[__init__] Creating StateMergeAction with memory space {}, width {} and merge mode {}"
#                           .format(memory_space, t_width, transform_merge_mode))
#         self.t_width = 0.1
#         self.memory_space = memory_space
#         self.transform_merge_mode = transform_merge_mode  # can 'AND' or 'OR'
#
#     def merge(self, pattern, memory_space=None, scheduler=None):
#         # print ''
#         # print '------BEGINNING MERGE-------'
#         self.logger.debug("[merge] Merging activity with pattern {}.".format(pattern))
#         if len(pattern) == 0 or memory_space == None:
#             return deepcopy(pattern)
#         merged_pattern = SequencedList()
#         states_list = []
#         current_index = -1
#         for i in range(len(pattern)):
#             # print 'looop ',i
#             # print 'current_index : ', current_index
#             z, (v, t) = pattern[i]
#             # print 'pattern at ', i, ' : ', z, v, t
#             state, distance = self.memory_space.get_events(z)
#             state, distance = state[0], distance[0]
#             # print 'current state and distance : ', state, distance
#             if current_index == -1:
#                 # print 'init loop'
#                 za, (va, ta) = pattern[i]
#                 merged_pattern.append(float(za), (float(va), deepcopy(ta)))
#                 states_list.append(state.index)
#                 current_index += 1
#                 # print 'merged pattern : ', merged_pattern
#                 continue
#
#             if state == None:
#                 # print 'no state....'
#                 continue
#
#             if state.index == states_list[current_index]:
#                 # print 'conflicting states found'
#                 if t == merged_pattern[current_index][1][1]:
#                     # print "same transformations found"
#                     za, (va, ta) = merged_pattern[current_index]
#                     # print 'previous merged_pattern state : '; za, ta, va
#                     za = (za * va + z * v) / (v + va)
#                     va = v + va
#                     # print 'updating to ', za, ' and value ', va, 'and trasform ', ta
#                     merged_pattern[current_index] = za, (va, ta)
#                     # print 'new merged patter at', current_index, ' : ', merged_pattern[current_index]
#                 else:
#                     # print "different transformations"
#                     za, (va, ta) = merged_pattern[current_index]
#                     # print 'current merged pattern at ',current_index, ' : ', merged_pattern[current_index]
#                     za = (za * va + z * v) / (v + va)
#                     va = v + va
#                     # print 'before conversion', ta
#                     if type(ta) != list:
#                         ta = [ta]
#                     # print 'after conversion', ta
#                     cop = deepcopy(pattern[i][1][1])
#                     # print 'original pattern : ', pattern[i][1][1]
#                     # print 'copy of original pattern : ', pattern[i][1][1]
#                     ta = ta + [cop]
#                     # print 'after mutation : ', ta
#                     # print 'updating to ', za, ' with transofrom ', va, ' and ta ', ta
#
#                     merged_pattern[current_index] = za, (va, ta)
#                     # print 'current merged pattern at ',current_index, ' : ', merged_pattern[current_index]
#             else:
#                 # print 'different states'
#                 za, (va, ta) = pattern[i]
#                 merged_pattern.append(float(za), (float(va), deepcopy(ta)))
#                 states_list.append(state.index)
#                 # print 'appending ', state.index, ' to state list'
#                 current_index += 1
#                 # print 'current merged pattern at ',current_index, ' : ', merged_pattern[current_index]
#         return merged_pattern
