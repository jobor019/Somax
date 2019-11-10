from typing import TypeVar, Union, Dict

from somaxlibrary.HasMaxDict import HasMaxDict

# TODO: Poor type description
MaxCompatible = TypeVar('MaxCompatible', int, float, bool)
Ranged = Union[MaxCompatible, None]


class Parameter(HasMaxDict):

    def __init__(self, default_value: MaxCompatible, min: Ranged, max: Ranged, type_str: str, description: str):
        self.value: MaxCompatible = default_value
        self.scope: (Ranged, Ranged) = min, max
        self.type_str: str = type_str
        self.description: str = description

    def max_dict(self) -> Dict:
        return {"value": self.value,
                "range": self.scope,
                "type": self.type_str,
                "description": self.description}
