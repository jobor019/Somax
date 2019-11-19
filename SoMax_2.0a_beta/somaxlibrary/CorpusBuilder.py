import json
import os
from typing import List

import numpy as np
from numpy import array, floor, ceil, zeros, arange, round, average, argmax, \
    insert

from somaxlibrary import virfun, MidiTools
from somaxlibrary.MidiTools import SomaxMidiParser, MidiIdx
from somaxlibrary.midi.MidiInFile import MidiInFile


class CorpusBuilder(object):
    MIDI_EXTS = ['.mid', '.midi']
    AUDIO_EXTS = ['.wav', '.aiff', '.aif']

    def __init__(self):
        pass

    def build_corpus(self, path: str, output: str = 'corpus/', **kwargs) -> None:
        assert type(path) == str
        filename, _ = os.path.splitext(path.split("/")[-1])
        if not os.path.exists(path):
            raise IOError(f"Could not build corpus, path '{path}' does not exist")
        if os.path.isdir(path):
            filename = path.split("/")[-1]

        elif os.path.isfile(path):
            # TODO: Change typesig once read_file has been updated
            corpus: dict = self.read_file(path, filename, **kwargs)
        output_filepath: str = os.path.join(os.path.dirname(__file__), '..', output, filename + '.json')
        with open(output_filepath, 'w') as f:
            json.dump(corpus, f)

    def read_file(self, path, name, **kwargs):
        _, ext = os.path.splitext(path)
        if ext in self.MIDI_EXTS:
            # TODO: Note! This line has been altered and will currently run harmonic, not melodic parsing.
            note_segmented_corpus_dict = self.read_midi(path, name, **kwargs)
            beat_segmented_corpus_dict = self.read_harmonic_data(path, name, **kwargs)
            corpus_dict = {"name": note_segmented_corpus_dict["name"],
                           "typeID": note_segmented_corpus_dict["typeID"],
                           "note_segmented": note_segmented_corpus_dict,
                           "beat_segmented": beat_segmented_corpus_dict}
        elif ext in self.AUDIO_EXTS:
            # TODO: Not properly supported yet
            corpus_dict = self.read_audio(path, name, **kwargs)
        else:
            # TODO: Raise error, not print error.
            print("[ERROR] File format not recognized in corpus construction")
        return corpus_dict

    # TODO: Annotate and explain parameters, handle default arguments
    def read_midi(self, path, name, time_offset=(0.0, 0.0), fg_channels=(1,), bg_channels=range(1, 17), t_step=20,
                  t_delay=40.0, legato=100.0, tolerance=30.0):
        # absolute: *[1], relative: *[0]
        parser: SomaxMidiParser = SomaxMidiParser()
        midi_in: MidiInFile = MidiInFile(parser, path)
        midi_in.read()
        midi_data: np.ndarray = array(parser.get_matrix())
        matrices: (List[List[float]], List[List[float]]) = MidiTools.split_matrix_by_channel(midi_data, fg_channels,
                                                                                             bg_channels)
        fgmatrix: np.ndarray = array(matrices[0])
        bgmatrix: np.ndarray = array(matrices[1])
        fgmatrix[:, MidiIdx.POSITION_TICK] += time_offset[0]
        fgmatrix[:, MidiIdx.POSITION_MS] += time_offset[1]
        bgmatrix[:, MidiIdx.POSITION_TICK] += time_offset[0]
        bgmatrix[:, MidiIdx.POSITION_MS] += time_offset[1]
        # creating harmonic context
        if bgmatrix.size != 0:
            harmonic_context, t_ref = MidiTools.computer_chroma_vector(bgmatrix)
        else:
            harmonic_context, t_ref = MidiTools.computer_chroma_vector(fgmatrix)

        # Initializing parameters
        last_note_onset = [0, -1 - tolerance]
        last_slice_onset = list(last_note_onset)
        state_idx = 0
        global_time_ms = time_offset
        corpus = dict({'name': name, 'typeID': "MIDI", 'size': 1, 'data': []})
        corpus["data"].append(
            {"state": 0, "tempo": 120, "time": {"absolute": [-1, 0], "relative": [-1, 0]}, "seg": [1, 0],
             "beat": [0.0, 0.0, 0, 0],
             "chroma": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "pitch": 140, "notes": []})
        event = dict()

        # Running over matrix' notes
        for i in range(len(fgmatrix)):
            # note is not in current slice
            if fgmatrix[i][MidiIdx.POSITION_MS] > (last_slice_onset[1] + tolerance):
                # finalizing current slice
                if state_idx > 0:
                    previous_slice_duration = [fgmatrix[i][MidiIdx.POSITION_TICK] - last_slice_onset[0],
                                               fgmatrix[i][MidiIdx.POSITION_MS] - last_slice_onset[1]]
                    corpus["data"][state_idx]["time"]["absolute"][1] = float(previous_slice_duration[1])
                    corpus["data"][state_idx]["time"]["relative"][1] = float(previous_slice_duration[0])
                    pitches: list = MidiTools.get_pitch_content(corpus["data"], state_idx, legato)
                    # No notes in slice: delete it
                    if len(pitches) == 0:
                        if useRests:  # TODO: Remove or handle. Never occurs but undefined
                            corpus["data"][state_idx]["pitch"] = 140  # silence
                        else:
                            state_idx -= 1
                    # Single note in slice: simply take the pitch
                    elif len(pitches) == 1:
                        corpus["data"][state_idx]["pitch"] = int(pitches[0])
                    # Multiple notes in slice: Calculate virtual fundamental
                    else:
                        virtual_fundamental = virfun.virfun(pitches, 0.293)
                        corpus["data"][state_idx]["pitch"] = int(128 + (virtual_fundamental - 8) % 12)

                # create a new state
                state_idx += 1
                global_time_ms = float(fgmatrix[i][MidiIdx.POSITION_MS])

                event = dict()
                event["state"] = int(state_idx)
                event["time"] = dict()
                event["time"]["absolute"] = list([global_time_ms, fgmatrix[i][MidiIdx.DUR_MS]])
                event["time"]["relative"] = list([fgmatrix[i][MidiIdx.POSITION_TICK], fgmatrix[i][MidiIdx.DUR_TICK]])
                event["tempo"] = fgmatrix[i][MidiIdx.TEMPO]
                frame_idx = int(ceil((fgmatrix[i][MidiIdx.POSITION_MS] + t_delay - t_ref) / t_step))
                if frame_idx <= 0:
                    event["chroma"] = [0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
                else:
                    event["chroma"] = harmonic_context[:, min(frame_idx, int(harmonic_context.shape[1]))].tolist()
                event["pitch"] = 0
                event["notes"] = []

                # if some notes of previous slice did not end in that slice, add to current slice too
                for k in range(len(corpus["data"][state_idx - 1]["notes"])):
                    if (corpus["data"][state_idx - 1]["notes"][k]["time"]["relative"][0] +
                        corpus["data"][state_idx - 1]["notes"][k]["time"]["relative"][1]) > previous_slice_duration[0]:
                        note_to_add = dict()
                        note_to_add["pitch"] = int(corpus["data"][state_idx - 1]["notes"][k]["pitch"])
                        note_to_add["velocity"] = int(corpus["data"][state_idx - 1]["notes"][k]["velocity"])
                        note_to_add["channel"] = int(corpus["data"][state_idx - 1]["notes"][k]["channel"])
                        note_to_add["time"] = dict()
                        note_to_add["time"]["relative"] = list(
                            corpus["data"][state_idx - 1]["notes"][k]["time"]["relative"])
                        note_to_add["time"]["absolute"] = list(
                            corpus["data"][state_idx - 1]["notes"][k]["time"]["absolute"])
                        note_to_add["time"]["relative"][0] = note_to_add["time"]["relative"][0] - float(
                            previous_slice_duration[0])
                        note_to_add["time"]["absolute"][0] = note_to_add["time"]["absolute"][0] - float(
                            previous_slice_duration[1])
                        if note_to_add["time"]["absolute"][0] > 0:
                            note_to_add["velocity"] = int(corpus["data"][state_idx - 1]["notes"][k]["velocity"])
                        else:
                            note_to_add["velocity"] = 0
                        event["notes"].append(note_to_add)

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
                last_note_onset = [fgmatrix[i][MidiIdx.POSITION_TICK], fgmatrix[i][MidiIdx.POSITION_MS]]

        # Finalizing the last slice (code duplication from above)
        pitches = MidiTools.get_pitch_content(corpus["data"], state_idx, legato)
        if len(pitches) == 0:
            if useRests:
                corpus["data"][state_idx]["pitch"] = 140  # silence
            else:
                state_idx -= 1  # delete slice
        elif len(pitches) == 1:
            corpus["data"][state_idx]["pitch"] = int(pitches[0])
        else:
            virtual_fundamental = virfun.virfun(pitches, 0.293)
            corpus["data"][state_idx]["pitch"] = int(128 + (virtual_fundamental - 8) % 12)

        frame_idx = int(ceil((fgmatrix[i][MidiIdx.POSITION_MS] + t_delay - t_ref) / t_step))
        if frame_idx <= 0:
            corpus["data"][state_idx]["chroma"] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        else:
            corpus["data"][state_idx]["chroma"] = harmonic_context[:,
                                                  min(frame_idx, int(harmonic_context.shape[1]))].tolist()
        corpus["size"] = state_idx + 1
        return corpus

    def read_harmonic_data(self, path, name, time_offset=[0.0, 0.0], fg_channels=[1, 2, 3, 4], bg_channels=range(1, 17),
                           tStep=20,
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
        fgmatrix, bgmatrix = MidiTools.split_matrix_by_channel(midi_data, fg_channels,
                                                               bg_channels)  # de-interlacing information

        corpus = dict({'name': name, 'typeID': "MIDI", 'size': 1, 'data': []})
        corpus["data"].append(
            {"state": 0, "tempo": 120, "time": {"absolute": [-1, 0], "relative": [-1, 0]}, "seg": [1, 0],
             "beat": [0.0, 0.0, 0, 0], \
             "chroma": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "pitch": 140, "notes": []})
        current_phrase = 1

        fgmatrix = array(fgmatrix)
        cd = arange(floor(min(fgmatrix[:, MidiIdx.POSITION_TICK])), ceil(max(fgmatrix[:, MidiIdx.POSITION_TICK])))

        matrix = zeros((cd.size, 10))
        matrix[:, 0] = cd
        matrix[:, 1] = 1.0  # the length of each slice when beat-segmented is always exactly one beat.
        matrix[:, 2] = 1
        matrix[:, 3] = 60
        matrix[:, 4] = 100

        for k in range(0, cd.size):
            beatPosTemp = matrix[k, 0]
            indTmp = min(np.argwhere(fgmatrix[:, 0] > beatPosTemp))
            if indTmp.size == 0:
                indTmp = fgmatrix.shape[0]
            if (indTmp > 1) and (abs(fgmatrix[indTmp, 0] - beatPosTemp) > abs(fgmatrix[indTmp - 1, 0] - beatPosTemp)):
                indTmp -= 1
            # print indTmp
            bpmTmp = fgmatrix[indTmp, 7]
            matrix[k, 5] = fgmatrix[indTmp, 5] + round((beatPosTemp - fgmatrix[indTmp, 0]) * 60000 / bpmTmp)
            matrix[k, 6] = 1.0 * round(60000.0 / bpmTmp)
            matrix[k, 7] = bpmTmp
            matrix[k, 8] = 2
            matrix[k, 9] = 2

        # print matrix

        if (len(bgmatrix) != 0):
            hCtxt, tRef = MidiTools.computer_chroma_vector(bgmatrix, tStep)
        else:
            print("Warning: no notes in background channels. Computing harmonic context with foreground channels")
            hCtxt, tRef = MidiTools.computer_chroma_vector(fgmatrix, tStep)

        lastNoteOnset = [0, -1 - tolerance]
        lastSliceOnset = lastNoteOnset
        stateIdx = 0
        nbNotes = cd.size
        global_time = time_offset  # TODO: List here but changed to int below????
        nextState = dict()
        matrix = np.asarray(matrix)
        for i in range(0, matrix.shape[0]):  # on parcourt les notes de la matrice
            if (matrix[i][5] > lastSliceOnset[1] + tolerance):  # la note n'est pas consideree dans la slice courante

                if stateIdx > 0:
                    tmpListOfPitches = MidiTools.get_pitch_content(corpus["data"], stateIdx,
                                                                   legato)  # on obtient l'etiquette de la slice precedente
                    l = len(tmpListOfPitches)
                    if l == 0:
                        corpus["data"][stateIdx]["pitch"] = 140  # repos
                    if l == 1:
                        corpus["data"][stateIdx]["pitch"] = int(tmpListOfPitches[0])
                    else:
                        virtualfunTmp = virfun.virfun(tmpListOfPitches, 0.293)
                        corpus["data"][stateIdx]["pitch"] = int(128 + virtualfunTmp % 12)

                # create new state
                stateIdx += 1
                nextState = dict()
                global_time = matrix[i][5]
                nextState["state"] = int(stateIdx)
                nextState["time"] = dict()
                nextState["time"]["absolute"] = list([global_time, matrix[i][6]])
                nextState["time"]["relative"] = list([matrix[i][0], matrix[i][1]])
                nextState["tempo"] = fgmatrix[i][7]
                frameNbTmp = ceil((matrix[i][5] + tDelay - tRef) / tStep)
                if frameNbTmp <= 0:
                    nextState["chroma"] = [0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
                else:
                    nextState["chroma"] = hCtxt[:, min(int(frameNbTmp), hCtxt.shape[1] - 1)].tolist()
                nextState["pitch"] = 0
                nextState["notes"] = []
                # previousSliceDuration = matrix[i][5] - lastSliceOnset
                previousSliceDuration = [matrix[i][0] - lastSliceOnset[0], matrix[i][5] - lastSliceOnset[1]]
                numNotesInPreviousSlice = len(corpus["data"][stateIdx - 1]["notes"])
                for k in range(0, numNotesInPreviousSlice):
                    if ((corpus["data"][stateIdx - 1]["notes"][k]["time"]["absolute"][0] +
                         corpus["data"][stateIdx - 1]["notes"][k]["time"]["absolute"][1]) \
                            <= previousSliceDuration[1]):  # note-off went off during the previous slice
                        if (corpus["data"][stateIdx - 1]["notes"][k]["time"]["absolute"][0] < 0):
                            corpus["data"][stateIdx - 1]["notes"][k]["velocity"] = 0

                            # self.logger.debug("Setting velocity of note {0} of state {1} to 0.".format(k, stateIdx - 1))
                            corpus["data"][stateIdx - 1]["notes"][k]["time"]["absolute"][0] = int(
                                corpus["data"][stateIdx - 1]["notes"][k]["time"]["absolute"][1]) + int(
                                corpus["data"][stateIdx - 1]["notes"][k]["time"]["absolute"][0])
                    else:  # note continues ; if still in current slice, add it to the current slice and modify the previous one
                        # add it
                        numNotesInSlice = len(nextState["notes"])

                        note_to_add = dict()
                        note_to_add["pitch"] = corpus["data"][stateIdx - 1]["notes"][k]["pitch"]
                        note_to_add["velocity"] = corpus["data"][stateIdx - 1]["notes"][k]["velocity"]
                        note_to_add["channel"] = corpus["data"][stateIdx - 1]["notes"][k]["channel"]
                        note_to_add["time"] = dict()
                        note_to_add["time"]["relative"] = list(
                            corpus["data"][stateIdx - 1]["notes"][k]["time"]["relative"])
                        note_to_add["time"]["absolute"] = list(
                            corpus["data"][stateIdx - 1]["notes"][k]["time"]["absolute"])
                        note_to_add["time"]["relative"][0] = note_to_add["time"]["relative"][0] - float(
                            previousSliceDuration[0])
                        note_to_add["time"]["absolute"][0] = note_to_add["time"]["absolute"][0] - float(
                            previousSliceDuration[1])

                        nextState["notes"].append(note_to_add)

                        # modify it
                        corpus["data"][stateIdx - 1]["notes"][k]["time"]["absolute"][1] = 0  # TODO: Not sure why

                # add the new note
                numNotesInSlice = len(nextState["notes"])
                note_to_add = dict()
                note_to_add["pitch"] = matrix[i][3]
                note_to_add["velocity"] = matrix[i][4]
                note_to_add["channel"] = matrix[i][2]
                note_to_add["time"] = dict()
                note_to_add["time"]["absolute"] = [0, matrix[i][6]]
                note_to_add["time"]["relative"] = [0, matrix[i][1]]
                nextState["notes"].append(note_to_add)
                corpus["data"].append(dict(nextState))

                # update variables used during the slicing process
                # lastNoteOnset = matrix[i][5]
                # lastSliceOnset = matrix[i][5]
                lastNoteOnset = [matrix[i][0], matrix[i][5]]
                lastSliceOnset = [matrix[i][0], matrix[i][5]]

            # note in current slice ; updates current slice
            else:
                numNotesInSlice = len(corpus["data"][stateIdx]["notes"])
                offset = matrix[i][5] - corpus["data"][stateIdx]["time"]["absolute"][0]
                offset_r = fgmatrix[i][0] - corpus["data"][stateIdx]["time"]["relative"][0]
                nextState = dict()
                nextState["pitch"] = matrix[i][3]
                nextState["velocity"] = matrix[i][4]
                nextState["channel"] = matrix[i][2]
                nextState["time"] = dict()
                # nextState["time"]["absolute"] = [0, matrix[i][6]]
                # nextState["time"]["relative"] = [0, fgmatrix[i][1]]
                nextState["time"]["absolute"] = [offset, matrix[i][6]]
                nextState["time"]["relative"] = [offset_r, fgmatrix[i][1]]

                corpus["data"][stateIdx]["notes"].append(nextState)

                if ((matrix[i][6] + offset) > corpus["data"][stateIdx]["time"]["absolute"][1]):
                    corpus["data"][stateIdx]["time"]["absolute"][1] = matrix[i][6] + offset
                # lastNoteOnset = matrix[i][5]
                lastNoteOnset = [fgmatrix[i][0], matrix[i][5]]

        # on finalise la slice courante
        global_time = matrix[i][5]
        lastSliceDuration = float(corpus["data"][stateIdx]["time"]["absolute"][1])
        nbNotesInLastSlice = len(corpus["data"][stateIdx]["notes"])
        for k in range(0, nbNotesInLastSlice):
            if ((corpus["data"][stateIdx]["notes"][k]["time"]["absolute"][0]
                 + corpus["data"][stateIdx]["notes"][k]["time"]["absolute"][1]) <= lastSliceDuration):
                if (corpus["data"][stateIdx]["notes"][k]["time"]["absolute"][0] < 0):
                    corpus["data"][stateIdx]["notes"][k]["velocity"] = 0
                    # self.logger.debug("Setting velocity of note", k, "of state", stateIdx, "to 0"
                    corpus["data"][stateIdx]["notes"][k]["time"]["absolute"][0] = int(
                        corpus["data"][stateIdx]["notes"][k]["time"]["absolute"][1]) + int(
                        corpus["data"][stateIdx]["notes"][k]["time"]["absolute"][0])  # TODO: What??
                    corpus["data"][stateIdx]["notes"][k]["time"]["relative"][0] = int(  # TODO: added for coherence
                        corpus["data"][stateIdx]["notes"][k]["time"]["relative"][1]) + int(
                        corpus["data"][stateIdx]["notes"][k]["time"]["relative"][0])
        tmpListOfPitches = MidiTools.get_pitch_content(corpus["data"], stateIdx, legato)
        if len(tmpListOfPitches) == 0:
            corpus["data"][stateIdx]["pitch"] = 140
        elif len(tmpListOfPitches) == 1:
            corpus["data"][stateIdx]["pitch"] = int(tmpListOfPitches[0])
        else:
            virtualFunTmp = virfun.virfun(tmpListOfPitches, 0.293)
            corpus["data"][stateIdx]["pitch"] = int(128 + virtualFunTmp % 12)

        frameNbTmp = ceil((matrix[i][5] + tDelay - tRef) / tStep)
        if (frameNbTmp <= 0):
            corpus["data"][stateIdx]["chroma"] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        else:
            corpus["data"][stateIdx]["chroma"] = hCtxt[:, min(int(frameNbTmp), hCtxt.shape[1] - 1)].tolist()

        corpus["size"] = stateIdx + 1
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
