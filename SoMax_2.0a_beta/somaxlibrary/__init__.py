from importlib import reload

import somaxlibrary.ActivityPatterns
import somaxlibrary.MemorySpaces
import somaxlibrary.StreamViews
import somaxlibrary.Tools
import somaxlibrary.Events
import somaxlibrary.SoMaxScheduler
import somaxlibrary.Players
import somaxlibrary.Transforms
import somaxlibrary.Atom
import somaxlibrary.MergeActions
import somaxlibrary.GenCorpus
import somaxlibrary.CorpusBuilder
import somaxlibrary.Contents
import somaxlibrary.Corpus
import somaxlibrary.DictClasses
import somaxlibrary.Exceptions
import somaxlibrary.Labels

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
LABEL_TYPES = [Labels.MelodicLabel, Labels.HarmonicLabel]
CONTENTS_TYPES = [Contents.ClassicMIDIContents, Contents.ClassicAudioContents]
EVENT_TYPES = [Events.AbstractEvent]
MEMORY_TYPES = [MemorySpaces.NGramMemorySpace]

'''reload(ActivityPatterns)
reload(MemorySpaces)
reload(StreamViews)
reload(Tools)
reload(Events)
reload(SoMaxScheduler)'''
