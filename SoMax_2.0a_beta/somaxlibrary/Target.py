import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

from pythonosc.udp_client import SimpleUDPClient

from maxosc.MaxFormatter import MaxFormatter


class Target(ABC):
    @abstractmethod
    def send(self, content: Any, **kwargs):
        raise NotImplementedError("Target.send is abstract.")


class OscTarget(Target):

    def __init__(self, address: str, port: int, ip: str = "127.0.0.1"):
        # TODO: Maybe error handling (invalid address, etc.) BUT NOT HERE.
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Creating new OscTarget with address '{address}', port '{port}' and ip '{ip}'.")
        self.address: str = address
        self._client = SimpleUDPClient(ip, port)
        self._max_formatter: MaxFormatter = MaxFormatter()

    def send(self, content: Any, **_kwargs):
        self.logger.debug(f"[send] Sending Message '{content}'")
        self._client.send_message(self.address, content)


class CallableTarget(Target):

    def __init__(self, callback_func: Callable):
        self.callback_func: Callable = callback_func

    def send(self, content: Any, **_kwargs):
        self.callback_func(content)
