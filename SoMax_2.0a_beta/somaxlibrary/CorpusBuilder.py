import json
import os
from typing import Union, Tuple

import numpy as np
from numpy import array, floor, ceil, zeros, arange, round, average, argmax, \
    insert

from somaxlibrary import virfun, MidiTools
from somaxlibrary.MidiTools import SomaxMidiParser, MidiIdx
from somaxlibrary.midi.MidiInFile import MidiInFile


class CorpusBuilder(object):
    MIDI_EXTENSIONS = ['.mid', '.midi']
    AUDIO_EXTENSIONS = ['.wav', '.aiff', '.aif']

    def __init__(self):
        pass

    def build_corpus(self, path: str, output: str = 'corpus/', **kwargs) -> None:
        assert type(path) == str
        filename, _ = os.path.splitext(path.split("/")[-1])
        if not os.path.exists(path):
            raise IOError(f"Could not build corpus. Path '{path}' does not exist")
        if os.path.isdir(path):
            filename = path.split("/")[-1]

        elif os.path.isfile(path):
            # TODO: Change typesig once read_file has been updated
            corpus: dict = self._read_file(path, filename, **kwargs)
        output_filepath: str = os.path.join(os.path.dirname(__file__), '..', output, filename + '.json')
        with open(output_filepath, 'w') as f:
            json.dump(corpus, f)

    def _read_file(self, path, name, **kwargs):
        _, ext = os.path.splitext(path)
        if ext in self.MIDI_EXTENSIONS:
            # TODO: Note! This line has been altered and will currently run harmonic, not melodic parsing.
            note_segmented_corpus_dict = self._read_midi(path, name, **kwargs)
            beat_segmented_corpus_dict = self.read_harmonic_data(path, name, **kwargs)
            corpus_dict = {"name": note_segmented_corpus_dict["name"],
                           "typeID": note_segmented_corpus_dict["typeID"],
                           "note_segmented": note_segmented_corpus_dict,
                           "beat_segmented": beat_segmented_corpus_dict}
        elif ext in self.AUDIO_EXTENSIONS:
            # TODO: Not properly supported yet
            corpus_dict = self.read_audio(path, name, **kwargs)
        else:
            # TODO: Raise error, not print error.
            print("[ERROR] File format not recognized in corpus construction")
        return corpus_dict

    # TODO: Annotate and explain parameters, handle default arguments
    def _read_midi(self, path, name, time_offset=(0.0, 0.0), fg_channels=(1,), bg_channels=range(1, 17), t_step=20,
                   t_delay=40.0, legato=100.0, tolerance=30.0):
        """Notes: absolute: *[1], relative: *[0]"""
        fgmatrix, bgmatrix = self._parse_midi_matrices(path, tuple(fg_channels), tuple(bg_channels), time_offset)
        harmonic_context, t_ref = self._harmonic_context(fgmatrix, bgmatrix)

        # Initializing parameters
        last_note_onset = [0, -1 - tolerance]
        last_slice_onset = list(last_note_onset)
        previous_slice_duration: [float, float] = [-1, -1]
        state_idx = 0

        corpus = dict({'name': name, 'typeID': "MIDI", 'size': 1, 'data': []})
        corpus["data"].append(
            {"state": 0, "tempo": 120, "time": {"absolute": [-1, 0], "relative": [-1, 0]}, "seg": [1, 0],
             "beat": [0.0, 0.0, 0, 0],
             "chroma": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "pitch": 140, "notes": []})
        event = dict()

        for i in range(len(fgmatrix)):
            # note is not in current slice
            if fgmatrix[i][MidiIdx.POSITION_MS] > (last_slice_onset[1] + tolerance):
                # finalizing current slice
                if state_idx > 0:
                    previous_slice_duration = [fgmatrix[i][MidiIdx.POSITION_TICK] - last_slice_onset[0],
                                               fgmatrix[i][MidiIdx.POSITION_MS] - last_slice_onset[1]]
                    corpus["data"][state_idx]["time"]["absolute"][1] = float(previous_slice_duration[1])
                    corpus["data"][state_idx]["time"]["relative"][1] = float(previous_slice_duration[0])

                    pitches: [int] = MidiTools.get_pitch_content(corpus["data"], state_idx, legato)
                    pitch: int = self._calculate_pitch(pitches)
                    if pitch:
                        corpus["data"][state_idx]["pitch"] = pitch
                    # Delete empty slice
                    else:
                        state_idx -= 1

                # create a new state
                state_idx += 1
                event = self._temporary_create_new_state(state_idx, fgmatrix[i], harmonic_context, t_delay, t_ref, t_step)

                # if some notes of previous slice did not end in that slice, add to current slice too
                overlapping_notes: [dict] = self._get_overlapping_notes(corpus["data"][state_idx - 1]["notes"],
                                                                        previous_slice_duration)
                for note in overlapping_notes:
                    event["notes"].append(note)

                # adding the current note from fgmatrix
                note = {"pitch": fgmatrix[i][MidiIdx.NOTE], "velocity": fgmatrix[i][MidiIdx.VEL],
                        "channel": fgmatrix[i][MidiIdx.CHANNEL], "time": dict()}
                note["time"]["absolute"] = [0, fgmatrix[i][MidiIdx.DUR_MS]]
                note["time"]["relative"] = [0, fgmatrix[i][MidiIdx.DUR_TICK]]

                event["notes"].append(note)

                # update variables used during the slicing process
                last_note_onset = [fgmatrix[i][MidiIdx.POSITION_TICK], fgmatrix[i][MidiIdx.POSITION_MS]]
                last_slice_onset = [fgmatrix[i][MidiIdx.POSITION_TICK], fgmatrix[i][MidiIdx.POSITION_MS]]
                corpus["data"].append(event)
            # note in current slice
            else:
                # Add note to slice
                num_notes_in_slice = len(corpus["data"][state_idx]["notes"])
                offset_abs = fgmatrix[i][MidiIdx.POSITION_MS] - corpus["data"][state_idx]["time"]["absolute"][0]
                offset_rel = fgmatrix[i][MidiIdx.POSITION_TICK] - corpus["data"][state_idx]["time"]["relative"][0]
                event["notes"].append(
                    {"pitch": fgmatrix[i][MidiIdx.NOTE], "velocity": fgmatrix[i][MidiIdx.VEL],
                     "channel": fgmatrix[i][MidiIdx.CHANNEL], "time": dict()})
                event["notes"][num_notes_in_slice]["time"]["absolute"] = [offset_abs, fgmatrix[i][MidiIdx.DUR_MS]]
                event["notes"][num_notes_in_slice]["time"]["relative"] = [offset_rel, fgmatrix[i][MidiIdx.DUR_TICK]]

                # extend slice duration
                if (fgmatrix[i][MidiIdx.DUR_MS] + offset_abs) > corpus["data"][state_idx]["time"]["absolute"][1]:
                    corpus["data"][state_idx]["time"]["absolute"][1] = fgmatrix[i][MidiIdx.DUR_MS] + int(offset_abs)
                    corpus["data"][state_idx]["time"]["relative"][1] = fgmatrix[i][MidiIdx.DUR_TICK] + int(offset_rel)

        # Finalizing the last slice (code duplication from above)
        pitches: [int] = MidiTools.get_pitch_content(corpus["data"], state_idx, legato)
        pitch: int = self._calculate_pitch(pitches)
        if pitch:
            corpus["data"][state_idx]["pitch"] = pitch
        # Delete empty slice
        else:
            state_idx -= 1

        frame_idx = int(ceil((fgmatrix[i][MidiIdx.POSITION_MS] + t_delay - t_ref) / t_step))
        if frame_idx <= 0:
            corpus["data"][state_idx]["chroma"] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        else:
            corpus["data"][state_idx]["chroma"] = harmonic_context[:,
                                                  min(frame_idx, int(harmonic_context.shape[1]))].tolist()
        corpus["size"] = state_idx + 1
        return corpus

    def _parse_midi_matrices(self, path: str, fg_channels: Tuple[int, ...], bg_channels: Tuple[int, ...],
                             time_offset: (float, float)):
        parser: SomaxMidiParser = SomaxMidiParser()
        midi_in: MidiInFile = MidiInFile(parser, path)
        midi_in.read()
        midi_data: np.ndarray = array(parser.get_matrix())
        matrices: ([[float]], [[float]]) = MidiTools.split_matrix_by_channel(midi_data, fg_channels, bg_channels)
        fgmatrix: np.ndarray = array(matrices[0])
        bgmatrix: np.ndarray = array(matrices[1])
        fgmatrix[:, MidiIdx.POSITION_TICK] += time_offset[0]
        fgmatrix[:, MidiIdx.POSITION_MS] += time_offset[1]
        bgmatrix[:, MidiIdx.POSITION_TICK] += time_offset[0]
        bgmatrix[:, MidiIdx.POSITION_MS] += time_offset[1]
        return fgmatrix, bgmatrix

    def _harmonic_context(self, fgmatrix, bgmatrix):
        if bgmatrix.size != 0:
            harmonic_context, t_ref = MidiTools.computer_chroma_vector(bgmatrix)
        else:
            self.logger.warning(
                "Warning: no notes in background channels. Computing harmonic context with foreground channels")
            harmonic_context, t_ref = MidiTools.computer_chroma_vector(fgmatrix)
        return harmonic_context, t_ref

    def _calculate_pitch(self, pitches: [int], use_rests: bool = False) -> Union[int, None]:
        # No notes in slice: delete it or return silence
        if len(pitches) == 0:
            if use_rests:  # TODO: Remove or handle. Never occurs but undefined
                return 140  # silence
            else:
                return None
        # Single note in slice: simply take the pitch
        elif len(pitches) == 1:
            return int(pitches[0])
        # Multiple notes in slice: Calculate virtual fundamental
        else:
            virtual_fundamental = virfun.virfun(pitches, 0.293)
            return int(128 + (virtual_fundamental - 8) % 12)

    # TODO: Remove
    def _temporary_create_new_state(self, state_idx: int, fgmatrix_row, harmonic_context, t_delay, t_ref, t_step):
        event = dict()
        event["state"] = int(state_idx)
        event["time"] = dict()
        event["time"]["absolute"] = list([fgmatrix_row[MidiIdx.POSITION_MS], fgmatrix_row[MidiIdx.DUR_MS]])
        event["time"]["relative"] = list([fgmatrix_row[MidiIdx.POSITION_TICK], fgmatrix_row[MidiIdx.DUR_TICK]])
        event["tempo"] = fgmatrix_row[MidiIdx.TEMPO]
        event["chroma"] = self._get_chroma(fgmatrix_row[MidiIdx.POSITION_MS], harmonic_context, t_delay, t_ref, t_step)
        event["pitch"] = 0
        event["notes"] = []
        return event

    def _get_chroma(self, abs_time, harmonic_context, t_delay, t_ref, t_step):
        frame_idx = int(ceil((abs_time + t_delay - t_ref) / t_step))
        if frame_idx <= 0:
            return [0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
        else:
            return harmonic_context[:, min(frame_idx, int(harmonic_context.shape[1]))].tolist()




    # TODO: Rewrite with Note class
    def _get_overlapping_notes(self, previous_state_notes, previous_slice_duration: (float, float)) -> [dict]:
        overlapping_notes = []
        for k in range(len(previous_state_notes)):
            if (previous_state_notes[k]["time"]["relative"][0]
               + previous_state_notes[k]["time"]["relative"][1]) > previous_slice_duration[0]:
                note_to_add = dict()
                note_to_add["pitch"] = int(previous_state_notes[k]["pitch"])
                note_to_add["velocity"] = int(previous_state_notes[k]["velocity"])
                note_to_add["channel"] = int(previous_state_notes[k]["channel"])
                note_to_add["time"] = dict()
                note_to_add["time"]["relative"] = list(
                    previous_state_notes[k]["time"]["relative"])
                note_to_add["time"]["absolute"] = list(
                    previous_state_notes[k]["time"]["absolute"])
                note_to_add["time"]["relative"][0] = note_to_add["time"]["relative"][0] - float(
                    previous_slice_duration[0])
                note_to_add["time"]["absolute"][0] = note_to_add["time"]["absolute"][0] - float(
                    previous_slice_duration[1])
                if note_to_add["time"]["absolute"][0] > 0:
                    note_to_add["velocity"] = int(previous_state_notes[k]["velocity"])
                else:
                    note_to_add["velocity"] = 0
                overlapping_notes.append(note_to_add)
        return overlapping_notes

    def read_harmonic_data(self, path, name, time_offset=[0.0, 0.0], fg_channels=[1, 2, 3, 4], bg_channels=range(1, 17),
                           t_step=20,
                           tDelay=40.0, legato=100.0, tolerance=30.0):
        # TODO: Once up and running, rewrite this!! It's a monster of dictionaries, matrices with duplicated data
        #   (fgmatrix, matrix), magic number matrices that aren't used (variable `matrix`: index 1,2,3,4 could just
        #   be zeros, 8,9 shouldn't exist at all). Also, shitloads of code duplication from melodic parsing above, but
        #   entangled in a way so rewriting will be very difficult.
        #   Once everything is working, design proper test for these and rewrite code from scratch.
        # TODO: Also note that nn, vel and ch are not used at all in the _h file. Could be replaced with zeros (or empty)
        #
        # TODO: Finally, the note content ("notes" dict) is not used __at all__ in any real-time performance, only to
        #   calculate chroma at the end. Hence, this should be removed entirely from the json file.
        #
        # On fgmatrix vs matrix. fgmatrix is the per-note sliced matrix, matrix is the per-beat sliced matrix. Hence
        #  fgmatrix[:, 1] and fgmatrix[:, 0] varies in duration and length, while matrix[:,0] is equivalent to the index
        #  of the slice and matrix[:,1] is always 1.
        #  Note that 0 (onset in tick) and 1 (duration in tick) correspond to relative time. But this doesn't
        #  necessarily hold for note onsets

        # absolute: *[1], relative: *[0]
        parser = SomaxMidiParser()
        midi_in = MidiInFile(parser, path)
        midi_in.read()
        midi_data = array(parser.get_matrix())
        fgmatrix, bgmatrix = MidiTools.split_matrix_by_channel(midi_data, fg_channels, bg_channels)

        corpus = dict({'name': name, 'typeID': "MIDI", 'size': 1, 'data': []})
        corpus["data"].append(
            {"state": 0, "tempo": 120, "time": {"absolute": [-1, 0], "relative": [-1, 0]}, "seg": [1, 0],
             "beat": [0.0, 0.0, 0, 0],
             "chroma": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "pitch": 140, "notes": []})
        current_phrase = 1

        fgmatrix = array(fgmatrix)
        indices = arange(floor(min(fgmatrix[:, MidiIdx.POSITION_TICK])), ceil(max(fgmatrix[:, MidiIdx.POSITION_TICK])))

        matrix = zeros((indices.size, MidiIdx.NUM_INDICES))
        matrix[:, MidiIdx.POSITION_TICK] = indices
        matrix[:, MidiIdx.DUR_TICK] = 1.0  # the length of each slice when beat-segmented is always exactly one beat.
        matrix[:, MidiIdx.CHANNEL] = 1  # TODO pointless placeholder
        matrix[:, MidiIdx.NOTE] = 60  # TODO pointless placeholder
        matrix[:, MidiIdx.VEL] = 100  # TODO pointless placeholder

        for k in range(indices.size):
            beat_position: float = matrix[k, MidiIdx.POSITION_TICK]
            index: np.ndarray = min(np.argwhere(fgmatrix[:, MidiIdx.POSITION_TICK] > beat_position))
            if index.size == 0:
                index = fgmatrix.shape[0]
            if (index > 1) and (abs(fgmatrix[index, MidiIdx.POSITION_TICK] - beat_position)
                                > abs(fgmatrix[index - 1, MidiIdx.POSITION_TICK] - beat_position)):
                index -= 1
            tempo = fgmatrix[index, MidiIdx.TEMPO]
            matrix[k, MidiIdx.POSITION_MS] = fgmatrix[index, MidiIdx.POSITION_MS] \
                                             + round(
                (beat_position - fgmatrix[index, MidiIdx.POSITION_TICK]) * 60000 / tempo)
            matrix[k, MidiIdx.DUR_MS] = round(60000.0 / tempo)
            matrix[k, MidiIdx.TEMPO] = tempo

        if len(bgmatrix) != 0:
            harmonic_context, t_ref = MidiTools.computer_chroma_vector(bgmatrix, t_step)
        else:
            self.logger.warning("No notes in background channels. Computing harmonic context with foreground channels")
            harmonic_context, t_ref = MidiTools.computer_chroma_vector(fgmatrix, t_step)

        last_note_onset = [0, -1 - tolerance]
        last_slice_onset = last_note_onset
        state_idx = 0
        num_notes = indices.size
        global_time_ms = time_offset  # TODO: List here but changed to int below????
        matrix = np.asarray(matrix)

        for i in range(matrix.shape[0]):
            # note is not in current slice
            if matrix[i][MidiIdx.POSITION_MS] > (last_slice_onset[1] + tolerance):
                if state_idx > 0:
                    pitches = MidiTools.get_pitch_content(corpus["data"], state_idx, legato)
                    num_pitches = len(pitches)
                    # No notes in slice: add silence
                    if num_pitches == 0:
                        corpus["data"][state_idx]["pitch"] = 140  # repos
                    # Single note in slice: simply take the pitch
                    if num_pitches == 1:
                        corpus["data"][state_idx]["pitch"] = int(pitches[0])
                    # Multiple notes in slice: Calculate virtual fundamental
                    else:
                        virtualfunTmp = virfun.virfun(pitches, 0.293)
                        corpus["data"][state_idx]["pitch"] = int(128 + virtualfunTmp % 12)

                # create new state
                state_idx += 1
                next_state = dict()
                global_time_ms = matrix[i][MidiIdx.POSITION_MS]
                next_state["state"] = int(state_idx)
                next_state["time"] = dict()
                next_state["time"]["absolute"] = list([global_time_ms, matrix[i][MidiIdx.DUR_MS]])
                next_state["time"]["relative"] = list([matrix[i][0], matrix[i][MidiIdx.DUR_TICK]])
                next_state["tempo"] = fgmatrix[i][MidiIdx.TEMPO]
                frame_idx = ceil((matrix[i][MidiIdx.POSITION_MS] + tDelay - t_ref) / t_step)
                if frame_idx <= 0:
                    next_state["chroma"] = [0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
                else:
                    next_state["chroma"] = harmonic_context[:,
                                           min(int(frame_idx), harmonic_context.shape[1] - 1)].tolist()
                next_state["pitch"] = 0
                next_state["notes"] = []

                previous_slice_duration = [matrix[i][0] - last_slice_onset[0], matrix[i][5] - last_slice_onset[1]]
                num_notes_in_previous_slice = len(corpus["data"][state_idx - 1]["notes"])
                for k in range(0, num_notes_in_previous_slice):
                    if ((corpus["data"][state_idx - 1]["notes"][k]["time"]["absolute"][0] +
                         corpus["data"][state_idx - 1]["notes"][k]["time"]["absolute"][1]) \
                            <= previous_slice_duration[1]):  # note-off went off during the previous slice
                        if (corpus["data"][state_idx - 1]["notes"][k]["time"]["absolute"][0] < 0):
                            corpus["data"][state_idx - 1]["notes"][k]["velocity"] = 0
                            corpus["data"][state_idx - 1]["notes"][k]["time"]["absolute"][0] = int(
                                corpus["data"][state_idx - 1]["notes"][k]["time"]["absolute"][1]) + int(
                                corpus["data"][state_idx - 1]["notes"][k]["time"]["absolute"][0])
                    # note continues ; if still in current slice, add it to the current slice and modify the previous one
                    else:
                        # add it
                        num_notes_in_slice = len(next_state["notes"])

                        note_to_add = dict()
                        note_to_add["pitch"] = corpus["data"][state_idx - 1]["notes"][k]["pitch"]
                        note_to_add["velocity"] = corpus["data"][state_idx - 1]["notes"][k]["velocity"]
                        note_to_add["channel"] = corpus["data"][state_idx - 1]["notes"][k]["channel"]
                        note_to_add["time"] = dict()
                        note_to_add["time"]["relative"] = list(
                            corpus["data"][state_idx - 1]["notes"][k]["time"]["relative"])
                        note_to_add["time"]["absolute"] = list(
                            corpus["data"][state_idx - 1]["notes"][k]["time"]["absolute"])
                        note_to_add["time"]["relative"][0] = note_to_add["time"]["relative"][0] - float(
                            previous_slice_duration[0])
                        note_to_add["time"]["absolute"][0] = note_to_add["time"]["absolute"][0] - float(
                            previous_slice_duration[1])

                        next_state["notes"].append(note_to_add)

                        # modify it
                        corpus["data"][state_idx - 1]["notes"][k]["time"]["absolute"][1] = 0  # TODO: Not sure why

                # add the new note
                num_notes_in_slice = len(next_state["notes"])
                note_to_add = dict()
                note_to_add["pitch"] = matrix[i][3]
                note_to_add["velocity"] = matrix[i][4]
                note_to_add["channel"] = matrix[i][2]
                note_to_add["time"] = dict()
                note_to_add["time"]["absolute"] = [0, matrix[i][6]]
                note_to_add["time"]["relative"] = [0, matrix[i][1]]
                next_state["notes"].append(note_to_add)
                corpus["data"].append(dict(next_state))

                # update variables used during the slicing process
                # last_note_onset = matrix[i][5]
                # last_slice_onset = matrix[i][5]
                last_note_onset = [matrix[i][0], matrix[i][5]]
                last_slice_onset = [matrix[i][0], matrix[i][5]]

            # note in current slice ; updates current slice
            else:
                num_notes_in_slice = len(corpus["data"][state_idx]["notes"])
                offset = matrix[i][5] - corpus["data"][state_idx]["time"]["absolute"][0]
                offset_r = fgmatrix[i][0] - corpus["data"][state_idx]["time"]["relative"][0]
                next_state = dict()
                next_state["pitch"] = matrix[i][3]
                next_state["velocity"] = matrix[i][4]
                next_state["channel"] = matrix[i][2]
                next_state["time"] = dict()
                # next_state["time"]["absolute"] = [0, matrix[i][6]]
                # next_state["time"]["relative"] = [0, fgmatrix[i][1]]
                next_state["time"]["absolute"] = [offset, matrix[i][6]]
                next_state["time"]["relative"] = [offset_r, fgmatrix[i][1]]

                corpus["data"][state_idx]["notes"].append(next_state)

                if ((matrix[i][6] + offset) > corpus["data"][state_idx]["time"]["absolute"][1]):
                    corpus["data"][state_idx]["time"]["absolute"][1] = matrix[i][6] + offset
                # last_note_onset = matrix[i][5]
                last_note_onset = [fgmatrix[i][0], matrix[i][5]]

        # on finalise la slice courante
        global_time_ms = matrix[i][5]
        lastSliceDuration = float(corpus["data"][state_idx]["time"]["absolute"][1])
        nbNotesInLastSlice = len(corpus["data"][state_idx]["notes"])
        for k in range(0, nbNotesInLastSlice):
            if ((corpus["data"][state_idx]["notes"][k]["time"]["absolute"][0]
                 + corpus["data"][state_idx]["notes"][k]["time"]["absolute"][1]) <= lastSliceDuration):
                if (corpus["data"][state_idx]["notes"][k]["time"]["absolute"][0] < 0):
                    corpus["data"][state_idx]["notes"][k]["velocity"] = 0
                    # self.logger.debug("Setting velocity of note", k, "of state", state_idx, "to 0"
                    corpus["data"][state_idx]["notes"][k]["time"]["absolute"][0] = int(
                        corpus["data"][state_idx]["notes"][k]["time"]["absolute"][1]) + int(
                        corpus["data"][state_idx]["notes"][k]["time"]["absolute"][0])  # TODO: What??
                    corpus["data"][state_idx]["notes"][k]["time"]["relative"][0] = int(  # TODO: added for coherence
                        corpus["data"][state_idx]["notes"][k]["time"]["relative"][1]) + int(
                        corpus["data"][state_idx]["notes"][k]["time"]["relative"][0])
        pitches = MidiTools.get_pitch_content(corpus["data"], state_idx, legato)
        if len(pitches) == 0:
            corpus["data"][state_idx]["pitch"] = 140
        elif len(pitches) == 1:
            corpus["data"][state_idx]["pitch"] = int(pitches[0])
        else:
            virtualFunTmp = virfun.virfun(pitches, 0.293)
            corpus["data"][state_idx]["pitch"] = int(128 + virtualFunTmp % 12)

        frame_idx = ceil((matrix[i][5] + tDelay - t_ref) / t_step)
        if (frame_idx <= 0):
            corpus["data"][state_idx]["chroma"] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        else:
            corpus["data"][state_idx]["chroma"] = harmonic_context[:,
                                                  min(int(frame_idx), harmonic_context.shape[1] - 1)].tolist()

        corpus["size"] = state_idx + 1
        return dict(corpus)

    def read_audio(self, path, name, time_offset=0.0, segtype="onsets", hop=512, tau=600.0, usebeats=True,
                   descriptors=["pitch", "chroma"]):
        # importing file
        import librosa
        y, sr = librosa.load(path)
        corpus = dict()
        hop_t = librosa.core.samples_to_time(hop, sr)
        # beat detection
        if usebeats:
            tempo, beats = librosa.beat.beat_track(y)
        else:
            tempo = 120
            beats = arange(0.0, librosa.core.get_duration(y), 0.5)
        # segmentation
        if segtype == "onsets":
            seg = librosa.onset.onset_detect(y)
        elif segtype == "beats":
            seg = beats if usebeats else librosa.beat.beat_track(y)
        elif segtype == "free":
            beats = arange(0.0, librosa.core.get_duration(y), freeInt)
        else:
            raise Exception("[ERROR] : please use a compatible segmentation type (onsets, beats or free)")
        # chroma leaky integration
        # further evolution => leaky integration is filtering, can be accelerated
        harm_ctxt = librosa.feature.chroma_cqt(y, hop_length=hop)
        harm_ctxt_li = array(harm_ctxt)
        for n in range(1, harm_ctxt_li.shape[1]):
            harm_ctxt_li[:, n] = (1 - hop_t / tau) * harm_ctxt_li[:, n - 1] + hop_t / tau * harm_ctxt[:, n]

        # initizalization
        corpus = {"name": name, "typeID": "Audio", "type": 3, "size": 1, "data": []}
        corpus["data"].append({"state": 0, "time": {"absolute": [0.0, 0.0], "relative": [0.0, 0.0]}, \
                               "chroma": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                               "pitch": [140, 0.0], "notes": dict()})
        seg_samp = librosa.core.frames_to_samples(seg) / 512
        beats = insert(beats, len(beats), librosa.core.time_to_frames(librosa.core.get_duration(y)))

        # process
        for o in range(0, len(seg_samp) - 1):
            e = harm_ctxt.shape[1] if o == len(seg_samp) - 1 else seg_samp[o + 1]
            tmp = dict()
            tmp["state"] = o + 1
            tmp["seg"] = [1, 0]
            # time
            current_time = librosa.core.frames_to_time(seg[o])
            next_time = librosa.core.frames_to_time(seg[o + 1])
            tmp["time"] = dict()
            tmp["time"]["absolute"] = [current_time * 1000.0, (next_time - current_time) * 1000.0]
            # cur
            current_beat = int(MidiTools.get_beat(seg[o], beats))  # closer beat
            previous_beat = int(floor(current_beat))
            current_beat_t = librosa.core.frames_to_time(beats[previous_beat])
            if previous_beat < len(beats) - 1:
                next_beat_t = librosa.core.frames_to_time(beats[previous_beat + 1])
                if current_time != next_time:
                    tmp["tempo"] = 60.0 / (next_beat_t - current_beat_t)
                    tmp["time"]["relative"] = [current_beat, next_beat_t - current_beat_t]
                else:
                    tmp["time"]["relative"] = [current_beat, corpus["data"][o]["time"]["relative"][1]]
                    tmp["tempo"] = corpus["data"][o]["time"]["relative"][1]
            else:
                tmp["time"]["relative"] = [current_beat, corpus["data"][o]["time"]["relative"][1]]
                tmp["tempo"] = corpus["data"][o]["time"]["relative"][1]

            pitch_maxs = argmax(harm_ctxt[:, seg_samp[o]:e], axis=0)
            tmp["chroma"] = average(harm_ctxt_li[:, seg_samp[o]:e], 1).tolist()
            tmp["pitch"] = MidiTools.most_common(pitch_maxs)
            tmp["notes"] = dict()
            corpus["data"].append(tmp)

        return corpus


#####################################################################################################################t#o#o#L#S####################################################################
#############################################TOOLS##############################################################################################################################################
###### TOOOOLS ##########################################################TOOLS#################################################################################################################
#############################################TOOLS##############################################################################################################################################

# Class to transform midi file in MIDI matrix


if __name__ == '__main__':
    corpus_builder: CorpusBuilder = CorpusBuilder()
    corpus_builder.build_corpus("/Users/joakimborg/MaxProjects/somax-dyci2/SoMax_2.0a_beta/Corpus/debussy_part.mid",
                                "corpusbuilder_tests")
    corpus_builder.build_corpus("/Users/joakimborg/MaxProjects/somax-dyci2/SoMax_2.0a_beta/Corpus/best_composition.mid",
                                "corpusbuilder_tests")

    # TODO Temporary test scenario
    with open("/Users/joakimborg/somax2/corpusbuilder_tests/best_composition_pre_rewrite.json", "r") as read_file:
        b1 = json.load(read_file)
    with open("/Users/joakimborg/somax2/corpusbuilder_tests/best_composition.json", "r") as read_file:
        b2 = json.load(read_file)
    with open("/Users/joakimborg/somax2/corpusbuilder_tests/debussy_part_pre_rewrite.json", "r") as read_file:
        d1 = json.load(read_file)
    with open("/Users/joakimborg/somax2/corpusbuilder_tests/debussy_part.json", "r") as read_file:
        d2 = json.load(read_file)

    assert b1 == b2
    assert d1 == d2
    print("Temporary tests successfully terminated")
