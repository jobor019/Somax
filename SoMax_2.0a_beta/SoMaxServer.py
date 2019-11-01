import argparse
import asyncio
import logging
import logging.config
from typing import ClassVar, Any

from maxosc.MaxOsc import Caller
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer

from somaxlibrary.ActivityPattern import AbstractActivityPattern
from somaxlibrary.CorpusBuilder import CorpusBuilder
from somaxlibrary.Exceptions import InvalidPath, InvalidLabelInput, DuplicateKeyError
from somaxlibrary.IOParser import IOParser
from somaxlibrary.Labels import AbstractLabel
from somaxlibrary.MemorySpaces import AbstractMemorySpace
from somaxlibrary.MergeActions import AbstractMergeAction
from somaxlibrary.Player import Player
from somaxlibrary.Target import Target, SimpleOscTarget
from somaxlibrary.Transforms import AbstractTransform
from somaxlibrary.scheduler.ScheduledObject import TriggerMode
from somaxlibrary.scheduler.Scheduler import Scheduler


class SoMaxServer(Caller):

    def __init__(self, in_port: int, ip: str = IOParser.DEFAULT_IP):
        super(SoMaxServer, self).__init__(parse_parenthesis_as_list=False)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing SoMaxServer with input port {in_port} and ip '{ip}'.")
        self.players: {str: Player} = dict()
        self.scheduler = Scheduler()
        self.builder = CorpusBuilder()
        self.ip: str = ip
        self.in_port: int = in_port
        self.server: AsyncIOOSCUDPServer = None
        self.io_parser: IOParser = IOParser()
        # self.send_info_dict()     # TODO: Handle info dict laters

    async def _run(self) -> None:
        self.logger.info("Starting SoMaxServer...")
        osc_dispatcher: Dispatcher = Dispatcher()
        osc_dispatcher.map("/server", self._process_osc)
        osc_dispatcher.set_default_handler(self._unmatched_osc)
        self.server: AsyncIOOSCUDPServer = AsyncIOOSCUDPServer((self.ip, self.in_port), osc_dispatcher,
                                                               asyncio.get_event_loop())
        transport, protocol = await self.server.create_serve_endpoint()
        await self.scheduler.init_async_loop()
        transport.close()
        self.logger.info("SoMaxServer was successfully terminated.")

    async def _gui_callback(self, interval: float = 0.2) -> None:
        # TODO: Temporary solution
        self.logger.info("Initializing GUI callback.")
        while True:
            for player in self.players.values():
                player.send_gui()
            await asyncio.sleep(interval)



    def _process_osc(self, _address, *args):
        # TODO: Move string formatting elsewhere
        args_formatted: [str] = []
        for arg in args:
            if isinstance(arg, str) and " " in arg:
                args_formatted.append("'" + arg + "'")
            else:
                args_formatted.append(str(arg))
        args_str: str = " ".join([str(arg) for arg in args_formatted])
        self.call(args_str)

    def _unmatched_osc(self, address: str, *_args, **_kwargs) -> None:
        self.logger.info("The address {} does not exist.".format(address))

    # TODO: Send properly over OSC
    def send_warning(self, warning: str, *args, **kwargs):
        print(warning)

    ######################################################
    # CREATION OF PLAYERS/STREAMVIEWS/ATOMS
    ######################################################

    def new_player(self, name: str, port: int, ip: str = "", trig_mode: str = ""):
        # TODO: Check if player already exists
        # TODO Parse IP, port
        address: str = self.io_parser.parse_osc_address(name)
        trig_mode: TriggerMode = self.io_parser.parse_trigger_mode(trig_mode)
        target: Target = SimpleOscTarget(address, port, ip)
        self.players[name] = Player(name, target, trig_mode)

        if trig_mode == TriggerMode.AUTOMATIC:
            self.scheduler.add_trigger_event(self.players[name])
        # TODO info_dict
        # self.send_info_dict()
        # player.send_info_dict()

    @staticmethod
    def _osc_callback(self):
        pass  # TODO: implement

    def create_streamview(self, player: str, path: str = "streamview", weight: float = 1.0,
                          merge_actions=""):
        self.logger.debug("[create_streamview] called for player {0} with name {1}, weight {2} and merge actions {3}."
                          .format(player, path, weight, merge_actions))
        path_and_name: [str] = IOParser.parse_streamview_atom_path(path)
        merge_actions: [AbstractMergeAction] = self.io_parser.parse_merge_actions(merge_actions)

        try:
            self.players[player].create_streamview(path_and_name, weight, merge_actions)
        except KeyError:
            self.logger.error(f"Could not create streamview for player '{player}' at path '{path}'.")

    def create_atom(self, player: str, path: str, weight: float = 1.0, label: str = "",
                    activity_type: str = "", memory_type: str = "", self_influenced: bool = False,
                    transforms: (str, ...) = (""), transform_parse_mode=""):
        self.logger.debug(f"[create_atom] called for player {player} with path {path}.")
        path_and_name: [str] = IOParser.parse_streamview_atom_path(path)
        label: ClassVar[AbstractLabel] = self.io_parser.parse_label_type(label)
        activity_type: ClassVar[AbstractActivityPattern] = self.io_parser.parse_activity_type(activity_type)
        memory_type: ClassVar[AbstractMemorySpace] = self.io_parser.parse_memspace_type(memory_type)

        try:
            transforms: [(ClassVar[AbstractTransform], ...)] = self.io_parser.parse_transforms(transforms,
                                                                                               transform_parse_mode)
        except IOError as e:
            self.logger.error(f"{str(e)} Setting Transforms to default.")
            transforms: [(ClassVar[AbstractTransform], ...)] = IOParser.DEFAULT_TRANSFORMS
        try:
            self.players[player].create_atom(path_and_name, weight, label, activity_type, memory_type,
                                             self_influenced, transforms)
        except InvalidPath as e:
            self.logger.error(f"Could not create atom at path {path}. [Message]: {str(e)}")
        except KeyError:
            self.logger.error(f"Could not create atom at path {path}. The parent streamview/player does not exist.")
        except DuplicateKeyError as e:
            self.logger.error(f"{str(e)}. No atom was created.")

    def add_transform(self, player: str, path: str, transforms: [str], parse_mode=""):
        self.logger.debug(f"[add_transform] called for player {player} with path {path}.")
        path_and_name: [str] = self.io_parser.parse_streamview_atom_path(path)
        try:
            transforms: [(ClassVar[AbstractTransform], ...)] = self.io_parser.parse_transforms(transforms, parse_mode)
        except IOError as e:
            self.logger.error(f"{str(e)} No Transform was added.")
            return
        try:
            self.players[player].add_transforms(path_and_name, transforms)
        except KeyError:
            self.logger.error(f"Could not add transform at path {path}. The parent streamview/player does not exist.")

    ######################################################
    # PROCESS METHODS
    ######################################################

    def start(self):
        self.scheduler.start()

    def stop(self):
        """stops the scheduler and reset all players"""
        # TODO: IO Error handling
        self.scheduler.stop()

    ######################################################
    # TIMING METHODS
    ######################################################

    # TODO: Reimplement
    # def set_tempo(self, tempo):
    #     tempo = float(tempo)
    #     self.scheduler.set_tempo(tempo)
    #     self.client.send_message("/tempo", tempo)

    # TODO: Reimplement
    # def set_original_tempo(self, original_tempo):
    #     self.original_tempo = bool(original_tempo)
    #     self.scheduler.set_original_tempo(self.original_tempo)

    ######################################################
    # FEEDBACK METHODS
    ######################################################

    # TODO:Reimplement
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

    def trigger_mode(self, player: str, mode: str):
        trigger_mode: TriggerMode = self.io_parser.parse_trigger_mode(mode)
        try:
            previous_trigger_mode: TriggerMode = self.players[player].trigger_mode
            self.players[player].trigger_mode = trigger_mode
        except KeyError:
            self.logger.error(f"Could not set mode. No player named '{player}' exists.")
            return
        if previous_trigger_mode != trigger_mode and trigger_mode == TriggerMode.AUTOMATIC:
            self.scheduler.add_trigger_event(self.players[player])
        self.logger.debug(f"[trigger_mode]: Trigger mode set to '{trigger_mode}' for player '{player}'.")

    # TODO: Reimplement or remove
    # def new_event(self, player_name, time=None, event=None):
    #     self.logger.debug("[new_event] Call to new_event for player {} at time {} with content {}."
    #                       .format(player_name, time, event))
    #     time = self.scheduler.time if time is None else time
    #     if event is not None:
    #         self.scheduler.reset(player_name)
    #     self.process_intern_event(('ask_for_event', player_name, time, event))
    #     self.logger.debug("[new_event] New event created.")

    def influence(self, player: str, label_keyword: str, value: Any, path: str = "", **kwargs):
        self.logger.debug(f"[influence] called for player '{player}' with path '{path}', "
                          f"label keyword '{label_keyword}', value '{value}' and kwargs {kwargs}")
        try:
            labels: [AbstractLabel] = AbstractLabel.classify_as(label_keyword, value, **kwargs)
        except InvalidLabelInput as e:
            self.logger.error(str(e) + "No action performed.")
            return
        # TODO: Error handling (KeyError players + path_and_name)
        path_and_name: [str] = IOParser.parse_streamview_atom_path(path)
        time: float = self.scheduler.time
        for label in labels:
            self.players[player].influence(path_and_name, label, time, **kwargs)
        if self.players[player].trigger_mode == TriggerMode.MANUAL:
            self.scheduler.add_trigger_event(self.players[player])

    def jump(self, player):
        # TODO: IO Error handling
        self.logger.debug("[jump] called for player {0}.".format(player))
        self.players[player].jump()

    def read_corpus(self, player: str, filepath: str):
        # TODO: IO Error handling
        self.logger.debug(f"[read_corpus] called for player '{player}' and file '{filepath}'.")
        try:
            self.players[player].read_corpus(filepath)
        except KeyError:
            self.logger.error(f"Could not load corpus. No player named '{player}' exists.")

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Launch and manage a SoMaxServer')
    parser.add_argument('in_port', metavar='IN_PORT', type=int, nargs=1,
                        help='in port used by the server')
    # TODO: Ip as input argument

    logging.config.fileConfig('logging.ini', disable_existing_loggers=False)

    args = parser.parse_args()
    in_port = args.in_port[0]
    somax_server = SoMaxServer(in_port)

    async def gather():
        await asyncio.gather(somax_server._run(), somax_server._gui_callback())
    asyncio.run(gather())

