from importlib import reload

# TODO: Update with to current classes
import somaxlibrary.MemorySpaces
import somaxlibrary.StreamView
import somaxlibrary.Tools
import somaxlibrary.Player
import somaxlibrary.Transforms
import somaxlibrary.Atom
import somaxlibrary.MergeActions
import somaxlibrary.GenCorpus
import somaxlibrary.CorpusBuilder
import somaxlibrary.Corpus
import somaxlibrary.Exceptions

reload(MemorySpaces)
reload(StreamView)
reload(Tools)
reload(Player)
reload(Transforms)
reload(Atom)
reload(MergeActions)

# TODO: Remove this or parse from get_classes
# TRANSFORM_TYPES = [Transforms.NoTransform, Transforms.TransposeTransform]
# LABEL_TYPES = [Label.MelodicLabel, DeprecatedLabels.HarmonicLabel]
# CONTENTS_TYPES = [DeprecatedContents.ClassicMIDIContents, DeprecatedContents.ClassicAudioContents]
# EVENT_TYPES = [DeprecatedEvents.AbstractEvent]
# MEMORY_TYPES = [MemorySpaces.NGramMemorySpace]

'''reload(ActivityPatterns)
reload(MemorySpaces)
reload(StreamViews)
reload(Tools)
reload(Events)
reload(SoMaxScheduler)'''
