import inspect
import sys
from typing import Tuple, ClassVar, Any, Union, List

from somaxlibrary.ActivityPatterns import AbstractActivityPattern
from somaxlibrary.Labels import AbstractLabel
from somaxlibrary.MemorySpaces import AbstractMemorySpace
from somaxlibrary.MergeActions import AbstractMergeAction
from somaxlibrary.Transforms import AbstractTransform


class IOParser:

    @staticmethod
    def parse_merge_actions(merge_actions_str: Union[str, List[str]]) -> (ClassVar[AbstractMergeAction], ...):
        valid_merge_actions: {str: ClassVar} = AbstractMergeAction.classes()
        return tuple(IOParser._parse_from_dict(merge_actions_str, valid_merge_actions))

    @staticmethod
    def parse_activity_type(activity_type: str) -> ClassVar[AbstractActivityPattern]:
        raise IOError

    @staticmethod
    def parse_label_type(label_type: str) -> ClassVar[AbstractLabel]:
        raise IOError

    @staticmethod
    def parse_label(label: Any) -> AbstractLabel:
        raise IOError

    @staticmethod
    def parse_memspace_type(memspace: str) -> AbstractMemorySpace:
        raise IOError

    @staticmethod
    def parse_transforms(transforms: str) -> Tuple[AbstractTransform]:
        raise IOError

    @staticmethod
    def parse_streamview_atom_path(path: str) -> [str]:
        if ":" in path:
            return path.split(":")
        else:
            return [path]

    @staticmethod
    def _parse_from_dict(class_names: Union[str, List[str]], valid_targets: {str: ClassVar}):
        if type(class_names) is list:
            results: [ClassVar] = []
            for class_name in class_names:
                try:
                    results.append(valid_targets[class_name])
                except KeyError:
                    continue
            return results
        elif isinstance(class_names, str):
            try:
                return valid_targets[class_names]
            except KeyError:
                return []



