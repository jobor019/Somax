import logging
from collections import deque
from copy import deepcopy
from functools import reduce
from typing import ClassVar

from somaxlibrary.ActivityPattern import AbstractActivityPattern
from somaxlibrary.Atom import Atom
from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Exceptions import DuplicateKeyError, TransformError
from somaxlibrary.Exceptions import InvalidPath, InvalidCorpus, InvalidConfiguration, InvalidLabelInput
from somaxlibrary.ImprovisationMemory import ImprovisationMemory
from somaxlibrary.Labels import AbstractLabel
from somaxlibrary.MemorySpaces import AbstractMemorySpace
from somaxlibrary.MergeActions import DistanceMergeAction, PhaseModulationMergeAction, AbstractMergeAction, \
    NextStateMergeAction
from somaxlibrary.Parameter import Parametric
from somaxlibrary.Peak import Peak
from somaxlibrary.PeakSelector import AbstractPeakSelector, MaxPeakSelector, DefaultPeakSelector
from somaxlibrary.StreamView import StreamView
from somaxlibrary.Target import Target
from somaxlibrary.Transforms import AbstractTransform
from somaxlibrary.scheduler.ScheduledObject import ScheduledMidiObject, TriggerMode


class Player(ScheduledMidiObject, Parametric):

    def __init__(self, name: str, target: Target, triggering_mode: TriggerMode):
        super(Player, self).__init__(triggering_mode)
        self.logger = logging.getLogger(__name__)
        self.name: str = name  # name of the player
        self.target: Target = target

        self.streamviews: {str: StreamView} = dict()
        self.merge_actions: {str: AbstractMergeAction} = {}
        self.corpus: Corpus = None
        self.peak_selectors: {str: AbstractPeakSelector} = {}

        self.improvisation_memory: ImprovisationMemory = ImprovisationMemory()
        self._previous_peaks: [Peak] = []

        # TODO: Temp
        for merge_action in [DistanceMergeAction, PhaseModulationMergeAction, NextStateMergeAction]:
            self.add_merge_action(merge_action())
        for peak_selector in [MaxPeakSelector(), DefaultPeakSelector()]:
            self.add_peak_selector(peak_selector)

        self._parse_parameters()

        # self.nextstate_mod: float = 1.5   # TODO
        # self.waiting_to_jump: bool = False    # TODO

    def add_merge_action(self, merge_action: AbstractMergeAction, override: bool = False):
        name: str = type(merge_action).__name__
        if name in self.merge_actions and not override:
            raise DuplicateKeyError("A merge action of this type already exists.")
        else:
            self.merge_actions[name] = merge_action
            self._parse_parameters()

    def add_peak_selector(self, peak_selector: AbstractPeakSelector, override: bool = False):
        name: str = type(peak_selector).__name__
        if name in self.merge_actions and not override:
            raise DuplicateKeyError("A merge action of this type already exists.")
        else:
            self.peak_selectors[name] = peak_selector
            self._parse_parameters()

    # def update_parameter_dict(self) -> Dict[str, Union[Parametric, Parameter, Dict]]:
    #     streamviews = {}
    #     merge_actions = {}
    #     peak_selectors = {}
    #     parameters: Dict = {}
    #     for name, streamview in self.streamviews.items():
    #         streamviews[name] = streamview.update_parameter_dict()
    #     for merge_action in self.merge_actions:
    #         key: str = type(merge_action).__name__
    #         merge_actions[key] = merge_action.update_parameter_dict()
    #     for peak_selector in self.peak_selectors:
    #         key: str = type(peak_selector).__name__
    #         peak_selectors[key] = peak_selector.update_parameter_dict()
    #     for name, parameter in self._parse_parameters().items():
    #         parameters[name] = parameter.update_parameter_dict()
    #     self.parameter_dict = {"streamviews": streamviews,
    #                            "merge_actions": merge_actions,
    #                            "peak_selectors": peak_selectors,
    #                            "parameters": parameters}
    #     return self.parameter_dict

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

        event_and_transforms: (CorpusEvent, (AbstractTransform, ...)) = None
        for peak_selector in self.peak_selectors.values():
            event_and_transforms = peak_selector.decide(peaks, self.improvisation_memory, self.corpus, **kwargs)
            if event_and_transforms:
                break
        if not event_and_transforms:
            # TODO: Ensure that this never happens so that this error message can be removed
            raise InvalidConfiguration("All PeakSelectors failed. SoMax requires at least one default peak selector.")

        self.improvisation_memory.append(event_and_transforms[0], scheduler_time, event_and_transforms[1])

        event: CorpusEvent = deepcopy(event_and_transforms[0])
        transforms: (AbstractTransform, ...) = event_and_transforms[1]
        for transform in transforms:
            event = transform.transform(event)

        self._influence_self(event, scheduler_time)
        self.logger.debug(f"[new_event] Player {self.name} successfully created new event.")
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
                    # self.logger.debug(f"[influence] {repr(e)} Likely expected behaviour, only in rare cases an issue.")
                    continue
        else:
            try:
                self._get_atom(path).influence(label, time, **kwargs)
            except InvalidLabelInput as e:
                # self.logger.debug(f"[influence] {repr(e)} Likely expected behaviour, only in rare cases an issue.")
                pass


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
        self._parse_parameters()

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
        self._parse_parameters()

    def read_corpus(self, filepath: str):
        self.corpus = Corpus(filepath)
        for streamview in self.streamviews.values():
            streamview.read(self.corpus)
        self.target.send_simple("corpus", [self.corpus.name, str(self.corpus.content_type), self.corpus.length()])
        # TODO: info dict
        # self.update_memory_length()
        # self.send_parameter_dict()

    def merged_peaks(self, time: float, history: ImprovisationMemory, corpus: Corpus, **kwargs) -> [Peak]:
        weight_sum: float = 0.0
        for streamview in self.streamviews.values():
            weight_sum += streamview.weight if streamview.is_enabled() else 0.0
        peaks: [Peak] = []
        for streamview in self.streamviews.values():
            normalized_weight = streamview.weight / weight_sum
            for peak in streamview.merged_peaks(time, history, corpus, **kwargs):
                peak.score *= normalized_weight
                peaks.append(peak)

        for merge_action in self.merge_actions.values():
            if merge_action.is_enabled():
                peaks = merge_action.merge(peaks, time, history, corpus, **kwargs)
        self._previous_peaks = peaks
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


    def send_peaks(self, scheduler_time: float):
        # TODO: Remove the lines that have been commented out.
        # self._update_peaks(scheduler_time)
        peak_group: str = self.name
        # merged_peaks: [Peak] = self.merged_peaks(scheduler_time, self.improvisation_memory, self.corpus)
        # self.logger.debug(f"[send_peaks] sending {len(merged_peaks)} merged peaks...")
        # for peak in merged_peaks:
        #     state_index: int = self.corpus.event_closest(peak.time).state_index
        #     self.target.send_simple("peak", [peak_group, state_index, peak.score])
        self.target.send_simple("num_peaks", [peak_group, len(self._previous_peaks)])
        self.logger.debug(f"[send_peaks] sending raw peaks...")
        # TODO: Does not handle nested streamviews
        for streamview in self.streamviews.values():
            for atom in streamview.atoms.values():
                peak_group = "::".join([streamview.name, atom.name])
                peaks: [Peak] = atom.activity_pattern.peaks
                # for peak in peaks:
                #     state_index: int = self.corpus.event_closest(peak.time).state_index
                #     self.target.send_simple("peak", [peak_group, state_index, peak.score])
                self.target.send_simple("num_peaks", [atom.name, len(peaks)])

    def clear(self):
        self.improvisation_memory = ImprovisationMemory()
        for streamview in self.streamviews.values():
            streamview.clear()


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
    #     # self.send_parameter_dict()

    # TODO: Reimplement
    # def reset(self, time=None):
    #     '''reset improvisation memory and all sub-streamview'''
    #     time = time if time != None else self.scheduler.time
    #     self.improvisation_memory = deque('', self.max_history_len)
    #     self.self_streamview.reset(time)
    #     for s in self.streamviews.keys():
    #         self.streamviews[s]._reset(time)

    # TODO: Reimplement
    # '''def update_parameter_dictionary(self):
    #     if self.streamviews!=dict():
    #         self.parameter_dictionary["streamviews"] = OrderedDict()
    #         tmp_dic = dict()
    #         for k,v in self.streamviews.iteritems():
    #             tmp_dic[k] = dict()
    #             tmp_dic[k]["class"] = v[0].__desc__()
    #             tmp_dic[k]["weight"] = v[1]
    #             tmp_dic[k]["file"] = v[2]
    #             tmp_dic[k]["size"] = v[0].get_length()
    #             tmp_dic[k]["length_beat"] = v[0].metadata["duration_b"]
    #             if k==self.current_streamview:
    #                 self.parameter_dictionary["streamviews"][k] = dict(tmp_dic[k])
    #         for k,v in tmp_dic.iteritems():
    #             if k!=self.current_streamview:
    #                 self.parameter_dictionary["streamviews"][k] = dict(tmp_dic[k])
    #     else:
    #         self.parameter_dictionary["streamviews"] = "empty"
    #     self.parameter_dictionary["current_streamview"] = str(self.current_streamview)'''

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
    # def get_parameter_dict(self):
    #     '''returns the dictionary containing all information of the player'''
    #     infodict = {"decide": str(self.decide), "self_influence": str(self.self_influence), "port": self.out_port}
    #     try:
    #         infodict["current_file"] = str(self.current_streamview.atoms["_self"].current_file)
    #     except:
    #         pass
    #     infodict["streamviews"] = dict()
    #     for s, v in self.streamviews.items():
    #         infodict["streamviews"][s] = v.get_parameter_dict()
    #         infodict["current_atom"] = self.current_atom
    #     infodict["current_streamview"] = self.current_streamview.get_parameter_dict()
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
    # def send_parameter_dict(self):
    #     '''sending the info dictionary of the player'''
    #     infodict = self.get_parameter_dict()
    #     str_dic = Tools.dic_to_strout(infodict)
    #     self.send("clear", "/infodict")
    #     self.send(self.streamviews.keys(), "/streamviews")
    #     for s in str_dic:
    #         self.send(s, "/infodict")
    #     self.send(self.name, "/infodict-update")
    #     self.logger.debug("[send_parameter_dict] Updating infodict for player {}.".format(self.name))

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
    #     self.send_parameter_dict()
    #     return True
