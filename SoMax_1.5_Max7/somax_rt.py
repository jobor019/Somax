# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 19:04:19 2013

@author: lbg
"""

import numpy as np
import time

from maxosc import MaxOsc

from soma import *




# bridge between max and python

class SomaxPlayer(MaxOsc):

    # number of inlets and outlets
    _inlets=1
    _outlets=2
    location = ""
    # suffix of send/receive ids
    sr_str = '_r'


    def __init__(self, location=""):
        super(SomaxPlayer, self).__init__()
        np.random.seed(169)
        s_ngram_size = 3
        m_ngram_size = 3
        h_ngram_size = 2
        self.bob = Player('pitch', s_ngram_size, 'pitch', m_ngram_size, 'som_chroma', h_ngram_size)
        if location!="":
            self.location = location
            self.bob.set_location(self.location)
        self.run()


    def set_location(self, ret_adr, location):
        self.location = str(location)
        self.bob.set_location(self.location)

    def reset_1(self):
        self.__init__(self.location)
    

    def load(self, ret_adr, filename):
        result = 'ready', 0
        print('loading...')
        self.send_llll(ret_adr,*result)
        self.bob.load_mem(filename)
        print('musical memory loaded')
        result = 'ready', (len(self.bob.s_l.mm_data['data'])-1)
        self.send_llll(ret_adr,*result)

    def new_state(self, ret_adr, date, srid):
        event, new_date = self.bob.new_event(date)
        result = str(srid)+self.sr_str, event, new_date
        #print self.bob.s_l.activity.get_activity()
        print("new state stuff", ret_adr, result)
        self.send_llll(ret_adr,*result)
        #self._outlet(2, "new_event", "self", "zetas", self.bob.new_event_histo[0][0])
        #self._outlet(2, "new_event", "self", "activities", self.bob.new_event_histo[0][1])
        #self._outlet(2, "new_event", "mel", "zetas", self.bob.new_event_histo[1][0])
        #self._outlet(2, "new_event", "mel", "activities", self.bob.new_event_histo[1][1])
        #self._outlet(2, "new_event", "harmo", "zetas", self.bob.new_event_histo[2][0])
        #self._outlet(2, "new_event", "harmo", "activities", self.bob.new_event_histo[2][1])

    def self_influence(self, ret_adr, date, pitch):
        date_tmp = date
        pre_rep_tmp = pitch
        rep_tmp, a_tmp = self.bob.s_l.k_self_listening.kappa_activation(pre_rep_tmp)
        # mod date_tmp here for target
        kappa_event = [date_tmp, rep_tmp, a_tmp]
        self.bob.s_l.kappa_event_history.append(kappa_event)
        self.bob.s_l.update_player_activity(date_tmp)
        #self._outlet(2, "self", "event_history", self.bob.s_l.kappa_event_history)
        #self._outlet(2, "self", "zetas", self.bob.s_l.activity.zeta)
        #self._outlet(2, "self", "activities", self.bob.s_l.activity.value)



    def pitch_influence(self, ret_adr, date, pitch):
        date_tmp = date
        pre_rep_tmp = pitch
        rep_tmp, a_tmp = self.bob.m_l.k_self_listening.kappa_activation(pre_rep_tmp)
        # mod date_tmp here for target
        kappa_event = [date_tmp, rep_tmp, a_tmp]
        self.bob.m_l.kappa_event_history.append(kappa_event)
        self.bob.m_l.update_player_activity(date_tmp)
        #self._outlet(2, "mel", "event_history", self.bob.s_l.kappa_event_history)
        #self._outlet(2, "mel", "zetas", self.bob.s_l.activity.zeta)
        #self._outlet(2, "mel", "activities", self.bob.s_l.activity.value)

    def harmo_influence(self, ret_adr, *args):
        date_tmp = args[12]
        pre_rep_tmp = args[0:12]
        rep_tmp, a_tmp = self.bob.h_l.k_self_listening.kappa_activation(pre_rep_tmp)
        kappa_event = [date_tmp, rep_tmp, a_tmp]
        self.bob.h_l.kappa_event_history.append(kappa_event)
        self.bob.h_l.update_player_activity(date_tmp)
        #self._outlet(2, "harmo", "event_history", self.bob.s_l.kappa_event_history)
        #self._outlet(2, "harmo", "zetas", self.bob.s_l.activity.zeta)
        #self._outlet(2, "harmo", "activities", self.bob.s_l.activity.value)

    def start(self, ret_adr, date, event, srid):
        self.bob.s_l.event_history = [[date, event-1]]
        self.bob.s_l.activity = ActivityPattern()
        self.bob.m_l.activity = ActivityPattern()
        self.bob.h_l.activity = ActivityPattern()
        self.bob.s_l.kappa_event_history = []
        self.bob.m_l.kappa_event_history = []
        self.bob.h_l.kappa_event_history = []
        self.new_state_1(date, srid)
    	#print self.bob.s_l.activity.zetas

    def jump_1(self):
        self.bob.jump()

    def record_external_event(self, ret_adr, date):
        self.bob.s_l.record_external_event(date)
        if self.bob.s_l.external_events.size > 15:
            self.bob.s_l.external_events = np.delete(self.bob.s_l.external_events,0)

    def adjust_bpm(self, ret_adr, current_bpm, min_bpm, max_bpm, date):
        tic = time.time()
        new_bpm = self.bob.adjust_bpm(current_bpm, min_bpm, max_bpm, date)
        toc = time.time()
        result = 'new_bpm', new_bpm
        self.send_llll(ret_adr,*result)

    def set_verbose(self, ret_adr, verbose):
        if int(verbose)==1:
            self.bob.verbose_mode = True
        elif int(verbose)==0:
            self.bob.verbose_mode = False


    def set_tau_mem_decay(self, ret_adr, tau_mem_decay):
        self.bob.activity.tau_mem_decay = tau_mem_decay

    def set_activation_threshold(self, ret_adr, activation_threshold):
        self.bob.activation_threshold = activation_threshold

    def set_weights(self, ret_adr, *weight):
        self.bob.s_w = weight[0]
        self.bob.m_w = weight[1]
        self.bob.h_w = weight[2]

    def set_phase_ref(self, ret_adr, new_phase_ref):
        self.bob.phase_ref = new_phase_ref

    def set_phase_influence(self, ret_adr, new_phase_influence):
        self.bob.phase_influence = new_phase_influence

    def set_gamma(self, ret_adr, new_gamma):
        self.bob.gamma = new_gamma

    def set_adjust_phase(self, ret_adr, new_adjust_phase):
        self.bob.adjust_phase = new_adjust_phase

    def set_adjust_phase_w(self, ret_adr, *new_phase_adjustment_w):
        self.bob.phase_adjustment_w = new_phase_adjustment_w

    def set_taboo_params(self, ret_adr, *new_taboo_params):
        self.bob.taboo_params = new_taboo_params

    def set_w_length(self, ret_adr, new_w_length):
        self.bob.w_length = new_w_length

    def set_next_state(self, ret_adr, new_next_state):
        self.bob.next_state = new_next_state

    def set_tau_next_state(self, ret_adr, new_tau_next_state):
        self.bob.tau_next_state = new_tau_next_state

    def set_auto_jump_mode(self, ret_adr, new_autojump_mode):
        self.bob.auto_jump_mode = new_autojump_mode

    def set_verbose(self, ret_adr, new_verbose_mode):
        self.bob.verbose_mode = new_verbose_mode


    # srid is send/receive id; always the last element in; first element out
    def get_label(self, ret_adr, event, srid):
        result = str(srid)+self.sr_str, self.bob.s_l.mm_data['data'][event]['slice'][0]
        self.send_llll(ret_adr,*result)

    def get_notes(self, ret_adr, event, srid):
        tmp = self.bob.s_l.mm_data['data'][event]['notes']

        for note_tmp in tmp:
            result = (str(srid)+self.sr_str, note_tmp['note']+note_tmp['time']+
                            [self.bob.s_l.mm_data['data'][event]['beat'][1]])
            self.send_llll(ret_adr,*result)
        self.send_llll(ret_adr,*(str(srid)+self.sr_str,'bang'))

    def get_state_ticks_duration(self, ret_adr, event, srid):
        self.shorten_rests = 1
        is_rest_tmp = self.bob.s_l.mm_data['data'][event]['slice'][0] >= 140
        if is_rest_tmp and self.shorten_rests: # rest state
                result = (str(srid)+self.sr_str,
                  np.mod(0.008*self.bob.s_l.mm_data['data'][event]['time'][1]*
                  self.bob.s_l.mm_data['data'][event]['beat'][1], 480.0))
        else:
            result = (str(srid)+self.sr_str,
                      0.008*self.bob.s_l.mm_data['data'][event]['time'][1]*
                      self.bob.s_l.mm_data['data'][event]['beat'][1])
        self.send_llll(ret_adr,*result)

    def get_bpm(self, ret_adr, event, srid):
        result = (str(srid)+self.sr_str,
                  self.bob.s_l.mm_data['data'][event]['beat'][1])
        self.send_llll(ret_adr,*result)

    def get_hctxt(self, ret_adr, event, srid):
        result = (str(srid)+self.sr_str,
                  self.bob.s_l.mm_data['data'][event]['extras'])
        self.send_llll(ret_adr,*result)



    # learning methods
    def parse_new_slice(self, ret_adr, *args):
        slice_tmp = {}
        slice_tmp['notes'] = []
        slice_tmp['seg'] = [1, 1] # not used for now
        slice_tmp['state'] = len(self.bob.s_l.mm_data['data'])
        slice_tmp['extras'] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0,\
                            0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        indtmp = 0

        while (indtmp < len(args)):
            if str(args[indtmp]) == 'beat':
                slice_tmp['beat'] = list(args[indtmp+1:indtmp+5])
                indtmp += 5
            elif str(args[indtmp]) == 'extras':
                slice_tmp['extras'] = list(args[indtmp+1:indtmp+13])
                indtmp += 13
            elif str(args[indtmp]) == 'note':
                notes_tmp = {}
                notes_tmp['note'] = list(args[indtmp+1:indtmp+4])
                notes_tmp['time'] = list(args[indtmp+4:indtmp+6])
                slice_tmp['notes'].append(notes_tmp)
                indtmp += 6
            elif str(args[indtmp]) == 'slice':
                slice_tmp['slice'] = list(args[indtmp+1:indtmp+3])
                indtmp += 3
            elif str(args[indtmp]) == 'time':
                slice_tmp['time'] = list(args[indtmp+1:indtmp+3])
                indtmp += 3
            else:
                indtmp += 1

        self.bob.s_l.update_memory(slice_tmp)
        # same thing for s_l and h l for now
        # but this is of course very temporary
        self.bob.m_l.update_memory(slice_tmp)
        self.bob.h_l.update_memory(slice_tmp)
        result = 'ready', (len(self.bob.s_l.mm_data['data'])-1) #update size
        self.send_llll(ret_adr,*result)

    def save_as(self, ret_adr, name):
        self.bob.save_mem(str(name))
        print('new memory saved :: ', name)


    # audio tools
    crossfade = 50 #ms

    def set_crossfade(self, ret_adr, new_crossfade):
        self.crossfade = new_crossfade

# TODO: More complicated with buffers

#     def update_buffer(self, ret_adr, main_buff_name, tmp_buff_name, event, tb_pos, t_length):
#         sr = 44100./1000. # sample rate
#
#         mb_pos = self.bob.s_l.mm_data['data'][event]['time'][0]
#
#         main_buff = pyext.Buffer(main_buff_name)
#         tmp_buff = pyext.Buffer(tmp_buff_name)
#         ind_mb_1 = int(np.floor(sr*mb_pos))
#         len_tmp = len(tmp_buff)
#         s_length = int(np.round(sr*t_length))#in samples
# #        print s_length, sr, t_length
#         ind_tb_1 = int(np.floor(sr*tb_pos))
#         to_be_copied = np.array(main_buff[ind_mb_1:ind_mb_1+s_length])
#
#         s_crossfade = int(np.round(self.crossfade*sr))
#
#         if ind_tb_1 + s_crossfade <= len_tmp:
#             ind_tb_2 = ind_tb_1 + s_length
#
#             #print to_be_copied[0:s_crossfade].shape, tmp_buff[ind_tb_1:ind_tb_1+s_crossfade].shape
#
#             to_be_copied[0:s_crossfade] = (np.linspace(0.0, 1.0, s_crossfade)*
#                                     to_be_copied[0:s_crossfade]+
#                                     np.linspace(1.0, 0.0, s_crossfade)*
#                                     tmp_buff[ind_tb_1:ind_tb_1+s_crossfade])
#         else: # >
#             ind_c = len_tmp-ind_tb_1
#
#             to_be_copied[0:ind_c] = (
#                                 np.linspace(0.0, 1.0, s_crossfade)[0:ind_c]*
#                                 to_be_copied[0:ind_c]+
#                                 np.linspace(1.0, 0.0, s_crossfade)[0:ind_c]*
#                                 tmp_buff[ind_tb_1:ind_tb_1+ind_c])
#             to_be_copied[ind_c:s_crossfade] = (
#                         np.linspace(0.0, 1.0, s_crossfade)[ind_c:s_crossfade]*
#                         to_be_copied[ind_c:s_crossfade]+
#                         np.linspace(1.0, 0.0, s_crossfade)[ind_c:s_crossfade]*
#                         tmp_buff[ind_tb_1+ind_c:ind_tb_1+s_crossfade])
#
#         if ind_tb_1 + s_length <= len_tmp:
#             ind_tb_2 = ind_tb_1 + s_length
#             #ind_mb_2 = ind_mb_1+ind_tb_2-ind_tb_1
#             tmp_buff[ind_tb_1:ind_tb_2] = to_be_copied[:]
#         else: # >
#             ind_tb_2 = len_tmp
#             ind_mb_2 = ind_tb_2-ind_tb_1
#             tmp_buff[ind_tb_1:ind_tb_2] =to_be_copied[:ind_mb_2]
#             ind_tb_3 = 0
#             ind_tb_4 = s_length-len_tmp+ind_tb_1
#             tmp_buff[ind_tb_3:ind_tb_4] = to_be_copied[ind_mb_2:s_length]

if __name__ == '__main__':
    s = SomaxPlayer()