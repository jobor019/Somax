import argparse
import logging
import logging.config
from functools import reduce
from typing import ClassVar, Any

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from IOParser import IOParser
from somaxlibrary.ActivityPattern import ClassicActivityPattern, AbstractActivityPattern
from somaxlibrary.CorpusBuilder import CorpusBuilder
from somaxlibrary.Exceptions import InvalidPath, InvalidLabelInput
from somaxlibrary.Labels import AbstractLabel, MelodicLabel
from somaxlibrary.MaxOscLib import Caller
from somaxlibrary.MemorySpaces import NGramMemorySpace, AbstractMemorySpace
from somaxlibrary.MergeActions import DistanceMergeAction, PhaseModulationMergeAction
from somaxlibrary.Player import Player
from somaxlibrary.SoMaxScheduler import SomaxScheduler
from somaxlibrary.Transforms import NoTransform

""" 
SoMaxServer is the top class of the SoMax system.
It rules the scheduler, the players and communication between them,
in addition to several macro parameters. Information to players are passed through
the server, adressing /player_name.
It has to be initialized with an OSC incoming port and an OSC outcoming port.
"""


class SoMaxServer(Caller):
    max_activity_length = 500  # TODO: What is this?

    DEFAULT_IP = "127.0.0.1"
    DEFAULT_ACTIVITY_TYPE: ClassVar = ClassicActivityPattern
    DEFAULT_MERGE_ACTIONS: (ClassVar, ...) = (DistanceMergeAction, PhaseModulationMergeAction)
    DEFAULT_LABEL_TYPE: ClassVar = MelodicLabel
    DEFAULT_TRANSFORMS: (ClassVar, ...) = (NoTransform,)
    DEFAULT_TRIGGERING_MODE = "automatic"
    DEFAULT_MEMORY_TYPE: ClassVar = NGramMemorySpace

    def __init__(self, in_port: int, out_port: int):
        super(SoMaxServer, self).__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing SoMaxServer with input port {} and output port {}.".format(in_port, out_port))
        self.players: {str: Player} = dict()
        self.scheduler = SomaxScheduler(self.players)
        self.builder = CorpusBuilder()

        self.original_tempo: bool = False

        osc_dispatcher = Dispatcher()
        osc_dispatcher.map("/server", self._main_callback)
        osc_dispatcher.set_default_handler(self._unmatched_callback)

        self.server = BlockingOSCUDPServer((self.DEFAULT_IP, in_port), osc_dispatcher)
        self.client = SimpleUDPClient(self.DEFAULT_IP, out_port)

        # TODO: Ev. verify that connection is up and running
        self.logger.info("Initialization of SoMaxServer was successful.")
        # self.send_info_dict()     # TODO: Handle info dict later

    def _main_callback(self, _address, *args):
        # TODO: Move string formatting elsewhere
        args_formatted: [str] = []
        for arg in args:
            if isinstance(arg, str) and " " in arg:
                args_formatted.append("'" + arg + "'")
            else:
                args_formatted.append(str(arg))
        args_str: str = " ".join([str(arg) for arg in args_formatted])
        self.call(args_str)

    def _unmatched_callback(self, address: str, *_args, **_kwargs) -> None:
        self.logger.info("The address {} does not exist.".format(address))

    # TODO: Send properly over OSC
    def send_warning(self, warning: str, *args, **kwargs):
        print(warning)

    ######################################################
    # CREATION OF PLAYERS/STREAMVIEWS/ATOMS
    ######################################################

    def new_player(self, name, out_port):
        # TODO: Check if player already exists
        # TODO: IO Error handling
        self.players[name] = Player(name, out_port, output_activity=None, triggering=self.DEFAULT_TRIGGERING_MODE)
        # TODO info_dict
        # self.send_info_dict()
        # player.send_info_dict()

    @staticmethod
    def _osc_callback(self):

    def create_streamview(self, player: str, path: str = "streamview", weight: float = 1.0, merge_actions: str = ""):
        # TODO: IO Error handling
        self.logger.debug("[create_streamview] called for player {0} with name {1}, weight {2} and merge actions {3}."
                          .format(player, path, weight, merge_actions))
        path_and_name: [str] = IOParser.parse_streamview_atom_path(path)
        try:
            merge_actions = IOParser.parse_merge_actions(merge_actions)
        except KeyError:
            self.logger.warning(f"Could not parse merge actions from string '{merge_actions}'. Setting to default.")
            merge_actions = self.DEFAULT_MERGE_ACTIONS
        try:
            self.players[player].create_streamview(path_and_name, weight, merge_actions)
        except KeyError:
            self.logger.error(f"Could not create streamview for player '{player}' at path '{path}'.")

    def create_atom(self, player: str, path: str, weight: float = 1.0, label_type: str = "",
                    activity_type: str = "", memory_type: str = "", self_influenced: bool = False):
        self.logger.debug(f"[create_atom] called for player {player} with path {path}.")
        path_and_name: [str] = IOParser.parse_streamview_atom_path(path)

        try:
            label_type: ClassVar[AbstractLabel] = IOParser.parse_label_type(label_type)
        except KeyError:
            self.logger.warning(f"Unable to parse '{label_type}' as a Label Type. Setting to default.")
            label_type = self.DEFAULT_LABEL_TYPE

        try:
            activity_type: ClassVar[AbstractActivityPattern] = IOParser.parse_activity_type(activity_type)
        except KeyError:
            self.logger.warning(f"Unable to parse '{activity_type}' as an Activity Pattern. Setting to default.")
            activity_type = self.DEFAULT_ACTIVITY_TYPE

        try:
            memory_type: ClassVar[AbstractMemorySpace] = IOParser.parse_memspace_type(memory_type)
        except KeyError:
            self.logger.warning(f"Unable to parse '{memory_type}' as a MemorySpace. Setting to default.")
            memory_type = self.DEFAULT_MEMORY_TYPE
        try:
            self.players[player].create_atom(path_and_name, weight, label_type, activity_type, memory_type, self_influenced)
        except InvalidPath as e:
            self.logger.error(f"Could not create atom at path {path}. [Message]: {str(e)}")
        except KeyError:
            self.logger.error(f"Could not create atom at path {path}. The parent streamview does not exist.")



    ######################################################
    # PROCESS METHODS
    ######################################################

    def run(self):
        """runs the SoMax server"""
        # TODO: IO Error handling
        self.server.serve_forever()

    def play(self):
        """starts the scheduler and triggers first event if in automatic mode"""
        # TODO: IO Error handling
        self.scheduler.start(-self.scheduler.get_pretime())
        for player in self.players.values():
            player.reset(self.scheduler.time)
            # TODO: Handle once Server-Scheduler-Player refactor is completed
            # if player['triggering'] == "automatic":
            #     self.process_intern_event(('ask_for_event', name, 0))

    def stop(self):
        """stops the scheduler and reset all players"""
        # TODO: IO Error handling
        self.scheduler.stop()
        # TODO: Migrate this to be called via Scheduler
        # for name, player in self.players.items():
        #     player['player'].send("stop")

    # TODO: Merge with stop
    # def stopServer(self, *_args):
    #     """Stops the SoMax server"""
    #     self.client.send_message("/terminate", [])
    #     self.server.server_close()

    ######################################################
    # TIMING METHODS
    ######################################################

    def set_timing(self, timing):
        """set timing type"""
        # TODO: IO Error handling
        if timing == "relative" or timing == "absolute":
            self.scheduler.timing_type = timing

    def set_time(self, _address, *content):
        """main time routine. set current time of the scheduler, and takes out events to be played"""
        # TODO: Refactor to Scheduler/time module
        time = float(content[0])
        events = self.scheduler.set_time(time)
        # self.increment_internal_counter()
        # if self.intern_counter % 10 == 0:
        #     self.send_activity_profile(time)
        # TODO: Move this to Scheduler
        if events:
            self.process_events(events)
        if self.original_tempo:
            tempo = self.scheduler.tempo
            self.client.send_message("/tempo", tempo)

    def set_tempo(self, tempo):
        # TODO: IO Error handling
        tempo = float(tempo)
        self.scheduler.set_tempo(tempo)
        self.client.send_message("/tempo", tempo)

    def set_timescale(self, timescale):
        # TODO: IO Error handling
        timescale = float(timescale)
        self.scheduler.set_timescale(timescale)

    def set_original_tempo(self, original_tempo):
        # TODO: IO Error handling
        self.original_tempo = bool(original_tempo)
        self.scheduler.set_original_tempo(self.original_tempo)

    ######################################################
    # FEEDBACK METHODS
    ######################################################

    # TODO: Not updated for new osc protocol
    # def set_activity_feedback(self, _address, content):
    #     path, player = content[0:2]
    #     if path == "None":
    #         path = None
    #     if player in self.players:
    #         self.players[player]["output_activity"] = path

    # TODO: activity_profile
    # def send_activity_profile(self, time):
    #     for n, p in self.players.items():
    #         if p["output_activity"]:
    #             if p["output_activity"] == 'Player':
    #                 path = None
    #             else:
    #                 path = p["output_activity"]
    #             activity_profiles = p['player'].get_activities(time, path=path, weighted=True)
    #             final_activity_str = ""
    #             for st, pr in activity_profiles.iteritems():
    #                 for d, e in pr:
    #                     final_activity_str += str(d) + " " + str(e[0]) + " " + st + " "
    #                     if len(final_activity_str) > 5000:
    #                         break
    #                 if len(final_activity_str) > 5000:
    #                     break
    #             p['player'].send(final_activity_str, "/activity")

    # TODO: info_dict
    # def send_info_dict(self, *_args):
    #     info = dict()
    #     info["players"] = dict()
    #     for name, player in self.players.items():
    #         info["players"][name] = player['player'].get_info_dict()
    #
    #     def get_class_name(obj):
    #         return obj.__name__
    #
    #     def regularize(corpus_list):
    #         corpus_list = list(map(lambda x: os.path.splitext(x)[0], corpus_list))
    #         corpus_list = reduce(lambda x, y: str(x) + " " + str(y), corpus_list)
    #         return corpus_list
    #
    #     info["memory_types"] = regularize(map(get_class_name, sm.MEMORY_TYPES))
    #     info["event_types"] = regularize(map(get_class_name, sm.EVENT_TYPES))
    #     info["label_types"] = regularize(map(get_class_name, sm.LABEL_TYPES))
    #     info["contents_types"] = regularize(map(get_class_name, sm.CONTENTS_TYPES))
    #     info["transform_types"] = regularize(map(get_class_name, sm.TRANSFORM_TYPES))
    #     info["timing_type"] = self.scheduler.timing_type
    #     corpus_list = filter(lambda x: x[0] != "." and os.path.splitext(x)[1] == ".json", os.listdir("corpus/"))
    #     corpus_list = map(lambda x: os.path.splitext(x)[0], corpus_list)
    #     corpus_list = reduce(lambda x, y: str(x) + " " + str(y), corpus_list)
    #     info["corpus_list"] = corpus_list
    #
    #     self.client.send_message("/serverdict", "clear")
    #     messages = sm.Tools.dic_to_strout(info)
    #     for m in messages:
    #         self.client.send_message("/serverdict", m)
    #     self.client.send_message("/serverdict", " ")

    ######################################################
    # EVENTS METHODS
    ######################################################

    def triggering_mode(self, player, mode):
        # TODO: IO Error cleanup
        if mode == "reactive" or mode == "automatic":
            self.players[player]['triggering'] = mode
            self.scheduler.triggers[player] = mode
            self.logger.debug("Triggering mode set to {} for player {}.".format(mode, player))
        else:
            self.logger.error("Invalid input. Triggering mode has to be either reactive or automatic.")

    def new_event(self, player_name, time=None, event=None):
        # TODO: IO Error handling
        self.logger.debug("[new_event] Call to new_event for player {} at time {} with content {}."
                          .format(player_name, time, event))
        time = self.scheduler.time if time is None else time
        if event is not None:
            self.scheduler.reset(player_name)
        self.process_intern_event(('ask_for_event', player_name, time, event))
        self.logger.debug("[new_event] New event created.")

    def process_events(self, events):
        # TODO: Refactor to Scheduler
        for e in events:
            self.logger.debug("Processing event {}...".format(e))
            if e[0] == "server":
                self.process_intern_event(e[1:])
            else:
                player = str(e[0])
                ct = reduce(lambda x, y: str(x) + " " + str(y), e[1])

                self.players[player]["player"].send(ct)

    def process_intern_event(self, content):
        # TODO: Refactor to Scheduler
        self.logger.debug("Processing internal event with content {}.".format(content))
        if content[0] == 'ask_for_event':
            player_name = content[1]
            if len(content) > 2:
                time = content[2]
            else:
                time = self.scheduler.time
            if len(content) > 3:
                event = content[3]
            else:
                event = None
            # TODO: Remove event. Should never accept event as input
            event = self.players[player_name].new_event(time)
            self.scheduler.write_event(time, player_name, event)

    def influence(self, player: str, path: str, label_keyword: str, value: Any, **kwargs):
        self.logger.debug(f"[influence] called for player {player} with path {path}, label keyword {label_keyword}, "
                          f"value {value} and kwargs {kwargs}")
        try:
            label: AbstractLabel = AbstractLabel.classify_as(label_keyword, value, **kwargs)
        except InvalidLabelInput as e:
            self.logger.error(str(e) + "No action performed.")
            return
        # TODO: Error handling
        path_and_name: [str] = IOParser.parse_streamview_atom_path(path)
        # TODO: We don't need time on insert, only on update (called in new_event)
        time: float = self.scheduler.get_time()
        self.players[player].influence(path_and_name, label, time, **kwargs)


    def jump(self, player):
        # TODO: IO Error handling
        self.logger.debug("[jump] called for player {0}.".format(player))
        self.players[player].jump()

    # TODO: Add path for reading files into specific atoms etc
    def read_file(self, player: str, filepath: str):
        # TODO: IO Error handling
        self.logger.debug(f"[read_file] called for player '{player}' and file '{filepath}'.")
        self.players[player].read_file(filepath)

    def set_self_influence(self, player, si):
        # TODO: IO Error handling
        self.logger.debug(f"[set_self_influence] Attempting to set influence of player {player} to {si}.")
        self.players[player].set_self_influence(si)

    def set_weight(self, player: str, streamview: str, weight: float):
        # TODO: IO Error handling
        self.logger.debug(f"[set_weight] for player {player}, streamview {streamview} set to {weight}.")
        self.players[player].set_weight(streamview, weight)

    ######################################################
    # CORPUS METHODS
    ######################################################

    def build_corpus(self, path, output='corpus/'):
        # TODO: IO Error handling
        self.builder.build_corpus(path, output)
        self.logger.info("File {0} has been output at location : {1}".format(path, output))
        # TODO: Info dict
        # self.send_info_dict()

    ######################################################
    # COMMUNICATION METHODS
    ######################################################

    # TODO: Delete
    # def increment_internal_counter(self):
    #     self.intern_counter += 1
    #     if self.intern_counter > sys.maxsize:
    #         self.intern_counter = 0

    # TODO: Delete
    # @staticmethod
    # def parse_bool(ct):
    #     if ct == 'True':
    #         return True
    #     elif ct == 'False':
    #         return False
    #     elif ct == 'None':
    #         return None
    #     return ct

    # TODO: Delete
    # def get(self, path_contents):
    #     if path_contents is None:
    #         return self
    #     if path_contents[0] == "#":
    #         current_obj = getattr(sm.Transforms, path_contents[1:])
    #         return current_obj
    #
    #     assert (len(path_contents) > 1)
    #     current_obj = self
    #     for i in range(0, len(path_contents)):
    #         if i == 0:
    #             current_obj = current_obj.streamviews[path_contents[i]]
    #         else:
    #             current_obj = current_obj.atoms[path_contents[i]]
    #     return current_obj

    # TODO: Delete
    # def parse_arguments(self, contents):
    #     args = []
    #     kargs = dict()
    #     for u in contents:
    #         try:
    #             if "." in u:
    #                 u = float(u)
    #             else:
    #                 u = int(u)
    #         except (ValueError, TypeError):
    #             pass
    #         if type(u) == str and "=" in u:
    #             key, value = u.split("=")
    #             value = str.replace(value, "%20", " ")
    #             kargs[key] = self.parse_bool(value)
    #         else:
    #             args.append(u)
    #     args = map(self.parse_bool, args)
    #     return args, kargs

    # TODO: Delete
    # def main_callback(self, _address, *contents):
    #     if len(contents) == 0:
    #         return
    #     header = contents[0]
    #     vals = None
    #     # start splitting command
    #     if "=" in header:
    #         header, vals = header.split("=")
    #     things = header.split(".")
    #     attributes = things[0:]
    #     # target object (None for Player, :path:to:stream/atom for sub-atoms)
    #     obj = self
    #     it_range = range(0, len(attributes) - 1) if vals != None else range(0, len(attributes))
    #     for i in it_range:
    #         current_attribute = attributes[i]
    #         name, key = re.match(r"([\w]+)(\[.+\])?", current_attribute).groups()
    #         obj = getattr(obj, name)
    #         if key:
    #             key = key[1:-1]
    #             try:
    #                 key = int(key)
    #             except:  # TODO: Replace or catch relevant exceptions
    #                 pass
    #             obj = obj[key]
    #     if vals is None:
    #         if callable(obj):
    #             args, kargs = self.parse_arguments(contents[1:])
    #             obj(*args, **kargs)  # call function
    #     else:
    #         # problem here (same for Player?)
    #         vals = vals.split(",")
    #         vals, _ = self.parse_arguments(vals)
    #         vals = vals[0] if len(vals) == 1 else vals
    #         setattr(obj, attributes[-1], vals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Launch and manage a SoMaxServer')
    parser.add_argument('in_port', metavar='IN_PORT', type=int, nargs=1,
                        help='in port used by the server')
    parser.add_argument('out_port', metavar='OUT_PORT', type=int, nargs=1,
                        help='out port used by the server')

    logging.config.fileConfig('logging.ini', disable_existing_loggers=False)

    args = parser.parse_args()
    in_port = args.in_port[0]
    out_port = args.out_port[0]
    somax_server = SoMaxServer(in_port, out_port)

    somax_server.run()
