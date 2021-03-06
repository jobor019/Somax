import tools, virfun, json, os
import readMidi as midi
from numpy import floor, ceil, arange, array, zeros, argwhere, asarray, concatenate
from bisect import bisect_left
import librosa, pickle, numpy, scipy.io

# this is the operation model for every corpus operations.
# this meta-operation is initialized with the name of the corpus
#   and have a process function, which has to output a file at the output_file location.
class MetaOp():
	def __init__(self, corpus_name):
		self.corpus_name  = corpus_name

	def process(self, output_file, **args):
		print "this is a meta class for the SoMax corpus operations."
		return 0


	def setParameter(self, parameter,value):
		print "Here is the function that permits access to internal parameters from outside."
		print "This aims to give access only to the parameters relevant for the user."

	def printParms(self):
		print "Gives a user feedback of the parameters."
# this is a higher level abstraction to formalize the classic operations made on OMax and co. operations
#	 based on the segmentation of the files in states. This is why the init function requires one more argument,
#	  which is the paths of the files to analyze.

class SegmentationOp(MetaOp):
	admitted_extensions = [] # contains the file extensions that the operation can read.
	def __init__(self, file_paths, corpus_name):
		MetaOp.__init__(self, corpus_name)
		self.file_paths = file_paths

		# for the overload commodity, the process function is divided in three function :
		#	-- a readFiles function which reads the files to acquire the raw data
		#   -- a readData function which withdraws the wanted information from the raw data
		#   -- a writeFiles which writes the acquired data into the final corpus file at output_file location.

	def process(self, output_file):
		self.raw_data = self.readFiles(self.file_paths)
		self.result = self.readData(self.raw_data)
		self.writeFiles(self.result, output_file)

	def readFiles(self, file_paths):
		print "Here is the function reading the corpus files and returning the appropriate data structure."
		return []

	def readData(self, data):
		print "Here is the main process of the operation that will apply to data."

	def writeFiles(self, result, output_file):
		print "Writes the results in the given output_file location."


# this is the classic Somax operation, used for the main file.
class OpSomaxStandard(SegmentationOp):
	admitted_extensions = ['.mid', '.midi', '.wav', '.aif', '.aiff']
	def __init__(self, file_paths, corpus_name):
		SegmentationOp.__init__(self, file_paths, corpus_name)
		self.corpus_name = corpus_name
		self.tDelay = 40
		self.fgChannels = [1]
		self.bgChannels = range(2,17)
		self.tolerance = 30.0
		self.legato = 100.0
		self.tStep = 20
		self.corpus = dict()
		self.matrix = []
		self.verbose = 0
		self.mod12 = False
		self.segtype = "onsets"
		self.segtypes = ["onsets", "free", "beats"]
		self.usebeats = True
		self.file_inds = []
		self.hop = 512 # self.hop used in chromagram in samples (has to be 2^n)
		self.freeInt = 0.5 # interval of the free segmentation in seconds
		ext = os.path.splitext(file_paths[0])
		if ext[-1]=='.mid' or ext[-1]=='.midi':
			self.readFiles = self.readMIDIFiles
			self.readData = self.readMIDIData
		elif ext[-1]=='.wav' or ext[-1]=='.aif' or ext[-1]=='.aiff':
			self.readFiles = self.readAudioFiles
			self.readData = self.readAudioData

	def setParameter(self, parameter, value):
		if parameter=='bgChannels':
			if type(value)==type([]):
				self.bgChannels = map(int, value)
				return ''
			else:
				return 'Wrong format of channels!'
		elif parameter=='fgChannels':
			if type(value)==type([]):
				self.fgChannels = map(int, value)
				return ''
			else:
				return 'Wrong format of channels!'
		elif parameter=='segtype':
			if value in self.segtypes:
				self.segtype=value
				return ''
			else:
				return 'The segmentation type must be one of the following : '+str(self.segtypes)
		elif parameter=='mod12':
			if parameter=='True':
				self.mod12=True
				return ''
			elif parameter=='False':
				self.mod12=False
				return ''
			else:
				return 'Please return a boolean!'
		elif parameter=='usebeats':
			if parameter=='True':
				self.usebeats=True
				return ''
			elif parameter=='False':
				self.usebeats=False
				return ''
			else:
				return 'Please return a boolean!'
		elif parameter=='freeInterval':
			try:
				self.freeInt = float(value)
				return ''
			except:
				return 'Enter a float! (in seconds)'
				pass
		else:
			return 'parameter not recognized!'

	def printParams(self, parameter, value):
		print "Foreground Channels : ", self.fgChannels
		print "Background Channels : ", self.bgChannels
		print "Segmentation type : ", self.segtype
		print "Mod 12 : ", self.mod12
		print "Use beats : ", self.usebeats


	def readMIDIFiles(self, file_paths):
		matrix = []
		file_inds = []
		for f in file_paths:
			parser = midi.SomaxMidiParser()
			midi_in = midi.MidiInFile(parser, f)
			midi_in.read()
			if matrix == []:
				matrix = array(parser.get_matrix())
			else:
				tBeatRef, tMsRef = ceil(matrix[-1][0]+matrix[-1][1]), matrix[-1][5] + matrix[-1][6]
				newMatrix = array(parser.get_matrix())
				newMatrix[:, 0]+=tBeatRef
				newMatrix[:, 5]+=tMsRef
				matrix = concatenate((matrix, newMatrix), 0)
			file_inds.append(matrix.shape[0])
		if self.verbose:
			for i in range(0, len(matrix)):
				print matrix[i]
		self.file_inds = []
		mat = numpy.array(matrix)
		scipy.io.savemat('noteMatrix.mat', mdict={'notes': mat})
		return matrix

	def readMIDIData(self, data):
		corpus = dict()
		fgMatrix, bgMatrix = tools.splitMatrixByChannel(data, self.fgChannels, self.bgChannels) #de-interlacing information
		corpus["name"] = self.corpus_name # a changer
		corpus["typeID"] = 'MIDI'
		corpus["type"] = 3
		corpus["size"] = 1
		corpus["data"] = []

		# creating a first state, not really used except for
		corpus["data"].append({"state": 0, "time": [0,0], "seg": [1,0], "beat":[0.0, 0.0, 0, 0], \
			"extras": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "slice":[140, 0.0], "notes":dict()})

		current_phrase = 1
		tmpListOfPitches = []

		if (len(bgMatrix)!=0):
			hCtxt, tRef = tools.computePitchClassVector(bgMatrix, self.tStep)
		else:
			print("Warning: no notes in background channels. Computing harmonic context with foreground channels")
			hCtxt, tRef = tools.computePitchClassVector(fgMatrix, self.tStep)


		lastNoteOnset = -1-self.tolerance
		lastSliceOnset = lastNoteOnset
		stateNb = 0
		globalTime= 0
		tmp = dict()

		for i in range(0,len(fgMatrix)): # on parcourt les notes de la matrice
			if(fgMatrix[i][5]>(lastSliceOnset+self.tolerance)): # la note n'est pas consideree dans la slice courante
				if stateNb>0:
					tmpListOfPitches = tools.getPitchContent(corpus["data"], stateNb, self.legato) # on obtient l'etiquette de la slice precedente
					l = len(tmpListOfPitches)
					if l==0:
						corpus["data"][stateNb]["slice"][0] = 140 # repos
					if l==1:
						corpus["data"][stateNb]["slice"][0] = int(tmpListOfPitches[0])
					else:
						virtualfunTmp = virfun.virfun(tmpListOfPitches, 0.293)
						corpus["data"][stateNb]["slice"][0] = int(128+virtualfunTmp%12)

					if self.mod12:
						corpus["data"][stateNb]["slice"][0]%=12
				if self.verbose:
					print "slice is over, finalizing it"
					for k in range(0,len(corpus["data"])):
						print corpus["data"][k]
						print ""
						print "----------------------------------------"
						print ""

				#create new state
				stateNb+=1
				globalTime = float(fgMatrix[i][5])
				tmp = dict()
				tmp["state"] = int(stateNb)
				tmp["time"] = list([globalTime, fgMatrix[i][6]])
				tmp["seg"] = list([bisect_left(self.file_inds, i), current_phrase])
				tmp["beat"] = list([fgMatrix[i][0], fgMatrix[i][7], 0, 0])
				frameNbTmp = tools.ceil((fgMatrix[i][5]+self.tDelay-tRef)/self.tStep)
				if frameNbTmp<=0:
					tmp["extras"] = [0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.]
				else:
					tmp["extras"] = hCtxt[:, min(int(frameNbTmp), hCtxt.shape[1])].tolist()
				tmp["slice"] = [0, 0.0]
				tmp["notes"] = []

				previousSliceDuration = fgMatrix[i][5] - lastSliceOnset
				corpus["data"][stateNb-1]["time"][1] = previousSliceDuration

				nbNotesInPreviousSlice = len(corpus["data"][stateNb-1]["notes"])
				for k in range(0, nbNotesInPreviousSlice):
					if ((corpus["data"][stateNb-1]["notes"][k]["time"][0]+corpus["data"][stateNb-1]["notes"][k]["time"][1])\
																		<=previousSliceDuration): # note-off went off during the previous slice
						if (corpus["data"][stateNb-1]["notes"][k]["time"][0]<0):
							corpus["data"][stateNb-1]["notes"][k]["note"][1] = 0
							#print "setting velocity of note", k, "of state", stateNb, "to 0"
							corpus["data"][stateNb-1]["notes"][k]["time"][0] = float(corpus["data"][stateNb-1]["notes"][k]["time"][1]) + float(corpus["data"][stateNb-1]["notes"][k]["time"][0])
					else: #note continues ; if still in current slice, add it to the current slice and modify the previous one
						#add it
						nbNotesInSlice = len(tmp["notes"])
						tmp["notes"].append(dict())
						tmp["notes"][nbNotesInSlice]["note"] = list(corpus["data"][stateNb-1]["notes"][k]["note"])
						tmp["notes"][nbNotesInSlice]["time"] = list(corpus["data"][stateNb-1]["notes"][k]["time"])
						tmp["notes"][nbNotesInSlice]["time"][0] -= previousSliceDuration


						#modify it
						corpus["data"][stateNb-1]["notes"][k]["time"][1] = 0

				#add the new note
				nbNotesInSlice = len(tmp["notes"])
				tmp["notes"].append(dict())
				tmp["notes"][nbNotesInSlice]["note"] = [fgMatrix[i][3], fgMatrix[i][4], fgMatrix[i][2]]
				tmp["notes"][nbNotesInSlice]["time"] = [0, fgMatrix[i][6]]
				corpus["data"].append(dict(tmp))

				#update variables used during the slicing process
				lastNoteOnset = array(fgMatrix[i][5])
				lastSliceOnset = array(fgMatrix[i][5])

			# note in current slice ; updates current slice
			else:
				nbNotesInSlice = len(corpus["data"][stateNb]["notes"])
				offset = fgMatrix[i][5] - corpus["data"][stateNb]["time"][0]
				tmp = dict()
				tmp["note"] = [fgMatrix[i][3], fgMatrix[i][4], fgMatrix[i][2]]
				tmp["time"] = [offset, fgMatrix[i][6]]

				corpus["data"][stateNb]["notes"].append(tmp)

				if ((fgMatrix[i][6]+offset)>corpus["data"][stateNb]["time"][1]):
					corpus["data"][stateNb]["time"][1] = fgMatrix[i][6]+int(offset)

				lastNoteOnset = array(fgMatrix[i][5])


		# on finalise la slice courante
		globalTime = fgMatrix[i][5]
		lastSliceDuration = corpus["data"][stateNb]["time"][1]
		nbNotesInLastSlice = len(corpus["data"][stateNb]["notes"])
		for k in range(0, nbNotesInLastSlice):
			if ((corpus["data"][stateNb]["notes"][k]["time"][0]+corpus["data"][stateNb]["notes"][k]["time"][1])<=lastSliceDuration):
				if (corpus["data"][stateNb]["notes"][k]["time"][0]<0):
					corpus["data"][stateNb]["notes"][k]["note"][1] = 0
					print "setting velocity of note", k, "of state", stateNb, "to 0"
					corpus["data"][stateNb]["notes"][k]["time"][0] = int(corpus["data"][stateNb]["notes"][k]["time"][1]) + int(corpus["data"][stateNb]["notes"][k]["time"][0])
		tmpListOfPitches = tools.getPitchContent(corpus["data"], stateNb, self.legato)
		if len(tmpListOfPitches)==0:
			corpus["data"][stateNb]["slice"][0] = 140
		elif len(tmpListOfPitches)==1:
			corpus["data"][stateNb]["slice"][0] = int(tmpListOfPitches[0])
		else:
			virtualFunTmp = virfun.virfun(tmpListOfPitches, 0.293)
			corpus["data"][stateNb]["slice"][0] = int(128+virtualFunTmp%12)

		frameNbTmp = tools.ceil((fgMatrix[i][5]+self.tDelay-tRef)/self.tStep)
		if (frameNbTmp<=0):
			corpus["data"][stateNb]["extras"] = [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
		else:
			corpus["data"][stateNb]["extras"] = hCtxt[:, min(int(frameNbTmp), hCtxt.shape[1])].tolist()


		corpus["size"] = stateNb+1

		return dict(corpus)

	def readAudioFiles(self, file_paths):
		print "filepaths : ", file_paths
		all_arrays = []
		for filename in file_paths:
			picklename = "."+os.path.splitext(filename)[0]+".pickle"
			y, sr = librosa.load(filename)
			all_arrays.append((y,sr))
		return all_arrays

	def readAudioData(self, data):
		segtype = "beats"
		usebeats = True
		tau = 600.0 # range of leaky integration
		print len(data)
		for y,sr in data:
			self.hop_t = librosa.core.samples_to_time(self.hop, sr)

			'''detect beats'''
			if self.usebeats:
				tempo, beats = librosa.beat.beat_track(y)
			else:
				tempo = 120
				beats = numpy.arange(0.0, librosa.core.get_duration(y), 0.5)

			'''segmentation'''
			if self.segtype == "onsets":
				seg = librosa.onset.onset_detect(y) # in frames
			elif self.segtype == "beats":
				if usebeats:
					seg = beats # in frames
				else:
					seg = librosa.beat.beat_track(y)
			elif self.segtype == "free":
				beats = numpy.arange(0.0, librosa.core.get_duration(y), freeInt)
			else:
				print "segmentation type not recognized. Onsets used"
				seg = librosa.onset.onset_detect(y)

			'''harmonic context'''
			harm_ctxt = librosa.feature.chroma_cqt(y,hop_length=self.hop)
			harm_ctxt_li = numpy.array(harm_ctxt)
			# leaky integration ce truc est un filtrage, ca s'accelere
			for n in range(1, harm_ctxt_li.shape[1]):
				harm_ctxt_li[:, n] = (1 - self.hop_t/tau)*harm_ctxt_li[:,n-1] + self.hop_t/tau*harm_ctxt[:,n]

			#pitch = get_pitch_value(seg, harm_ctxt)

			'''analysis'''
			corpus = dict()
			corpus["name"] = "caca" # a changer
			corpus["typeID"] = 'Audio'
			corpus["type"] = 3
			corpus["size"] = 1
			corpus["data"] = []
			# creating a first state, not really used except for
			corpus["data"].append({"state": 0, "time": [0,0], "seg": [1,0], "beat":[0.0, 0.0, 0, 0], \
				"extras": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "slice":[140, 0.0], "notes":dict()})

			seg_samp = librosa.core.frames_to_samples(seg)/512
			'''seg_samp = numpy.insert(seg_samp, 0, 0)
			seg = numpy.insert(seg, 0, 0)'''

			beats = numpy.insert(beats, len(beats), librosa.core.time_to_frames(librosa.core.get_duration(y)))

			'''construction'''
			for o in range(0, len(seg_samp)-1):
				if o == len(seg_samp)-1:
					e = harm_ctxt.shape[1]
				else:
					e = seg_samp[o+1]
				tmp = dict()
				tmp["state"] = o+1
				tmp["seg"] = [1, 0]

				current_time= librosa.core.frames_to_time(seg[o]).tolist()[0]
				next_time = librosa.core.frames_to_time(seg[o+1]).tolist()[0]
				tmp["time"] = [int(current_time*1000.0), (next_time-current_time)*1000.0]

				current_beat = tools.get_beat(seg[o], beats)
				previous_beat = int(numpy.floor(current_beat))
				current_beat_t = librosa.core.frames_to_time(beats[previous_beat]).tolist()[0]
				try:
					next_beat_t = librosa.core.frames_to_time(beats[previous_beat+1]).tolist()[0]
					if current_time!=next_time:
						tmp["beat"] = [current_beat, 60.0/(next_beat_t-current_beat_t), 0, 0]
					else:
						tmp["beat"] = [current_beat, corpus["data"][o]["beat"][1], 0, 0]
				except:
					tmp["beat"] = [current_beat, corpus["data"][o]["beat"][1], 0, 0]

				tmp["extras"] = numpy.average(harm_ctxt_li[:,seg_samp[o]:e], 1).tolist()
				pitch_maxs = numpy.argmax(harm_ctxt[:,seg_samp[o]:e], axis=0)
				tmp["slice"]=[tools.most_common(pitch_maxs), 0.0]
				tmp["notes"] = dict()
				corpus["data"].append(tmp)

		return dict(corpus)

	def writeFiles(self, data, output_file):
		with open(output_file, 'wb') as fp:
			json.dump(data, fp)
		print output_file, 'file outputted.'
		return 0

# this is the harmonic Somax operation, where the segmentation is rather in beats :
class OpSomaxHarmonic(OpSomaxStandard):
	def __init__(self, file_paths, corpus_name):
		OpSomaxStandard.__init__(self, file_paths, corpus_name)
		ext = os.path.splitext(file_paths[0])
		if ext[-1]=='.mid' or ext[-1]=='.midi':
			self.readData=self.readMIDIData
		self.segtype = "beats"

	def readMIDIData(self, data):
		corpus = dict()
		fgMatrix, bgMatrix = tools.splitMatrixByChannel(data, self.fgChannels, self.bgChannels) #de-interlacing information
		corpus["name"] = self.corpus_name # a changer
		corpus["typeID"] = 'MIDI'
		corpus["type"] = 3
		corpus["size"] = 1
		corpus["data"] = []
		corpus["data"].append({"state": 0, "time": [0,0], "seg": [1,0], "beat":[0.0, 0.0, 0, 0], \
			"extras": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "slice":[140, 0.0], "notes":dict()})
		globalTime = 0
		current_phrase = 1

		fgMatrix = array(fgMatrix)
		cd = arange(floor(min(fgMatrix[:,0])), ceil(max(fgMatrix[:,0])))

		matrix = zeros((cd.size, 10))
		matrix[:,0] = cd
		matrix[:,1] = 1.0
		matrix[:,2] = 1
		matrix[:,3] = 60
		matrix[:,4] = 100

		for k in range(0, cd.size):
			beatPosTemp = matrix[k,0]
			indTmp = min(argwhere(fgMatrix[:,0]>beatPosTemp))
			if indTmp==[]:
				indTmp = fgMatrix.shape[0]
			if (indTmp>1) and (abs(fgMatrix[indTmp,0]-beatPosTemp)>abs(fgMatrix[indTmp-1, 0]-beatPosTemp)):
				indTmp-=1
			#print indTmp
			bpmTmp=fgMatrix[indTmp, 7]
			matrix[k, 5] = fgMatrix[indTmp, 5]+round((beatPosTemp-fgMatrix[indTmp, 0])*60000/bpmTmp)
			matrix[k, 6] = 1.0*round(60000.0/bpmTmp)
			matrix[k, 7] = bpmTmp
			matrix[k, 8] = 2
			matrix[k, 9] = 2

		#print matrix

		if (len(bgMatrix)!=0):
			hCtxt, tRef = tools.computePitchClassVector(bgMatrix, self.tStep)
		else:
			print("Warning: no notes in background channels. Computing harmonic context with foreground channels")
			hCtxt, tRef = tools.computePitchClassVector(fgMatrix, self.tStep)
		print("fdp")

		lastNoteOnset = -1-self.tolerance
		lastSliceOnset = lastNoteOnset
		stateNb = 0
		nbNotes = cd.size
		globalTime= 0
		tmp = dict()
		matrix  = asarray(matrix)
		for i in range(0,matrix.shape[0]): # on parcourt les notes de la matrice
			if(matrix[i][5]>lastSliceOnset+self.tolerance): # la note n'est pas consideree dans la slice courante

				if stateNb>0:
					tmpListOfPitches = tools.getPitchContent(corpus["data"], stateNb, self.legato) # on obtient l'etiquette de la slice precedente
					l = len(tmpListOfPitches)
					if l==0:
						corpus["data"][stateNb]["slice"][0] = 140 # repos
					if l==1:
						corpus["data"][stateNb]["slice"][0] = int(tmpListOfPitches[0])
					else:
						virtualfunTmp = virfun.virfun(tmpListOfPitches, 0.293)
						corpus["data"][stateNb]["slice"][0] = int(128+virtualfunTmp%12)
				if self.verbose:
					print "slice is over, finalizing it"
					for k in range(0,len(corpus["data"])):
						print corpus["data"][k]
						print ""
						print "----------------------------------------"
						print ""

				#create new state
				stateNb+=1
				tmp = dict()
				globalTime = matrix[i][5]
				tmp["state"] = int(stateNb)
				tmp["time"] = [globalTime, matrix[i][6]]
				tmp["seg"] = [bisect_left(self.file_inds, i), current_phrase]
				tmp["beat"] = [matrix[i][0], matrix[i][7], 0, 0]
				frameNbTmp = tools.ceil((matrix[i][5]+self.tDelay-tRef)/self.tStep)
				if frameNbTmp<=0:
					tmp["extras"] = [0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.]
				else:
					tmp["extras"] = hCtxt[:, min(frameNbTmp, hCtxt.shape[1]-1)].tolist()
				tmp["slice"] = [0, 0.0]
				tmp["notes"] = []
				previousSliceDuration = matrix[i][5] - lastSliceOnset
				nbNotesInPreviousSlice = len(corpus["data"][stateNb-1]["notes"])
				for k in range(0, nbNotesInPreviousSlice):
					if ((corpus["data"][stateNb-1]["notes"][k]["time"][0]+corpus["data"][stateNb-1]["notes"][k]["time"][1])\
																		<=previousSliceDuration): # note-off went off during the previous slice
						if (corpus["data"][stateNb-1]["notes"][k]["time"][0]<0):
							corpus["data"][stateNb-1]["notes"][k]["note"][1] = 0
							print "setting velocity of note", k, "of state", stateNb-1, "to 0"
							corpus["data"][stateNb-1]["notes"][k]["time"][0] = int(corpus["data"][stateNb-1]["notes"][k]["time"][1]) + int(corpus["data"][stateNb-1]["notes"][k]["time"][0])
					else: #note continues ; if still in current slice, add it to the current slice and modify the previous one
						#add it
						nbNotesInSlice = len(tmp["notes"])
						tmp["notes"].append(dict())
						tmp["notes"][nbNotesInSlice]["note"] = dict(corpus["data"][stateNb-1]["notes"][k]["note"])
						tmp["notes"][nbNotesInSlice]["time"] = dict(corpus["data"][stateNb-1]["notes"][k]["time"])
						tmp["notes"][nbNotesInSlice]["time"][0] -= previousSliceDuration

						#modify it
						corpus["data"][stateNb-1]["notes"][k]["time"][1] = 0

				#add the new note
				nbNotesInSlice = len(tmp["notes"])
				tmp["notes"].append(dict())
				tmp["notes"][nbNotesInSlice]["note"] = [matrix[i][3], matrix[i][4], matrix[i][2]]
				tmp["notes"][nbNotesInSlice]["time"] = [0, matrix[i][6]]
				corpus["data"].append(dict(tmp))

				#update variables used during the slicing process
				lastNoteOnset = matrix[i][5]
				lastSliceOnset = matrix[i][5]

			# note in current slice ; updates current slice
			else:
				nbNotesInSlice = len(corpus["data"][stateNb]["notes"])
				offset = matrix[i][5] - corpus["data"][stateNb]["time"][0]
				tmp = dict()
				tmp["note"] = [matrix[i][3], matrix[i][4], matrix[i][2]]
				tmp["time"] = [offset, matrix[i][6]]

				corpus["data"][stateNb]["notes"].append(tmp)

				if ((matrix[i][6]+offset)>corpus["data"][stateNb]["time"][1]):
					corpus["data"][stateNb]["time"][1] = matrix[i][6]+offset
				lastNoteOnset = matrix[i][5]


		# on finalise la slice courante
		globalTime = matrix[i][5]
		lastSliceDuration = float(corpus["data"][stateNb]["time"][1])
		nbNotesInLastSlice = len(corpus["data"][stateNb]["notes"])
		for k in range(0, nbNotesInLastSlice):
			if ((corpus["data"][stateNb]["notes"][k]["time"][0]+corpus["data"][stateNb]["notes"][k]["time"][1])<=lastSliceDuration):
				if (corpus["data"][stateNb]["notes"][k]["time"][0]<0):
					corpus["data"][stateNb]["notes"][k]["note"][1] = 0
					print "setting velocity of note", k, "of state", stateNb, "to 0"
					corpus["data"][stateNb]["notes"][k]["time"][0] = int(corpus["data"][stateNb]["notes"][k]["time"][1])+ int(corpus["data"][stateNb]["notes"][k]["time"][0])
		tmpListOfPitches = tools.getPitchContent(corpus["data"], stateNb, self.legato)
		if len(tmpListOfPitches)==0:
			corpus["data"][stateNb]["slice"][0] = 140
		elif len(tmpListOfPitches)==1:
			corpus["data"][stateNb]["slice"][0] = int(tmpListOfPitches[0])
		else:
			virtualFunTmp = virfun.virfun(tmpListOfPitches, 0.293)
			corpus["data"][stateNb]["slice"][0] = int(128+virtualFunTmp%12)

		frameNbTmp = tools.ceil((matrix[i][5]+self.tDelay-tRef)/self.tStep)
		if (frameNbTmp<=0):
			corpus["data"][stateNb]["extras"] = [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
		else:
			corpus["data"][stateNb]["extras"] = hCtxt[:, min(frameNbTmp, hCtxt.shape[1])].tolist()


		corpus["size"] = stateNb+1
		return dict(corpus)

# this is the melodic Somax operation, whose only difference is that the data is
# labelled with the note mod 12
class OpSomaxMelodic(OpSomaxStandard):
	def __init__(self, file_paths, corpus_name):
		OpSomaxStandard.__init__(self, file_paths, corpus_name)
		self.mod12 = True
