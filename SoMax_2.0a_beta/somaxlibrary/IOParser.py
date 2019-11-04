import itertools
import logging
from typing import ClassVar, Any, Union, List

from somaxlibrary.ActivityPattern import AbstractActivityPattern, ClassicActivityPattern
from somaxlibrary.Labels import AbstractLabel, MelodicLabel
from somaxlibrary.MemorySpaces import AbstractMemorySpace, NGramMemorySpace
from somaxlibrary.MergeActions import AbstractMergeAction, PhaseModulationMergeAction, DistanceMergeAction
from somaxlibrary.Transforms import AbstractTransform, NoTransform
from somaxlibrary.scheduler.ScheduledObject import TriggerMode


class IOParser:
    DEFAULT_IP = "127.0.0.1"
    DEFAULT_ACTIVITY_TYPE: ClassVar = ClassicActivityPattern
    DEFAULT_MERGE_ACTIONS: (ClassVar, ...) = (DistanceMergeAction, PhaseModulationMergeAction)
    DEFAULT_LABEL_TYPE: ClassVar = MelodicLabel
    DEFAULT_TRANSFORMS: [(ClassVar, ...)] = [(NoTransform(),)]      # objects, not classes
    DEFAULT_TRIGGER = TriggerMode.AUTOMATIC
    DEFAULT_MEMORY_TYPE: ClassVar = NGramMemorySpace

    PARSE_DEFAULT = "default"
    PARSE_COMBINATIONS = "combinations"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # TODO: Change to nonstatic to be able to handle logging whenever needed

    def _parse_single(self, to_parse: str, parent_class: ClassVar, value_if_invalid: Any) -> ClassVar:
        if not to_parse:
            return value_if_invalid
        else:
            valid_classes: {str: ClassVar} = parent_class.classes()
            try:
                return valid_classes[to_parse]
            except KeyError:
                self.logger.warning(f"Could not parse '{parent_class}' from string '{to_parse}'. Setting to default.")
                return value_if_invalid

    def parse_merge_actions(self, merge_actions: str) -> (ClassVar[AbstractMergeAction], ...):
        if not merge_actions:
            return self.DEFAULT_MERGE_ACTIONS
        else:
            valid_merge_actions_classes: {str: ClassVar} = AbstractMergeAction.classes()
            try:
                return tuple(IOParser._parse_list_from_dict(merge_actions, valid_merge_actions_classes))
            except KeyError:
                self.logger.warning(f"Could not parse merge actions from string '{merge_actions}'. Setting to default.")
            return self.DEFAULT_MERGE_ACTIONS

    def parse_activity_type(self, activity_type: str) -> ClassVar[AbstractActivityPattern]:
        return self._parse_single(activity_type, AbstractActivityPattern, self.DEFAULT_ACTIVITY_TYPE)

    def parse_label_type(self, label_type: str) -> ClassVar[AbstractLabel]:
        return self._parse_single(label_type, AbstractLabel, self.DEFAULT_LABEL_TYPE)

    def parse_memspace_type(self, memspace: str) -> ClassVar[AbstractMemorySpace]:
        return self._parse_single(memspace, AbstractMemorySpace, self.DEFAULT_MEMORY_TYPE)

    @staticmethod
    def parse_label(label: Any) -> AbstractLabel:
        raise IOError

    def parse_trigger_mode(self, trigger_mode: str) -> TriggerMode:
        if not trigger_mode:
            return self.DEFAULT_TRIGGER
        else:
            try:
                return TriggerMode(trigger_mode.lower())
            except ValueError:
                self.logger.warning(f"Could not parse '{trigger_mode}' as a trigger mode. Setting to default.")
                return TriggerMode(self.DEFAULT_TRIGGER)

    @staticmethod
    def parse_osc_address(string: str) -> str:
        # TODO: Naive parsing
        if not string.startswith("/"):
            return f"/{string}"
        return string

    @staticmethod
    def parse_ip(ip: str) -> str:
        raise NotImplementedError("parse_ip is not implemented.")  # TODO

    def parse_transforms(self, transforms: (str, ...), parse_mode: str) -> [(ClassVar[AbstractTransform],...)]:
        """ Raises: IOError """
        # TODO: Should return OBJECTS, not classes. Needs to handle input arguments (for example pc of transpose)
        return self.DEFAULT_TRANSFORMS
        # if not parse_mode or parse_mode.lower() == self.PARSE_DEFAULT:
        #     return self._parse_transform_default(transforms)
        # elif parse_mode.lower() == self.PARSE_COMBINATIONS:
        #     all_combinations: [(str, ...)] = []
        #     for i in range(1, len(transforms) + 1):
        #         all_combinations.extend(list(itertools.combinations(transforms, r=i)))
        #     all_transforms: [(ClassVar[AbstractTransform],...)] = []
        #     for transform_tuple in all_combinations:
        #         all_transforms.append(self._parse_transform_default(transform_tuple))
        #     return all_transforms
        # else:
        #     raise IOError(f"The parse mode '{parse_mode}' is not valid.")

    def _parse_transform_default(self, transforms: (str, ...)) -> [(ClassVar[AbstractTransform],...)]:
        output_transforms: [AbstractTransform] = []
        valid_classes: {str: ClassVar} = AbstractTransform.classes()
        for transform in transforms:
            try:
                output_transforms.append(valid_classes[transform])
            except KeyError:
                raise IOError(f"A transform with the name '{transform}' does not exist.")
        return tuple(output_transforms)

    @staticmethod
    def parse_streamview_atom_path(path: str) -> [str]:
        if not path:
            return []
        elif ":" in path:
            return path.split(":")
        else:
            return [path]

    @staticmethod
    def _parse_list_from_dict(class_names: Union[str, List[str]], valid_targets: {str: ClassVar}) -> [ClassVar]:
        """" Raises: KeyError """
        if type(class_names) is list:
            results: [ClassVar] = []
            for class_name in class_names:
                try:
                    results.append(valid_targets[class_name])
                except KeyError:
                    continue
            if not results:
                raise KeyError(f"No matches for content '{class_names}'.")
            else:
                return results

        elif isinstance(class_names, str):
            return [valid_targets[class_names]]