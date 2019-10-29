import inspect
import logging
import math
import sys
from abc import abstractmethod, ABC
from typing import ClassVar

from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Peak import Peak


class AbstractMergeAction(ABC):
    # TODO: Maybe pass Corpus at construction time instead of at each merge.
    # TODO: Maybe add transform merge modes and merge action merge modes

    @abstractmethod
    def merge(self, peaks: [Peak], time: float, history: [CorpusEvent] = None, corpus: Corpus = None, **kwargs) -> [
        Peak]:
        raise NotImplementedError("AbstractMergeAction.peaks is abstract.")

    @staticmethod
    def classes() -> {str: ClassVar}:
        return dict(inspect.getmembers(sys.modules[__name__],
                                       lambda member: inspect.isclass(member) and not inspect.isabstract(
                                           member) and member.__module__ == __name__))


class DistanceMergeAction(AbstractMergeAction):

    # TODO: Clean up constructor
    def __init__(self, t_width=0.1, transform_merge_mode='OR'):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("[__init__] Creating DistanceMergeAction with width {} and merge mode {}."
                          .format(t_width, transform_merge_mode))
        self.t_width = t_width
        self.transform_merge_mode = transform_merge_mode  # can 'AND' or 'OR'   # TODO Merge modes

    def __repr__(self):
        return f"DistanceMergeAction(t_width={self.t_width}, merge_mode={self.transform_merge_mode})"

    def merge(self, peaks: [Peak], _time: float, _history: [CorpusEvent] = None, _corpus: Corpus = None, **_kwargs) -> [
        Peak]:
        """(TODO: old temp docstring) Merges events that are similar and sufficiently close in time to each other into a
             single events. Returns all other events unchanged. Unless mode is set to AND, then it deletes both unless
             peaks occur in all layers simultaneously."""
        self.logger.debug("[merge] Merging activity with peaks '{}'.".format(peaks))
        peaks.sort(key=lambda p: (p.time, p.precomputed_transform_hash))
        if len(peaks) <= 1:
            return peaks
        prev = peaks[0]
        i = 1
        while i < len(peaks):
            cur = peaks[i]
            if abs(cur.time - prev.time) < 0.9 * self.t_width and cur.transforms == prev.transforms:  # TODO: magic nr
                merged_time: float = (prev.time * prev.score + cur.time * cur.score) / (prev.score + cur.score)
                merged_score: float = prev.score + cur.score
                peaks[i - 1] = Peak(merged_time, merged_score, cur.transforms, cur.last_update_time)
                del peaks[i]
            # TODO: Handle different merge modes
            else:
                i += 1
        return peaks


# TODO: Never used. Rewrite later!!!
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


class PhaseModulationMergeAction(AbstractMergeAction):
    DEFAULT_SELECTIVITY = 1.0

    def __init__(self, selectivity=DEFAULT_SELECTIVITY):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("[__init__] Creating PhaseMergeAction with selectivity {}".format(selectivity))
        self.selectivity = selectivity

    def merge(self, peaks: [Peak], time: float, _history: [CorpusEvent] = None, _corpus: Corpus = None, **_kwargs) -> [Peak]:
        for peak in peaks:
            factor = math.exp(self.selectivity * (math.cos(2 * math.pi * (time - peak.time)) - 1))
            peak.score *= factor
        return peaks

    # TODO: Parameter setting in general
    # def set_selectivity(self, selectivity):
    #     try:
    #         self.selectivity = float(selectivity)
    #     except:
    #         self.logger.error("Phase modulation selectivity must be a number.")
    #         pass
