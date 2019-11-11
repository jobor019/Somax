import collections
import functools
from abc import ABC, abstractmethod
from typing import TypeVar, Union, Dict, Any

# TODO: Poor type description
MaxCompatible = TypeVar('MaxCompatible', int, float, bool)
Ranged = Union[MaxCompatible, None]


class HasParameterDict(ABC):

    def __init__(self):
        self.parameter_dict: Dict[str, Union[Parametric, Parameter, Dict]] = {}

    # @abstractmethod
    # def update_parameter_dict(self) -> Dict[str, Union['Parametric', 'Parameter', Dict]]:
    #     """ Update and return parameter dict """
    #     raise NotImplementedError("HasParameterDict.update_parameter_dict is abstract.")


class Parameter(HasParameterDict):

    def __init__(self, default_value: MaxCompatible, min: Ranged, max: Ranged, type_str: str, description: str):
        super(Parameter, self).__init__()
        self.value: MaxCompatible = default_value
        self.scope: (Ranged, Ranged) = (min, max)
        self.type_str: str = type_str
        self.description: str = description

    def max_representation(self) -> Dict:
        return vars(self)

    # def update_parameter_dict(self) -> Dict[str, str]:
    #     return {"value": self.value,
    #             "range": str(self.scope),
    #             "type": self.type_str,
    #             "description": self.description}

    def set_value(self, value):
        # TODO: Check range
        self.value = value

    def _parse_parameters(self):
        # Base case: TODO: remove this
        return




class Parametric(HasParameterDict):

    def __init__(self):
        """ Parameter dict is a dict of dicts (of dicts of ...). Note: only dicts (no lists).
            It should be updated using parameter_dict() whenever parameter info is changed
            (for example, upon creating a streamview, adding a mergeaction or deleting an atom) """
        super(Parametric, self).__init__()
        self.parameter_dict: Dict[str, Union[Parametric, Parameter]] = {}

    def max_representation(self) -> Dict:
        d = {}
        for name, param in self.parameter_dict.items():
            d[name] = param.max_representation()
        return d

    def set_param(self, path: [str], value: Any):
        """ raises IndexError: if path spec is invalid, for example empty list,
                   ParameterError: if path spec is invalid or if trying to set an object that is not a Parameter.
        """
        param: Parameter = self.get_param(path)
        param.set_value(value)
        self.logger.debug(f"Parameter {param} set to {value}.")

    def get_param(self, param_path: [str]) -> Parameter:
        """ raises KeyError """
        param_name: str = param_path.pop(-1)
        parent_dict: Dict[str, Union[Parametric, Parameter]] = functools.reduce(lambda d, key: d[key].parameter_dict,
                                                                                param_path, self.parameter_dict)
        return parent_dict[param_name]

    def _parse_parameters(self) -> {str: Parameter}:
        self.parameter_dict = {}
        param_dict: {str: Union[Parameter, Parametric]} = {}
        for name, variable in vars(self).items():
            # Parse all Parameter and Parametric into dict
            if isinstance(variable, Parameter) or isinstance(variable, Parametric):
                variable._parse_parameters()
                param_dict[name] = variable
            # Parse all Parameter and Parametric inside other dicts (for example MergeAction)
            if isinstance(variable, collections.abc.Mapping):
                for name, item in variable.items():
                    if isinstance(item, Parameter) or isinstance(item, Parametric):
                        item._parse_parameters()
                        param_dict[name] = item
        self.parameter_dict = param_dict
