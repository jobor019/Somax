import bisect
import itertools
import operator

import numpy as np
from numpy import floor, zeros, ceil, array, exp, log, arange, maximum, log2, where, dot, power, ones_like, round

from somaxlibrary.midi.MidiOutStream import MidiOutStream


class SomaxMidiParser(MidiOutStream):
    def __init__(self):
        MidiOutStream.__init__(self)
        self.matrix = []
        self.orderedTimeList = []
        self.orderedEventList = []
        self.midiTempo = 500000
        self.realTempo = 120
        self.res = 96
        self.held_notes = dict()
        self.sigs = [[0, (4, 2)]]

    def tempo(self, value):
        self.midiTempo = value
        self.realTempo = 60.0 / value * 1e6

    def header(self, format=0, nTracks=1, division=96):
        self.res = division

    def note_on(self, channel=0, note=0x40, velocity=0x40):
        t = self.abs_time()
        if (velocity == 0x0):
            self.note_off(channel, note, velocity)
        else:
            i = bisect.bisect_right(self.orderedTimeList, t)
            self.orderedTimeList.insert(i, t)

            # self.orderedEventList.insert(i, [self.tickToMS(t), note, velocity, 0.0, channel, self.realTempo])
            self.orderedEventList.insert(i,
                                         [self.tickToQuarterNote(t), 0.0, channel + 1, note, velocity, self.tickToMS(t),
                                          0.0, self.realTempo])
            self.held_notes[(note, channel)] = i

    def note_off(self, channel=0, note=0x40, velocity=0x40):
        try:
            i = self.held_notes[(note, channel)]
            self.orderedEventList[i][6] = self.tickToMS(self.abs_time()) - self.orderedEventList[i][5]
            self.orderedEventList[i][1] = self.tickToQuarterNote(self.abs_time()) - self.orderedEventList[i][0]
            del self.held_notes[(note, channel)]
        except:
            pass

    # print "Warning : note-off at", self.abs_time()

    def eof(self):
        pass

    def tickToMS(self, tick):
        return tick * self.midiTempo / self.res / 1000.0

    def tickToQuarterNote(self, tick):
        return round(tick * 1.0 / self.res, 3)

    def time_signature(self, nn, dd, cc, bb):
        self.sig = (nn, dd)
        if self.abs_time() == 0:
            self.sigs[0] = [0, (nn, dd)]
        else:
            self.sigs.append([self.abs_time(), (nn, dd)])

    def get_matrix(self):
        return self.orderedEventList

    def get_sigs(self):
        return self.sigs


def splitMatrixByChannel(matrix, fgChannels, bgChannels):
    fgmatrix = []
    bgmatrix = []
    for i in range(0, len(matrix)):
        if matrix[i][2] in fgChannels:
            fgmatrix.append(matrix[i])
        if matrix[i][2] in bgChannels:
            bgmatrix.append(matrix[i])
    return fgmatrix, bgmatrix


def getPitchContent(data, state_nb, legato):
    nbNotesInSlice = len(data[state_nb]["notes"])
    tmpListOfPitches = []
    for k in range(0, nbNotesInSlice):
        if (data[state_nb]["notes"][k]["velocity"] > 0) \
                or (data[state_nb]["notes"][k]["time"]["absolute"][0] > legato):
            tmpListOfPitches.append(data[state_nb]["notes"][k]["pitch"])

    return list(set(tmpListOfPitches))


def most_common(L):
    # get an iterable of (item, iterable) pairs
    SL = sorted((x, i) for i, x in enumerate(L))
    # print 'SL:', SL
    groups = itertools.groupby(SL, key=operator.itemgetter(0))

    # auxiliary function to get "quality" for an item
    def _auxfun(g):
        item, iterable = g
        count = 0
        min_index = len(L)
        for _, where in iterable:
            count += 1
            min_index = min(min_index, where)
        # print 'item %r, count %r, minind %r' % (item, count, min_index)
        return count, -min_index

    # pick the highest-count/earliest item
    return max(groups, key=_auxfun)[0]


def get_beat(onset, beats):
    indice = bisect.bisect_left(beats, onset)  # insertion index of the onset in the beats
    current_beat = indice  # get the current beat
    try:
        current_beat += round((onset * 1.0 - beats[indice]) / (beats[indice + 1] - beats[indice]), 1)
    except:
        pass
    return current_beat


def computePitchClassVector(noteMatrix, tStep=20.0, thresh=0.05, m_onset=0.5, p_max=1.0, tau_up=400, tau_down=1000,
                            decayParam=0.5):
    nbNotes = len(noteMatrix)
    matrix = array(noteMatrix)
    tRef = min(matrix[:, 5])
    matrix[:, 5] -= tRef
    tEndOfNM = max(matrix[:, 5] + matrix[:, 6]) + 1000
    nbSteps = int(ceil(tEndOfNM / tStep))
    pVector = zeros((128, nbSteps))
    mVector = zeros((12, nbSteps))
    nbMaxHarmonics = 10;

    for i in range(0, nbNotes):
        if (matrix[i, 5] == 0):
            t_on = 0.0
        else:
            t_on = matrix[i, 5]

        t_off = t_on + matrix[i, 6]

        ind_t_on = int(floor(t_on / tStep))
        ind_t_off = int(floor(t_off / tStep))

        p_t_off = (m_onset - p_max) * exp(-(t_off - t_on) / tau_up) + p_max
        t_end = min(tEndOfNM, t_off - tau_down * log(thresh / p_t_off))
        ind_t_end = int(floor(t_end / tStep))

        p_up = (m_onset - p_max) * exp(-(arange(ind_t_on, ind_t_off) * tStep - t_on) / tau_up) + p_max
        p_down = p_t_off * exp(-(arange(ind_t_off, ind_t_end) * tStep - t_off) / tau_down)

        ind_p = int(matrix[i, 3])  # + 1?

        pVector[ind_p, ind_t_on:ind_t_off] = maximum(pVector[ind_p, ind_t_on:ind_t_off], p_up)
        pVector[ind_p, ind_t_off:ind_t_end] = maximum(pVector[ind_p, ind_t_off:ind_t_end], p_down)

        listOfMidiHarmonics = matrix[i, 3] + np.round(12 * log2(1 + arange(1, nbMaxHarmonics)))
        listOfMidiHarmonics = listOfMidiHarmonics[where(listOfMidiHarmonics < 128)].astype(int)

        if listOfMidiHarmonics.size != 0:
            pVector[listOfMidiHarmonics, ind_t_on:ind_t_off] = maximum(pVector[listOfMidiHarmonics, ind_t_on:ind_t_off], \
                                                                       dot(power(
                                                                           ones_like(listOfMidiHarmonics) * decayParam,
                                                                           arange(1,
                                                                                  listOfMidiHarmonics.size + 1)).reshape(
                                                                           listOfMidiHarmonics.size, 1),
                                                                           p_up.reshape(1, p_up.size)))

            pVector[listOfMidiHarmonics, ind_t_off:ind_t_end] = maximum(
                pVector[listOfMidiHarmonics, ind_t_off:ind_t_end], \
                dot(power(ones_like(listOfMidiHarmonics) * decayParam, arange(1, listOfMidiHarmonics.size + 1)).reshape(
                    listOfMidiHarmonics.size, 1), p_down.reshape(1, p_down.size)))

    for k in range(0, 128):
        ind_pc = k % 12
        mVector[ind_pc, :] = mVector[ind_pc, :] + pVector[k, :]
    return mVector, tRef
