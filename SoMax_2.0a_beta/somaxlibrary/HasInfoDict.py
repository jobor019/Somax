from abc import ABC, abstractmethod
from typing import Dict


class HasInfoDict(ABC):

    @abstractmethod
    def info_dict(self) -> Dict:
        raise NotImplementedError("HasMaxDict.info_dict is abstract.")
