from abc import ABC, abstractmethod
from typing import Dict


class HasMaxDict(ABC):

    @abstractmethod
    def max_dict(self) -> Dict:
        raise NotImplementedError("HasMaxDict.max_dict is abstract.")
