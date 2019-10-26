from abc import ABC, abstractmethod
from typing import Any, Callable

from pythonosc.udp_client import SimpleUDPClient

from somaxlibrary.MaxOscLib import MaxFormatter


class Target(ABC):
    @abstractmethod
    def send(self, content: Any, **kwargs):
        raise NotImplementedError("Target.send is abstract.")


class OscTarget(Target):

    def __init__(self, address: str, port: int, ip: str = "127.0.0.1"):
        # TODO: Maybe error handling (invalid address, etc.
        self.address: str = address
        self._client = SimpleUDPClient(ip, port)
        self._max_formatter: MaxFormatter = MaxFormatter()

    def send(self, content: Any, **_kwargs):
        msg: str = self._max_formatter.format_llll(*content)    # TODO: llll probably not ideal
        self._client.send_message(self.address, msg)


class CallableTarget(Target):

    def __init__(self, callback_func: Callable):
        self.callback_func: Callable = callback_func

    def send(self, content: Any, **_kwargs):
        self.callback_func(content)
