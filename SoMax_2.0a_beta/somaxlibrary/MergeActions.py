import inspect
import logging
import math
import sys
from abc import abstractmethod, ABC
from typing import ClassVar, Dict

from Parameter import Parameter
from Parametric import Parametric
from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.HasInfoDict import HasInfoDict
from somaxlibrary.Peak import Peak


class AbstractMergeAction(Parametric, HasInfoDict):

    @abstractmethod
    def merge(self, peaks: [Peak], time: float, history: [CorpusEvent] = None, corpus: Corpus = None, **kwargs) -> [
        Peak]:
        raise NotImplementedError("AbstractMergeAction.peaks is abstract.")

    @staticmethod
    def classes() -> {str: ClassVar}:
        return dict(inspect.getmembers(sys.modules[__name__],
                                       lambda member: inspect.isclass(member) and not inspect.isabstract(
                                           member) and member.__module__ == __name__))

    def info_dict(self) -> Dict:
        parameters: Dict = {}
        for name, parameter in self.parameters.items():
            parameters[name] = parameter.info_dict()
        return {"parameters": parameters}


class DistanceMergeAction(AbstractMergeAction):

    # TODO: Clean up constructor
    def __init__(self, t_width: float = 0.1, transform_merge_mode='OR'):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("[__init__] Creating DistanceMergeAction with width {} and merge mode {}."
                          .format(t_width, transform_merge_mode))
        self._t_width: Parameter = Parameter(t_width, 0.0, None, 'float', "Very unclear parameter")  # TODO
        self.transform_merge_mode = transform_merge_mode  # can 'AND' or 'OR'   # TODO Merge modes. Make parametric
        self._parse_parameters()

    def __repr__(self):
        return f"DistanceMergeAction(t_width={self.t_width}, merge_mode={self.transform_merge_mode})"

    def merge(self, peaks: [Peak], _time: float, _history: [CorpusEvent] = None, _corpus: Corpus = None, **_kwargs) -> [
        Peak]:
        self.logger.debug(f"[merge] Merging activity with {len(peaks)} peaks.")
        peaks.sort(key=lambda p: (p.transform_hash, p.time))
        if len(peaks) <= 1:
            return peaks
        i = 1
        while i < len(peaks):
            prev = peaks[i - 1]
            cur = peaks[i]
            if abs(
                    cur.time - prev.time) < 0.9 * self.t_width and cur.transform_hash == prev.transform_hash:  # TODO: magic nr
                self.logger.debug(f"Merging peak '{prev}' with peak '{cur}'.")
                merged_time: float = (prev.time * prev.score + cur.time * cur.score) / (prev.score + cur.score)
                merged_score: float = prev.score + cur.score
                peaks[i - 1] = Peak(merged_time, merged_score, cur.transforms, cur.last_update_time)
                del peaks[i]
            # TODO: Handle different merge modes
            else:
                i += 1
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
        self.logger = logging.getLogger(__name__)
        self.logger.debug("[__init__] Creating PhaseMergeAction with selectivity {}".format(selectivity))
        self._selectivity: Parameter = Parameter(selectivity,None, None, 'float', "Very unclear parameter.")    # TODO
        self._parse_parameters()

    def merge(self, peaks: [Peak], time: float, _history: [CorpusEvent] = None, _corpus: Corpus = None, **_kwargs) -> [
        Peak]:
        for peak in peaks:
            factor = math.exp(self.selectivity * (math.cos(2 * math.pi * (time - peak.time)) - 1))
            peak.score *= factor
        return peaks

    @property
    def selectivity(self):
        return self._selectivity.value

    @selectivity.setter
    def selectivity(self, value):
        self._selectivity.value = value


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
