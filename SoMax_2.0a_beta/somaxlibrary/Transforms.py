import logging
from abc import ABC, abstractmethod
from typing import Any


class AbstractTransform(ABC):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.precomputed_hash: int = hash(self)  # Precomputed for performance reasons

    @abstractmethod
    def __hash__(self):
        """Notes: This is mandatory to implement to enable optimized sorting of peaks by transform type.
                  The hash should contain information about class and any for the instance relevant value. """
        raise NotImplementedError("AbstractTransform.__hash__ is abstract.")

    @abstractmethod
    def __eq__(self, other):
        """Notes: Strictly not needed in current implementation, but should always be implemented when __hash__ is"""
        raise NotImplementedError("AbstractTransform.__eq__ is abstract.")

    @abstractmethod
    def encode(self, obj: Any) -> Any:
        raise NotImplementedError("AbstractTransform.encode is abstract")

    @abstractmethod
    def decode(self, obj: Any) -> Any:
        raise NotImplementedError("AbstractTransform.decode is abstract")


class NoTransform(AbstractTransform):
    def __init__(self):
        super().__init__()
        # TODO: Clean this up
        # self.admitted_types = [Events.AbstractLabel, Events.AbstractContents]  # dictionary of admitted label classes

    def __repr__(self):
        return "No Transformation"

    def __hash__(self):
        return hash(__class__)

    def __eq__(self, a):
        return type(a) == type(self)

    def encode(self, obj):
        """
        Raises
        ------
        TransformError: TODO
        """
        return obj

    def decode(self, obj):
        """
        Raises
        ------
        TransformError: TODO
        """
        return obj

    @classmethod
    def get_transformation_patterns(cls):
        return [cls()]

#
# class TransposeTransform(NoTransform):
#     transposition_range = [-3, 3]
#
#     def __init__(self, semitone: int, mod12: bool=True):
#         super(TransposeTransform, self).__init__()
#         self.semitone: int = semitone    # Number of semitones to transpose
#         self.mod12: bool = mod12
#         # self.admitted_types = [DeprecatedEvents.MelodicLabel, DeprecatedEvents.HarmonicLabel,
#         #                        DeprecatedEvents.ClassicMIDIContents,
#         #                        DeprecatedEvents.ClassicAudioContents]
#
#     def __repr__(self):
#         return "Transposition of " + str(self.semitone) + " semi-tones"
#
#     def __hash__(self):
#         return hash((__class__, self.semitone, self.mod12))
#
#     def __eq__(self, other):
#         # TODO: Potentially very slow
#         if type(other) == NoTransform:
#             return self.semitone == 0
#         if type(other) == TransposeTransform:
#             return self.semitone == other.semitone and self.mod12 == other.mod12
#         return False
#
#
#     def encode(self, obj: Union[CorpusEvent, AbstractLabel]):
#         # TODO: Note: Should handle Events and Labels. Thus needs access to chroma etc from label.
#         #       Becomes quite complex to implement new Labels if one needs to modify all existing Transforms too.
#         if isinstance(obj, DeprecatedEvents.AbstractEvent):
#             new_thing = deepcopy(obj)
#             new_thing.label = self.encode(new_thing.label)
#             new_thing.contents = self.encode(new_thing.contents)
#             return new_thing
#         if type(obj) is DeprecatedEvents.MelodicLabel:
#             new_label = deepcopy(obj)
#             new_label.label += self.semitone  # pas precis : rajouter les bornes et les accords
#             return new_label
#         elif type(obj) is DeprecatedEvents.HarmonicLabel:
#             chromas = list(obj.chroma)
#             new_label = DeprecatedEvents.HarmonicLabel(roll(obj.chroma, self.semitone))
#         elif type(obj) is DeprecatedEvents.ClassicMIDIContents:
#             new_content = deepcopy(obj)
#             for u in new_content.contents["notes"]:
#                 u["pitch"] += float(self.semitone)
#             return new_content
#         elif type(obj) is DeprecatedEvents.ClassicAudioContents:
#             new_content = deepcopy(obj)
#             new_content.transpose += float(self.semitone * 100.0)
#             return new_content
#         else:
#             raise TransformError(obj, self)
#
#     def _transform_event(self, event: CorpusEvent, semitones: int) -> CorpusEvent:
#         pass
#
#     def _transform_label(self):
#
#     def decode(self, obj):
#         if isinstance(obj, DeprecatedEvents.AbstractEvent):
#             new_thing = deepcopy(obj)
#             new_thing.label = self.decode(new_thing.label)
#             new_thing.contents = self.decode(new_thing.contents)
#             return new_thing
#         if type(obj) is DeprecatedEvents.MelodicLabel:
#             new_label = deepcopy(obj)
#             new_label.label -= self.semitone  # pas precis : rajouter les bornes et les accords
#             return new_label
#         elif type(obj) is DeprecatedEvents.HarmonicLabel:
#             chromas = list(obj.chroma)
#             new_label = DeprecatedEvents.HarmonicLabel(roll(obj.chroma, -self.semitone))
#         elif type(obj) is DeprecatedEvents.ClassicMIDIContents:
#             new_content = deepcopy(obj)
#             for u in new_content.contents["notes"]:
#                 u["pitch"] -= float(self.semitone)
#             return new_content
#         elif type(obj) is DeprecatedEvents.ClassicAudioContents:
#             new_content = deepcopy(obj)
#             new_content.transpose -= float(self.semitone * 100)
#             return new_content
#         else:
#             raise TransformError(obj, self)
#
#     @classmethod
#     def get_transformation_patterns(cls, r=None):
#         r = r if r != None else TransposeTransform.transposition_range
#         transforms = []
#         for s in range(r[0], r[1] + 1):
#             transforms.append(cls(s))
#         return transforms
#
#     @classmethod
#     def set_transformation_range(cls, minim, maxim):
#         cls.transposition_range = [minim, maxim]
#         print("[INFO] Default transposition range set to", cls.transposition_range)
