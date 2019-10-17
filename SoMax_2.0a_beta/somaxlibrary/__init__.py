from importlib import reload

import somaxlibrary.MemorySpaces
import somaxlibrary.StreamView
import somaxlibrary.Tools
import somaxlibrary.DeprecatedEvents
import somaxlibrary.SoMaxScheduler
import somaxlibrary.Player
import somaxlibrary.Transforms
import somaxlibrary.Atom
import somaxlibrary.MergeActions
import somaxlibrary.GenCorpus
import somaxlibrary.CorpusBuilder
import somaxlibrary.DeprecatedContents
import somaxlibrary.Corpus
import somaxlibrary.DictClasses
import somaxlibrary.Exceptions
import somaxlibrary.DeprecatedLabels

reload(MemorySpaces)
reload(StreamView)
reload(Tools)
reload(DeprecatedEvents)
reload(SoMaxScheduler)
reload(Player)
reload(Transforms)
reload(Atom)
reload(MergeActions)


TRANSFORM_TYPES = [Transforms.NoTransform, Transforms.TransposeTransform]
LABEL_TYPES = [DeprecatedLabels.MelodicLabel, DeprecatedLabels.HarmonicLabel]
CONTENTS_TYPES = [DeprecatedContents.ClassicMIDIContents, DeprecatedContents.ClassicAudioContents]
EVENT_TYPES = [DeprecatedEvents.AbstractEvent]
MEMORY_TYPES = [MemorySpaces.NGramMemorySpace]

'''reload(ActivityPatterns)
reload(MemorySpaces)
reload(StreamViews)
reload(Tools)
reload(Events)
reload(SoMaxScheduler)'''
