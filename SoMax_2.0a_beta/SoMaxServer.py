import argparse
import logging
import logging.config
import os
import re
import sys
from functools import reduce

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

import somaxlibrary as sm
from somaxlibrary import MemorySpaces, ActivityPatterns, Events
from somaxlibrary.Contents import AbstractContents
from somaxlibrary.CorpusBuilder import CorpusBuilder
from somaxlibrary.DictClasses import PlayerDict
from somaxlibrary.MergeActions import DistanceMergeAction
from somaxlibrary.Players import Player
from somaxlibrary.SoMaxScheduler import SomaxScheduler

""" 
SoMaxServer is the top class of the SoMax system.
It rules the scheduler, the players and communication between them,
in addition to several macro parameters. Information to players are passed through
the server, adressing /player_name.
It has to be initialized with an OSC incoming port and an OSC outcoming port.
"""


class SoMaxServer:
    max_activity_length = 500  # TODO: What is this?

    def __init__(self, in_port: int, out_port: int):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing SoMaxServer with input port {} and output port {}.".format(in_port, out_port))
        self.in_port: int = in_port
        self.out_port: int = out_port
        self.intern_counter: int = 0

        self.players: PlayerDict = dict()
        self.original_tempo: bool = False

        self.scheduler = SomaxScheduler()
        self.builder = CorpusBuilder()

        osc_dispatcher = Dispatcher()

        osc_dispatcher.map("/server", self.main_osc_callback)
        osc_dispatcher.map("/stopserver", self.stopServer)
        osc_dispatcher.map("/time", self.set_time)
        osc_dispatcher.map("/set_activity_feedback", self.set_activity_feedback)
        osc_dispatcher.map("/update", self.send_info_dict)
        osc_dispatcher.map("default", self.unregistered_callback)

        self.server = BlockingOSCUDPServer(("127.0.0.1", self.in_port), osc_dispatcher)
        self.client = SimpleUDPClient("127.0.0.1", self.out_port)

        # TODO: Ev. verify that connection is up and running
        self.logger.info("Initialization of SoMaxServer was successful.")
        self.send_info_dict()

    def unregistered_callback(self, address: str, *_args, **_kwargs) -> None:
        self.logger.info("The address {} does not exist.".format(address))

    def stopServer(self, *_args):
        """Stops the SoMax server"""
        self.client.send_message("/terminate", [])
        self.server.server_close()

    ######################################################
    # PROCESS METHODS
    ######################################################

    def run(self):
        """runs the SoMax server"""
        self.server.serve_forever()

    def play(self, _time):
        """starts the scheduler and triggers first event if in automatic mode"""
        self.scheduler.start(-self.scheduler.get_pretime())
        for name, player in self.players.items():
            player['player']._reset(self.scheduler.time)
            if player['triggering'] == "automatic":
                self.process_intern_event(('ask_for_event', name, 0))

    def stop(self):
        """stops the scheduler and reset all players"""
        self.scheduler.stop()
        for name, player in self.players.items():
            player['player'].send("stop")

    ######################################################
    # TIMING METHODS
    ######################################################

    def set_timing(self, timing):
        """set timing type"""
        if timing == "relative" or timing == "absolute":
            self.scheduler.timing_type = timing

    def set_time(self, _address, *content):
        """main time routine. set current time of the scheduler, and takes out events to be played"""
        time = float(content[0])
        events = self.scheduler.set_time(time)
        self.increment_internal_counter()
        if self.intern_counter % 10 == 0:
            self.send_activity_profile(time)
        if events:
            self.process_events(events)
        if self.original_tempo:
            tempo = self.scheduler.tempo
            self.client.send_message("/tempo", tempo)

    def set_tempo(self, tempo):
        tempo = float(tempo)
        self.scheduler.set_tempo(tempo)
        self.client.send_message("/tempo", tempo)

    def set_timescale(self, timescale):
        timescale = float(timescale)
        self.scheduler.set_timescale(timescale)

    def set_original_tempo(self, original_tempo):
        self.original_tempo = bool(original_tempo)
        self.scheduler.set_original_tempo(self.original_tempo)

    ######################################################
    # FEEDBACK METHODS
    ######################################################

    def set_activity_feedback(self, _address, content):
        # TODO: Not updated for new osc protocol
        path, player = content[0:2]
        if path == "None":
            path = None
        if player in self.players:
            self.players[player]["output_activity"] = path

    def send_activity_profile(self, time):
        for n, p in self.players.items():
            if p["output_activity"]:
                if p["output_activity"] == 'Player':
                    path = None
                else:
                    path = p["output_activity"]
                activity_profiles = p['player'].get_activities(time, path=path, weighted=True)
                final_activity_str = ""
                for st, pr in activity_profiles.iteritems():
                    for d, e in pr:
                        final_activity_str += str(d) + " " + str(e[0]) + " " + st + " "
                        if len(final_activity_str) > 5000:
                            break
                    if len(final_activity_str) > 5000:
                        break
                p['player'].send(final_activity_str, "/activity")

    def send_info_dict(self, *_args):
        info = dict()
        info["players"] = dict()
        for name, player in self.players.items():
            info["players"][name] = player['player'].get_info_dict()

        def get_class_name(obj):
            return obj.__name__

        def regularize(corpus_list):
            corpus_list = list(map(lambda x: os.path.splitext(x)[0], corpus_list))
            corpus_list = reduce(lambda x, y: str(x) + " " + str(y), corpus_list)
            return corpus_list

        info["memory_types"] = regularize(map(get_class_name, sm.MEMORY_TYPES))
        info["event_types"] = regularize(map(get_class_name, sm.EVENT_TYPES))
        info["label_types"] = regularize(map(get_class_name, sm.LABEL_TYPES))
        info["contents_types"] = regularize(map(get_class_name, sm.CONTENTS_TYPES))
        info["transform_types"] = regularize(map(get_class_name, sm.TRANSFORM_TYPES))
        info["timing_type"] = self.scheduler.timing_type
        corpus_list = filter(lambda x: x[0] != "." and os.path.splitext(x)[1] == ".json", os.listdir("corpus/"))
        corpus_list = map(lambda x: os.path.splitext(x)[0], corpus_list)
        corpus_list = reduce(lambda x, y: str(x) + " " + str(y), corpus_list)
        info["corpus_list"] = corpus_list

        self.client.send_message("/serverdict", "clear")
        messages = sm.Tools.dic_to_strout(info)
        for m in messages:
            self.client.send_message("/serverdict", m)
        self.client.send_message("/serverdict", " ")

    ######################################################
    # EVENTS METHODS
    ######################################################

    def triggering_mode(self, player, mode):
        if mode == "reactive" or mode == "automatic":
            self.players[player]['triggering'] = mode
            self.scheduler.triggers[player] = mode
            self.logger.debug("Triggering mode set to {} for player {}.".format(mode, player))
        else:
            self.logger.error("Invalid input. Triggering mode has to be either reactive or automatic.")

    def new_event(self, player_name, time=None, event=None):
        self.logger.debug("[new_event] Call to new_event for player {} at time {} with content {}."
                          .format(player_name, time, event))
        time = self.scheduler.time if time is None else time
        if event is not None:
            self.scheduler.reset(player_name)
        self.process_intern_event(('ask_for_event', player_name, time, event))
        self.logger.debug("[new_event] New event created.")

    def process_events(self, events):
        for e in events:
            self.logger.debug("Processing event {}...".format(e))
            if e[0] == "server":
                self.process_intern_event(e[1:])
            else:
                player = str(e[0])
                ct = reduce(lambda x, y: str(x) + " " + str(y), e[1])

                self.players[player]["player"].send(ct)

    def process_intern_event(self, content):
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
            event = self.players[player_name]['player'].new_event(time, event)
            self.scheduler.write_event(time, player_name, event)

    def influence(self, player, path, *args, **kwargs):
        self.logger.debug("[influence] called for player {0} with path {1} and args {2}, kwargs {3}."
                          .format(player, path, args, kwargs))
        self.players[player]['player'].influence(path, *args, **kwargs)

    def jump(self, player):
        self.logger.debug("[jump] called for player {0}.".format(player))
        self.players[player]['player'].jump()

    def create_streamview(self, player, name="streamview", weight=1.0, merge_actions=[DistanceMergeAction()]):
        self.logger.debug("[create_streamview] called for player {0} with name {1}, weight {2} and merge actions {3}."
                          .format(player, name, weight, merge_actions))
        self.players[player]['player'].create_streamview(name, weight, merge_actions)

    def create_atom(self, player, name, weight=1.0, label_type=Events.AbstractLabel,
                    contents_type=AbstractContents,
                    event_type=Events.AbstractEvent, activity_type=ActivityPatterns.ClassicActivityPattern,
                    memory_type=MemorySpaces.NGramMemorySpace, memory_file=None):
        self.logger.debug("[create_atom] called for player {0}.".format(player))
        self.players[player]['player'].create_atom(name, weight, label_type, contents_type, event_type, activity_type,
                                                   memory_type, memory_file)

    def read_file(self, player, path, filez):
        self.logger.debug("[read_file] called for player {0} with path {1} and file {2}.".format(player, path, filez))
        self.players[player]['player'].read_file(path, filez)

    def set_self_influence(self, player, si):
        self.logger.debug(f"[set_self_influence] Attemptint to set influence of player {player} to {si}.")
        self.players[player]['player'].set_self_influence(si)

    def set_weight(self, player: str, streamview: str, weight: float):
        self.logger.debug(f"[set_weight] for player {player}, streamview {streamview} set to {weight}.")
        self.players[player]['player'].set_weight(streamview, weight)

    ######################################################
    # PLAYER CREATION METHODS
    ######################################################

    def new_player(self, name, out_port):
        n_player = Player(name, self.scheduler, out_port)
        self.players[name] = {'player': n_player, 'output_activity': None, "triggering": "automatic"}
        self.scheduler.triggers[name] = "automatic"
        self.send_info_dict()
        n_player.send_info_dict()

    ######################################################
    # CORPUS METHODS
    ######################################################

    def build_corpus(self, path, output='corpus/'):
        self.builder.build_corpus(path, output)
        self.logger.info("File {0} has been output at location : {1}".format(path, output))
        self.send_info_dict()

    ######################################################
    # COMMUNICATION METHODS
    ######################################################

    def increment_internal_counter(self):
        self.intern_counter += 1
        if self.intern_counter > sys.maxsize:
            self.intern_counter = 0

    @staticmethod
    def parse_bool(ct):
        if ct == 'True':
            return True
        elif ct == 'False':
            return False
        elif ct == 'None':
            return None
        return ct

    def get(self, path_contents):
        if path_contents is None:
            return self
        if path_contents[0] == "#":
            current_obj = getattr(sm.Transforms, path_contents[1:])
            return current_obj

        assert (len(path_contents) > 1)
        current_obj = self
        for i in range(0, len(path_contents)):
            if i == 0:
                current_obj = current_obj.streamviews[path_contents[i]]
            else:
                current_obj = current_obj.atoms[path_contents[i]]
        return current_obj

    def parse_arguments(self, contents):
        args = []
        kargs = dict()
        for u in contents:
            try:
                if "." in u:
                    u = float(u)
                else:
                    u = int(u)
            except (ValueError, TypeError):
                pass
            if type(u) == str and "=" in u:
                key, value = u.split("=")
                value = str.replace(value, "%20", " ")
                kargs[key] = self.parse_bool(value)
            else:
                args.append(u)
        args = map(self.parse_bool, args)
        return args, kargs

    def main_osc_callback(self, _address, *contents):
        if len(contents) == 0:
            return
        header = contents[0]
        vals = None
        # start splitting command
        if "=" in header:
            header, vals = header.split("=")
        things = header.split(".")
        attributes = things[0:]
        # target object (None for Player, :path:to:stream/atom for sub-atoms)
        obj = self
        it_range = range(0, len(attributes) - 1) if vals != None else range(0, len(attributes))
        for i in it_range:
            current_attribute = attributes[i]
            name, key = re.match(r"([\w]+)(\[.+\])?", current_attribute).groups()
            obj = getattr(obj, name)
            if key:
                key = key[1:-1]
                try:
                    key = int(key)
                except:  # TODO: Replace or catch relevant exceptions
                    pass
                obj = obj[key]
        if vals is None:
            if callable(obj):
                args, kargs = self.parse_arguments(contents[1:])
                obj(*args, **kargs)  # call function
        else:
            # problem here (same for Player?)
            vals = vals.split(",")
            vals, _ = self.parse_arguments(vals)
            vals = vals[0] if len(vals) == 1 else vals
            setattr(obj, attributes[-1], vals)


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
