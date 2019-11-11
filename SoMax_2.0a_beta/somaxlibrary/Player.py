import logging
from collections import deque
from copy import deepcopy
from functools import reduce
from typing import ClassVar, Dict

from somaxlibrary.ActivityPattern import AbstractActivityPattern
from somaxlibrary.Atom import Atom
from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Exceptions import DuplicateKeyError, TransformError
from somaxlibrary.Exceptions import InvalidPath, InvalidCorpus, InvalidConfiguration, InvalidLabelInput
from somaxlibrary.HasInfoDict import HasInfoDict
from somaxlibrary.Labels import AbstractLabel
from somaxlibrary.MemorySpaces import AbstractMemorySpace
from somaxlibrary.MergeActions import DistanceMergeAction, PhaseModulationMergeAction, AbstractMergeAction
from somaxlibrary.Peak import Peak
from somaxlibrary.PeakSelector import AbstractPeakSelector, MaxPeakSelector, DefaultPeakSelector
from somaxlibrary.StreamView import StreamView
from somaxlibrary.Target import Target
from somaxlibrary.Transforms import AbstractTransform
from somaxlibrary.scheduler.ScheduledObject import ScheduledMidiObject, TriggerMode


class Player(ScheduledMidiObject, HasInfoDict):
    MAX_HISTORY_LEN = 100

    def __init__(self, name: str, target: Target, triggering_mode: TriggerMode):
        super(Player, self).__init__(triggering_mode)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Created Player with name '{name}' and trigger mode '{triggering_mode}'")
        self.name: str = name  # name of the player
        self.target: Target = target

        self.streamviews: {str: StreamView} = dict()
        self.merge_actions: [AbstractMergeAction] = [DistanceMergeAction(), PhaseModulationMergeAction()]
        self.corpus: Corpus = None
        self.peak_selectors: [AbstractPeakSelector] = [MaxPeakSelector(), DefaultPeakSelector()]  # TODO impl. setters

        self.improvisation_memory: deque[(CorpusEvent, AbstractTransform)] = deque('', self.MAX_HISTORY_LEN)
        self._previous_peaks: [Peak] = []

        self._parse_parameters()

        # self.nextstate_mod: float = 1.5   # TODO
        # self.waiting_to_jump: bool = False    # TODO

        # self.info_dictionary = dict()  # TODO

    def info_dict(self) -> Dict:
        streamviews = {}
        merge_actions = {}
        peak_selectors = {}
        parameters: Dict = {}
        for name, streamview in self.streamviews.items():
            streamviews[name] = streamview.info_dict()
        for merge_action in self.merge_actions:
            key: str = type(merge_action).__name__
            merge_actions[key] = merge_action.info_dict()
        for peak_selector in self.peak_selectors:
            key: str = type(peak_selector).__name__
            peak_selectors[key] = peak_selector.info_dict()
        for name, parameter in self.parameters.items():
            parameters[name] = parameter.info_dict()
        return {self.name: {"streamviews": streamviews,
                            "merge_actions": merge_actions,
                            "peak_selectors": peak_selectors,
                            "parameters": parameters}}

    def _get_streamview(self, path: [str]) -> StreamView:
        streamview: str = path.pop(0)
        return self.streamviews[streamview].get_streamview(path)

    def _get_atom(self, path: [str]) -> Atom:
        streamview: str = path.pop(0)
        return self.streamviews[streamview].get_atom(path)

    def _self_atoms(self) -> [Atom]:
        atoms: [Atom] = []
        for streamview in self.streamviews.values():
            for atom in streamview.atoms.values():
                if atom.self_influenced:
                    atoms.append(atom)
        return atoms

    def _all_atoms(self) -> [Atom]:
        atoms: [Atom] = []
        for streamview in self.streamviews.values():
            for atom in streamview.atoms.values():
                atoms.append(atom)
        return atoms

    def _update_peaks(self, time: float) -> None:
        for streamview in self.streamviews.values():
            streamview.update_peaks(time)

    def new_event(self, scheduler_time: float, **kwargs) -> CorpusEvent:
        """ Raises: InvalidCorpus """
        self.logger.debug("[new_event] Player {} attempting to create a new event at scheduler time '{}'."
                          .format(self.name, scheduler_time))

        if not self.corpus:
            raise InvalidCorpus(f"No Corpus has been loaded in player '{self.name}'.")

        self._update_peaks(scheduler_time)
        peaks: [Peak] = self.merged_peaks(scheduler_time, self.improvisation_memory, self.corpus, **kwargs)

        event_and_transforms: (CorpusEvent, AbstractTransform) = None
        for peak_selector in self.peak_selectors:
            event_and_transforms = peak_selector.decide(peaks, self.improvisation_memory, self.corpus, **kwargs)
            if event_and_transforms:
                break
        if not event_and_transforms:
            # TODO: Ensure that this never happens so that this error message can be removed
            raise InvalidConfiguration("All PeakSelectors failed. SoMax requires at least one default peak selector.")

        self.improvisation_memory.append(event_and_transforms)
        self._previous_peaks: [Peak] = peaks

        event: CorpusEvent = deepcopy(event_and_transforms[0])
        transforms: (AbstractTransform, ...) = event_and_transforms[1]
        for transform in transforms:
            event = transform.transform(event)

        self._influence_self(event, scheduler_time)
        return event

    def _influence_self(self, event: CorpusEvent, time: float) -> None:
        atoms: [Atom] = self._self_atoms()
        labels: [AbstractLabel] = event.labels
        for atom in atoms:
            for label in labels:
                try:
                    atom.influence(label, time)
                except InvalidLabelInput:
                    continue

    def influence(self, path: [str], label: AbstractLabel, time: float, **kwargs) -> None:
        """ Raises: InvalidLabelInput, KeyError"""
        if not path:
            for atom in self._all_atoms():
                try:
                    atom.influence(label, time, **kwargs)
                except InvalidLabelInput as e:
                    self.logger.debug(f"[influence] {repr(e)} Likely expected behaviour, only in rare cases an issue.")
        else:
            self._get_atom(path).influence(label, time, **kwargs)

    def create_streamview(self, path: [str], weight: float, merge_actions: (ClassVar, ...)):
        """creates streamview at target path"""
        self.logger.debug("[create_streamview] Creating streamview {} in player {} with merge_actions {}..."
                          .format(path, self.name, merge_actions))
        streamview: str = path.pop(0)
        if not path:
            if streamview in self.streamviews.keys():
                raise DuplicateKeyError(f"A streamview '{streamview}' already exists in player '{self.name}'.")
            else:
                self.streamviews[streamview] = StreamView(name=streamview, weight=weight, merge_actions=merge_actions)
        else:
            self.streamviews[streamview].create_streamview(path, weight, merge_actions)

    def create_atom(self, path: [str], weight: float, label_type: ClassVar[AbstractLabel],
                    activity_type: ClassVar[AbstractActivityPattern], memory_type: ClassVar[AbstractMemorySpace],
                    self_influenced: bool, transforms: [(ClassVar[AbstractTransform], ...)]):
        """creates atom at target path
        raises: InvalidPath, KeyError, DuplicateKeyError"""
        self.logger.debug(f"[create_atom] Attempting to create atom at {path}...")

        streamview: str = path.pop(0)
        if not path:  # path is empty means no streamview path was given
            raise InvalidPath(f"Cannot create an atom directly in Player.")
        else:
            self.streamviews[streamview].create_atom(path, weight, label_type, activity_type, memory_type,
                                                     self.corpus, self_influenced, transforms)

    def read_corpus(self, filepath: str):
        self.corpus = Corpus(filepath)
        for streamview in self.streamviews.values():
            streamview.read(self.corpus)
        # TODO: info dict
        # self.update_memory_length()
        # self.send_info_dict()

    def merged_peaks(self, time: float, history: [CorpusEvent], corpus: Corpus, **kwargs) -> [Peak]:
        weight_sum: float = float(reduce(lambda a, b: a + b.weight, self.streamviews.values(), 0.0))
        peaks: [Peak] = []
        for streamview in self.streamviews.values():
            normalized_weight = streamview.weight / weight_sum
            for peak in streamview.merged_peaks(time, history, corpus, **kwargs):
                peak.score *= normalized_weight
                peaks.append(peak)

        for merge_action in self.merge_actions:
            peaks = merge_action.merge(peaks, time, history, corpus, **kwargs)
        return peaks

    def add_transform(self, path: [str], transform: (AbstractTransform, ...)) -> None:
        """ raises TransformError, KeyError"""
        if not path:
            for atom in self._all_atoms():
                try:
                    atom.memory_space.add_transforms(transform)
                except TransformError as e:
                    self.logger.error(f"{str(e)}")
        else:
            self._get_atom(path).memory_space.add_transforms(transform)

    @property
    def previous_peaks_raw(self) -> [(float, float, int)]:
        peaks: [(int, float, int)] = []
        transform_indices: {int: int} = {}
        transform_tuple_index: int = 0
        for peak in self._previous_peaks:
            if peak.transforms not in transform_indices:
                transform_indices[peak.transform_hash] = transform_tuple_index
                transform_tuple_index += 1
            state: int = self.corpus.event_closest(peak.time).state_index
            score: float = peak.score
            transform_index: int = transform_indices[peak.transform_hash]
            peaks.append((state, score, transform_index))
        return peaks

    def send_gui(self):
        self.target.send_gui(self.previous_peaks_raw)

    # TODO: Reimplement as activity
    # def jump(self):
    #     self.logger.debug("[jump] Jump set to True.")
    #     self.waiting_to_jump = True

    # TODO: Reimplement
    # def delete_atom(self, name):
    #     '''deletes target atom'''
    #
    #     if not ":" in name:
    #         del self.streamviews[name]
    #     else:
    #         head, tail = Tools.parse_path(name)
    #         self.streamviews[head].delete_atom(tail)
    #     self.logger.info("Atom {0} deleted from player {1}".format(name, self.name))
    #     # self.send_info_dict()

    # TODO: Reimplement
    # def reset(self, time=None):
    #     '''reset improvisation memory and all sub-streamview'''
    #     time = time if time != None else self.scheduler.time
    #     self.improvisation_memory = deque('', self.max_history_len)
    #     self.self_streamview.reset(time)
    #     for s in self.streamviews.keys():
    #         self.streamviews[s]._reset(time)

    # TODO: Reimplement
    # '''def update_info_dictionary(self):
    #     if self.streamviews!=dict():
    #         self.info_dictionary["streamviews"] = OrderedDict()
    #         tmp_dic = dict()
    #         for k,v in self.streamviews.iteritems():
    #             tmp_dic[k] = dict()
    #             tmp_dic[k]["class"] = v[0].__desc__()
    #             tmp_dic[k]["weight"] = v[1]
    #             tmp_dic[k]["file"] = v[2]
    #             tmp_dic[k]["size"] = v[0].get_length()
    #             tmp_dic[k]["length_beat"] = v[0].metadata["duration_b"]
    #             if k==self.current_streamview:
    #                 self.info_dictionary["streamviews"][k] = dict(tmp_dic[k])
    #         for k,v in tmp_dic.iteritems():
    #             if k!=self.current_streamview:
    #                 self.info_dictionary["streamviews"][k] = dict(tmp_dic[k])
    #     else:
    #         self.info_dictionary["streamviews"] = "empty"
    #     self.info_dictionary["current_streamview"] = str(self.current_streamview)'''

    # TODO: Reimplement
    # def send_buffer(self, atom):
    #     ''' sending buffers in case of audio contents'''
    #     filez = atom.memorySpace.current_file
    #     with open(filez) as f:
    #         name, _ = os.path.splitext(filez)
    #         name = name.split('/')[-1]
    #         g = os.walk('../')
    #         filepath = None
    #         for r, d, fs in g:
    #             for f in fs:
    #                 n, e = os.path.splitext(f)
    #                 if n == name and e != '.json':
    #                     filepath = r + '/' + f
    #         if filepath != None:
    #             self.send('buffer ' + os.path.realpath(filepath))
    #         else:
    #             raise Exception("[ERROR] couldn't find audio file associated with file", filez)

    # TODO: Reimplement as activity
    # def set_nextstate_mod(self, ns):
    #     self.nextstate_mod = ns

    # TODO: Reimplement
    # def get_info_dict(self):
    #     '''returns the dictionary containing all information of the player'''
    #     infodict = {"decide": str(self.decide), "self_influence": str(self.self_influence), "port": self.out_port}
    #     try:
    #         infodict["current_file"] = str(self.current_streamview.atoms["_self"].current_file)
    #     except:
    #         pass
    #     infodict["streamviews"] = dict()
    #     for s, v in self.streamviews.items():
    #         infodict["streamviews"][s] = v.get_info_dict()
    #         infodict["current_atom"] = self.current_atom
    #     infodict["current_streamview"] = self.current_streamview.get_info_dict()
    #     if self.current_streamview.atoms != dict():
    #         if len(self.current_streamview.atoms["_self"].memorySpace) != 0:
    #             self_contents = self.current_streamview.atoms["_self"].memorySpace[-1][1].get_contents()
    #             infodict["current_streamview"]["length_beat"] = \
    #                 self_contents.get_zeta("relative") + self_contents.get_state_length("relative")
    #             infodict["current_streamview"]["length_time"] = \
    #                 self_contents.get_zeta("absolute") + self_contents.get_state_length("absolute")
    #     infodict["subweights"] = self.get_normalized_subweights()
    #     infodict["nextstate_mod"] = self.nextstate_mod
    #     infodict["phase_selectivity"] = self.merge_actions[1].selectivity
    #     infodict["triggering_mode"] = self.scheduler.triggers[self.name]
    #     return infodict

    # TODO: Reimplement
    # def send_info_dict(self):
    #     '''sending the info dictionary of the player'''
    #     infodict = self.get_info_dict()
    #     str_dic = Tools.dic_to_strout(infodict)
    #     self.send("clear", "/infodict")
    #     self.send(self.streamviews.keys(), "/streamviews")
    #     for s in str_dic:
    #         self.send(s, "/infodict")
    #     self.send(self.name, "/infodict-update")
    #     self.logger.debug("[send_info_dict] Updating infodict for player {}.".format(self.name))

    # TODO: Reimplement
    # def set_weight(self, streamview: str, weight: float):
    #     '''setting the weight at target path'''
    #     if not ":" in streamview:
    #         if streamview != "_self":
    #             self.streamviews[streamview].weight = weight
    #         else:
    #             self.self_streamview._atoms["_self"].weight = weight
    #     else:
    #         head, tail = Tools.parse_path(streamview)
    #         self.streamviews[head].set_weight(tail, weight)
    #     self.send_info_dict()
    #     return True
