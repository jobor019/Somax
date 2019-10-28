import itertools
import logging
import operator
import os
import random
from collections import deque
###############################################################################
# Player is the main generation unit in SoMax.
# it is roughly composed by three different parts :
#       - generation units : all streamviews in the self.streamviews dictionary,
#           which return their activity profile to guide the event generation
#       - decision units : "decide" functions that selects the event to generate
#           given a set of activity profiles
#       - communication units : connecting with Max, external compatibility
from functools import reduce
from typing import ClassVar, Any

from somaxlibrary import Transforms, Tools
from somaxlibrary.ActivityPattern import AbstractActivityPattern
from somaxlibrary.Atom import Atom
from somaxlibrary.Corpus import Corpus, ContentType
from somaxlibrary.CorpusEvent import CorpusEvent
from somaxlibrary.Exceptions import InvalidPath, InvalidCorpus, InvalidConfiguration, InvalidLabelInput
from somaxlibrary.Labels import AbstractLabel
from somaxlibrary.MaxOscLib import DuplicateKeyError
from somaxlibrary.MemorySpaces import AbstractMemorySpace
from somaxlibrary.MergeActions import DistanceMergeAction, PhaseModulationMergeAction, AbstractMergeAction
from somaxlibrary.Peak import Peak
from somaxlibrary.PeakSelector import AbstractPeakSelector, MaxPeakSelector, DefaultPeakSelector
from somaxlibrary.StreamView import StreamView
from somaxlibrary.Target import Target
from somaxlibrary.Transforms import AbstractTransform
from somaxlibrary.scheduler.ScheduledObject import ScheduledMidiObject, TriggerMode


class Player(ScheduledMidiObject):
    max_history_len = 100  # TODO: Don't think this is ever used

    def __init__(self, name: str, target: Target, triggering_mode: TriggerMode = TriggerMode.MANUAL):
        super(Player, self).__init__(triggering_mode)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Created Player with name '{name}.'")
        self.name: str = name  # name of the player
        self.target: Target = target

        self.streamviews: {str: StreamView} = dict()
        self.improvisation_memory: deque[(CorpusEvent, AbstractTransform)] = deque('', self.max_history_len)
        self.merge_actions: [AbstractMergeAction] = [DistanceMergeAction(), PhaseModulationMergeAction()]
        self.corpus: Corpus = None
        self.peak_selectors: [AbstractPeakSelector] = [MaxPeakSelector(), DefaultPeakSelector()]  # TODO impl. setters

        # self.nextstate_mod: float = 1.5   # TODO
        # self.waiting_to_jump: bool = False    # TODO

        # self.info_dictionary = dict()  # TODO



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

    def _update_peaks(self, time: float) -> None:
        for streamview in self.streamviews.values():
            streamview.update_peaks(time)

    def _merged_peaks(self, time: float, influence_history: [CorpusEvent]) -> [Peak]:
        # TODO: (Maybe) Optimize with sort on insertion instead of afterwards.
        pass

    ######################################################
    ###### GENERATION AND INFLUENCE METHODS

    # TODO: Does currently NOT handle event index if given. Not sure why it would
    def new_event(self, scheduler_time: float, **kwargs) -> CorpusEvent:
        """ Raises: InvalidCorpus """
        self.logger.debug("[new_event] Player {} attempting to create a new event at scheduler time '{}'."
                          .format(self.name, scheduler_time))

        if not self.corpus:
            raise InvalidCorpus(f"No Corpus has been loaded in player '{self.name}'.")

        # TODO: Remove or handle
        # # if event is specified, play it now
        # if event_index != None:
        #     self.reset()
        #     event_index = int(event_index)
        #     z_, event = self.self_streamview._atoms["_self"].memorySpace[event_index]
        #     # using actual transformation?
        #     transforms = [Transforms.NoTransform()]
        #     self.waiting_to_jump = False

        self._update_peaks(scheduler_time)
        peaks: [Peak] = self.merged_peaks(scheduler_time, self.improvisation_memory, self.corpus, **kwargs)

        if self.waiting_to_jump:
            self.logger.debug("[new_event] Player {} jumping due to waiting_to_jump set to true.".format(self.name))

        # TODO: Implement as a label/activity pattern
        # # if going to jump, erases peak in neighbour event
        # if self.waiting_to_jump:
        #     self.logger.debug("[new_event] Player {} jumping due to waiting_to_jump set to true.".format(self.name))
        #     zetas = peaks.get_dates_list()
        #     states, _ = self.self_streamview._atoms["_self"].memorySpace.get_events(zetas)
        #     for i in range(0, len(states)):
        #         if states[i].index == self.improvisation_memory[-1][0].index + 1:
        #             del peaks[i]
        #
        #     self.waiting_to_jump = False

        event_and_transform: (CorpusEvent, AbstractTransform) = None
        for peak_selector in self.peak_selectors:
            event_and_transform = peak_selector.decide(peaks, self.improvisation_memory, self.corpus, **kwargs)
            if event_and_transform:
                break
        if not event_and_transform:
            # TODO: Ensure that this never happens so that this error message can be removed
            raise InvalidConfiguration("All PeakSelectors failed. SoMax requires at least one default peak selector.")

        self.improvisation_memory.append(event_and_transform)

        # TODO: Multiple transforms
        event: CorpusEvent = event_and_transform[0]
        transform: AbstractTransform = event_and_transform[1]
        output_event: CorpusEvent = transform.decode(event)

        self._influence_self(output_event, scheduler_time)

        return output_event

        # for transform in transforms:
        #     event = transform.decode(event)
        # # add event to improvisation memory
        # self.improvisation_memory.append((event, transforms))
        # # influences private streamview if auto-influence activated
        # if self.self_influence:
        #     self.self_streamview.influence("_self", scheduler_time, event.label())
        # # sends state num
        # self.send([event.index, event.get_contents().get_zeta(), event.get_contents().get_state_length()], "/state")
        # self.logger.debug("[new_event] Player {} created a new event with content {}."
        #                   .format(self.name, event.get_contents()))
        # return event

    # def new_content(self, date):
    #     ''' returns new contents'''
    #     event = new_event(date)
    #     return event.get_contents().get_contents()

    def _influence_self(self, event: CorpusEvent, time: float) -> None:
        atoms: [Atom] = self._self_atoms()
        labels: [AbstractLabel] = event.labels
        for atom in atoms:
            for label in labels:
                try:
                    atom.influence(label, time)
                except InvalidLabelInput:
                    continue

    # TODO: Pass time from SoMaxServer (gotten through Scheduler)
    def influence(self, path: [str], label: AbstractLabel, time: float, **kwargs) -> None:
        """ Raises: InvalidLabelInput."""
        self._get_atom(path).influence(label, time, **kwargs)

        # self.logger.debug("[influence] Player {} initialized call to influence with path {}, args {} and kwargs {}"
        #                   .format(self.name, path, args, kwargs))
        # time = self.scheduler.get_time()
        # pf, pr = Tools.parse_path(path)
        # if pf in self.streamviews.keys():
        #     self.streamviews[pf].influence(pr, time, *args, **kwargs)
        #     self.logger.debug("[influence] Completed successfully.")
        # else:
        #     self.logger.error("Call to influence failed: Player {} does not have a streamview with name {}."
        #                       .format(self.name, pf))

    def jump(self):
        self.logger.debug("[jump] Jump set to True.")
        self.waiting_to_jump = True

    def goto(self, state=None):
        # TODO: expose to OSC
        self.pending_event = state

    ######################################################
    ###### UNIT GENERATION AND DELETION

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
                    self_influenced: bool):
        """creates atom at target path
        raises: InvalidPath, KeyError, DuplicateKeyError"""
        self.logger.debug(f"[create_atom] Attempting to create atom at {path}...")

        streamview: str = path.pop(0)
        if not path:  # path is empty means no streamview path was given
            raise InvalidPath(f"Cannot create an atom directly in Player.")
        else:
            self.streamviews[streamview].create_atom(path, weight, label_type, activity_type, memory_type,
                                                     self.corpus, self_influenced)

    def delete_atom(self, name):
        '''deletes target atom'''
        # TODO: Expose to OSC
        if not ":" in name:
            del self.streamviews[name]
        else:
            head, tail = Tools.parse_path(name)
            self.streamviews[head].delete_atom(tail)
        self.logger.info("Atom {0} deleted from player {1}".format(name, self.name))
        # self.send_info_dict()

    def read_file(self, filepath: str):
        """ raises: OSError # TODO: Major cleanup on OSChandling"""
        self.corpus = Corpus(filepath)
        for streamview in self.streamviews.values():
            streamview.read(self.corpus)
        # TODO: Temp removed
        # self.update_memory_length()
        # self.send_info_dict()

    # TODO: Fix/get rid of this
    # def set_active_atom(self, streamview: str, atom_name: str):
    #     '''set private atom of the player to target'''
    #     # path, path_bottom = Tools.parse_path(atom_name)
    #     path = streamview
    #     path_bottom = atom_name
    #     if path in self.streamviews.keys():
    #         atom = self.streamviews[path].get_atom_rec(path_bottom)
    #     else:
    #         atom = None
    #     if atom != None:
    #         if "_self" in self.self_streamview._atoms:
    #             del self.self_streamview._atoms["_self"]
    #         self.self_streamview.add_atom(atom, copy=True, replace=True, name="_self")
    #     else:
    #         raise Exception("Could not find atom {0}!".format(atom_name))
    #     if self.current_atom != None:
    #         path, path_bottom = Tools.parse_path(self.current_atom)
    #         if path in self.streamviews.keys():
    #             former_atom = self.streamviews[path].get_atom_rec(path_bottom)
    #             former_atom.active = False
    #     self.current_atom = atom_name
    #     # TODO: Deprecated
    #     if issubclass(atom.memorySpace.contents_type, ClassicAudioContents):
    #         self.send_buffer(atom)
    #     atom.active = True
    #     self.logger.info("Player {0} setting active atom to {1}.".format(self.name, atom_name))
    #     self.update_memory_length()
    #     self.send_info_dict()

    ######################################################
    ###### ACTIVITIES ACCESSORS

    def get_activities(self, date, path=None, weighted=True):
        '''fetches separated activities of the children of target path'''
        if path != None:
            if ":" in path:
                head, tail = Tools.parse_path(path)
                activities = self.streamviews[head].get_activities(date, path=tail)
            else:
                activities = self.streamviews[path].get_activities(date, path=None)
        else:
            activities = dict()
            for n, a in self.streamviews.iteritems():
                w = a.weight if weighted else 1.0
                activities[n] = a.merged_peaks(date, weighted=weighted).mul(w, 0)
            if "_self" in self.self_streamview._atoms:
                w = self.self_streamview.weight if weighted else 1.0
                activities["_self"] = self.self_streamview.merged_peaks(date, weighted=weighted).mul(w, 0)
        return activities

    def merged_peaks(self, time: float, history: [CorpusEvent], corpus: Corpus, **kwargs) -> [Peak]:
        weight_sum: float = float(reduce(lambda a, b: a + b.weight, self.streamviews.values(), 0.0))
        peaks: [Peak] = []
        for streamview in self.streamviews.values():
            normalized_weight = streamview.weight / weight_sum
            for peak in streamview.merged_peaks(time, history, corpus, **kwargs):
                peak *= normalized_weight
                peaks.append(peak)

        for merge_action in self.merge_actions:
            peaks = merge_action.merge(peaks, time, history, corpus, **kwargs)
        return peaks

    def reset(self, time=None):
        '''reset improvisation memory and all sub-streamview'''
        time = time if time != None else self.scheduler.time
        self.improvisation_memory = deque('', self.max_history_len)
        self.self_streamview.reset(time)
        for s in self.streamviews.keys():
            self.streamviews[s]._reset(time)

    def get_weights_sum(self):
        '''getting sum of subweights'''
        p = reduce(lambda x, y: x + y.weight, self.streamviews.values(), 0.0)
        if self.self_streamview._atoms["_self"]:
            p += self.self_streamview._atoms["_self"].weight
        return p

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

    ######################################################
    ###### EXTERNAL METHODS

    def send_buffer(self, atom):
        ''' sending buffers in case of audio contents'''
        filez = atom.memorySpace.current_file
        with open(filez) as f:
            name, _ = os.path.splitext(filez)
            name = name.split('/')[-1]
            g = os.walk('../')
            filepath = None
            for r, d, fs in g:
                for f in fs:
                    n, e = os.path.splitext(f)
                    if n == name and e != '.json':
                        filepath = r + '/' + f
            if filepath != None:
                self.send('buffer ' + os.path.realpath(filepath))
            else:
                raise Exception("[ERROR] couldn't find audio file associated with file", filez)

    def set_self_influence(self, si):
        self.logger.debug(f"[set_self_influence]: Self influence set to {si}.")
        self.self_influence = bool(si)

    def set_nextstate_mod(self, ns):
        self.nextstate_mod = ns

    # def update_memory_length(self):
    #     '''sending active memory length'''
    #     atom = self.current_streamview.atoms["_self"]
    #     if len(atom.memorySpace) > 0:
    #         lastEvent = atom.memorySpace[-1][1]
    #         length = lastEvent.get_contents().get_zeta() + lastEvent.get_contents().get_state_length()
    #         self.send(length, "/memory_length")

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

    def set_weight(self, streamview: str, weight: float):
        '''setting the weight at target path'''
        if not ":" in streamview:
            if streamview != "_self":
                self.streamviews[streamview].weight = weight
            else:
                self.self_streamview._atoms["_self"].weight = weight
        else:
            head, tail = Tools.parse_path(streamview)
            self.streamviews[head].set_weight(tail, weight)
        self.send_info_dict()
        return True

    def get_normalized_subweights(self):
        weights = [];
        weight_sum = 0
        for s in self.streamviews.values():
            weights.append(s.weight)
            weight_sum = weight_sum + s.weight
        return map(lambda x: x / weight_sum, weights)

    ######################################################
    ###### DECIDING METHODS

    def decide_default(self):
        '''default decision method : selecting conjoint event'''
        if len(self.improvisation_memory) != 0:
            previousState = self.improvisation_memory[-1][0]
            new = self.self_streamview._atoms["_self"].memorySpace[
                (previousState.index + 1) % len(self.self_streamview._atoms["_self"].memorySpace)]
            trans = self.improvisation_memory[-1][1]
        else:
            new = self.self_streamview._atoms["_self"].memorySpace[0]
            trans = [Transforms.NoTransform()]
        return new[1], trans

    def decide_chooseMax(self, global_activity):
        '''choosing the state with maximum activity'''
        self.logger.debug(f"[decide_chooseMax] Called with global activity {global_activity}.")
        zetas = global_activity.get_dates_list()
        states, _ = self.self_streamview._atoms["_self"].memorySpace.get_events(zetas)
        v_t = global_activity.get_events_list()
        v = list(map(lambda x: x[0], v_t))
        for i in range(1, len(states)):
            if not states[i] is None:
                if states[i].index == self.improvisation_memory[-1][0].index + 1:
                    v[i] *= self.nextstate_mod
        sorted_values = sorted(list(zip(v, range(len(v)))), key=operator.itemgetter(0), reverse=True)
        max_value = sorted_values[0][0]
        maxes = [n for n in itertools.takewhile(lambda x: x[0] == max_value, sorted_values)]
        next_state_index = random.choice(maxes)
        next_state_index = next_state_index[1]
        next_state, distance = self.self_streamview._atoms["_self"].memorySpace.get_events(zetas[next_state_index])
        return next_state[0], v_t[next_state_index][1]

    ######################################################
    ###### OSC METHODS

    def send(self, content: Any) -> None:
        self.target.send(content)