import asyncio
import logging
import time

from somaxlibrary.Corpus import ContentType
from somaxlibrary.CorpusEvent import CorpusEvent, Note
from somaxlibrary.Exceptions import InvalidCorpus
from somaxlibrary.Player import Player
from somaxlibrary.scheduler.ScheduledEvent import ScheduledEvent, MidiEvent, AudioEvent, TriggerEvent, OscEvent, \
    TempoEvent
from somaxlibrary.scheduler.ScheduledObject import TriggerMode


class Scheduler:
    DEFAULT_CALLBACK_INTERVAL = 0.001  # seconds
    TRIGGER_PRETIME = 0.1  # seconds

    def __init__(self, tempo: float = 120.0, callback_interval: int = DEFAULT_CALLBACK_INTERVAL):
        self.logger = logging.getLogger(__name__)
        self._internal_time: float = time.time()
        self.tempo: float = tempo
        self.beat: float = 0.0
        self.callback_interval: int = callback_interval  # in seconds
        self.running: bool = False
        self.queue: [ScheduledEvent] = []  # TODO: NO PREMATURE OPTIMIZIATION PLEASE
        self.tempo_master: Player = None

    def _callback(self):
        self._update_time()
        self._process_internal_events()

    def _process_internal_events(self) -> None:
        events: [ScheduledEvent] = [e for e in self.queue if e.time <= self.beat]
        self.queue = [e for e in self.queue if e.time > self.beat]
        for event in events:
            if type(event) == TempoEvent:
                self._process_tempo_event(event)
            if type(event) == MidiEvent:
                self._process_midi_event(event)
            elif type(event) == AudioEvent:
                self._process_audio_event(event)
            elif type(event) == TriggerEvent:
                self._process_trigger_event(event)
            elif type(event) == OscEvent:
                self._process_osc_event(event)

    def _process_tempo_event(self, tempo_event: TempoEvent) -> None:
        self.tempo = tempo_event.tempo

    def _process_midi_event(self, midi_event: MidiEvent) -> None:
        player: Player = midi_event.player
        player.send_midi()

    def _process_audio_event(self, audio_event: AudioEvent) -> None:
        pass  # TODO

    def _process_trigger_event(self, trigger_event: TriggerEvent) -> None:
        player: Player = trigger_event.player
        try:
            event: CorpusEvent = player.new_event(trigger_event.target_time)
        except InvalidCorpus as e:
            self.logger.error(str(e))
            return

        self.add_corpus_event(player, trigger_event.trigger_time, event)

        if player.trigger_mode == TriggerMode.AUTOMATIC:
            event_scaled_duration: float = event.duration * self.tempo / 60.0
            next_trigger_time: float = trigger_event.trigger_time + event_scaled_duration
            next_target_time: float = trigger_event.target_time + event_scaled_duration
            self._add_trigger_event(player, next_trigger_time, next_target_time)

    def _process_osc_event(self, osc_event: OscEvent) -> None:
        pass

    def add_tempo_event(self, trigger_time: float, tempo: float):
        self.queue.append(TempoEvent(trigger_time, tempo))

    def add_osc_event(self):
        pass  # TODO

    def add_corpus_event(self, player: Player, trigger_time: float, corpus_event: CorpusEvent):
        self._update_time()
        if player is self.tempo_master:
            self.add_tempo_event(trigger_time, corpus_event.tempo)

        if player.corpus.content_type == ContentType.AUDIO:
            event: ScheduledEvent = AudioEvent(trigger_time, player, corpus_event.onset, corpus_event.duration)
            self.queue.append(event)
        elif player.corpus.content_type == ContentType.MIDI:
            # Handle held notes from previous state:
            note_offs_previous: [Note] = [n for n in player.held_notes if n not in corpus_event.held_to()]
            note_ons: [Note] = [n for n in corpus_event.notes if n not in player.held_notes]
            note_offs: [Note] = [n for n in corpus_event.notes if n not in corpus_event.held_from()]
            player.held_notes = corpus_event.held_from()

            # Queue midi events for note ons/offs
            for note in note_offs_previous:
                self.queue.append(MidiEvent(trigger_time, player, note.pitch, 0, note.channel))
            for note in note_ons:
                self.queue.append(MidiEvent(trigger_time + note.onset, player, note.pitch, note.velocity, note.channel))
            for note in note_offs:
                position_in_state: float = note.onset + note.duration
                self.queue.append(MidiEvent(trigger_time + position_in_state, player, note.pitch, 0, note.channel))

    def add_trigger_event(self, player: Player, target_time: float):
        self._add_trigger_event(player, target_time - self.TRIGGER_PRETIME, target_time)

    def _add_trigger_event(self, player: Player, trigger_time: float, target_time: float):
        self.queue.append(TriggerEvent(trigger_time, player, target_time))

    def _sanity_check(self):
        pass  # TODO

    def _update_time(self):
        delta_time: float = time.time() - self._internal_time
        self.beat = delta_time * self.tempo / 60.0

    async def start(self, callback_interval: int = None) -> None:
        self.running = True
        self.callback_interval = self.callback_interval if callback_interval is None else callback_interval
        while self.running:
            self._callback()
            await asyncio.sleep(self.callback_interval)

    def pause(self) -> None:
        self.running = False

    def stop(self) -> None:
        self.running = False
        self.beat = 0
