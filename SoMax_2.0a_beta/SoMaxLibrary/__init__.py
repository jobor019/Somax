from importlib import reload

import SoMaxLibrary.ActivityPatterns
import SoMaxLibrary.MemorySpaces
import SoMaxLibrary.StreamViews
import SoMaxLibrary.Tools
import SoMaxLibrary.Events
import SoMaxLibrary.SoMaxScheduler
import SoMaxLibrary.Players
import SoMaxLibrary.Transforms
import SoMaxLibrary.Atom
import SoMaxLibrary.MergeActions
import SoMaxLibrary.GenCorpus
import SoMaxLibrary.CorpusBuilder

reload(ActivityPatterns)
reload(MemorySpaces)
reload(StreamViews)
reload(Tools)
reload(Events)
reload(SoMaxScheduler)
reload(Players)
reload(Transforms)
reload(Atom)
reload(MergeActions)


TRANSFORM_TYPES = [Transforms.NoTransform, Transforms.TransposeTransform]
LABEL_TYPES = [Events.MelodicLabel, Events.HarmonicLabel]
CONTENTS_TYPES = [Events.ClassicMIDIContents, Events.ClassicAudioContents]
EVENT_TYPES = [Events.AbstractEvent]
MEMORY_TYPES = [MemorySpaces.NGramMemorySpace]

'''reload(ActivityPatterns)
reload(MemorySpaces)
reload(StreamViews)
reload(Tools)
reload(Events)
reload(SoMaxScheduler)'''
