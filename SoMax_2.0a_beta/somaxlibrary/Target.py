import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict

from maxosc.MaxFormatter import MaxFormatter
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.udp_client import SimpleUDPClient


class Target(ABC):
    @abstractmethod
    def send_midi(self, content: Any, **kwargs):
        raise NotImplementedError("Target.send is abstract.")

    @abstractmethod
    def send_audio(self, content: Any, **kwargs):
        raise NotImplementedError("Target.send is abstract.")

    @abstractmethod
    def send_state(self, content: Any, **kwargs):
        raise NotImplementedError("Target.send is abstract.")

    @abstractmethod
    def send_gui(self, content: Any, **kwargs):
        raise NotImplementedError("Target.send is abstract.")


class SimpleOscTarget(Target):

    def __init__(self, address: str, port: int, ip: str = "127.0.0.1"):
        # TODO: Maybe error handling (invalid address, etc.) BUT NOT HERE.
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Creating new OscTarget with address '{address}', port '{port}' and ip '{ip}'.")
        self.address: str = address
        self._client = SimpleUDPClient(ip, port)
        self._max_formatter: MaxFormatter = MaxFormatter()

    def send_simple(self, keyword: str, content: Any, **_kwargs):
        msg_builder: OscMessageBuilder = OscMessageBuilder(self.address)
        msg_builder.add_arg(keyword)
        try:
            for item in content:
                msg_builder.add_arg(item)
        except TypeError:   # Not iterable
            msg_builder.add_arg(content)
        message = msg_builder.build()
        self._client.send(message)
        # self.logger.debug(f"[send] Sent message '{content}' with keyword '{keyword}' on address '{self.address}'")

    def send_midi(self, content: Any, **kwargs):
        self.send_simple("midi", content)

    def send_audio(self, content: Any, **kwargs):
        self.send_simple("audio", content)

    def send_state(self, content: Any, **kwargs):
        self.send_simple("state", content)

    def send_gui(self, content: Any, **kwargs):
        self._client.send_message(self.address, ["gui", self._max_formatter.format_llll(content)])

    def send_dict(self, content: Dict, **_kwargs):
        max_dict: [(str, str)] = self._max_formatter.format_maxdict_large(content)
        for address, value in max_dict:
            self.send_simple("parameter_dict", (address, str(value)))
        self.send_simple("parameter_dict", ["bang"])


class CallableTarget(Target):

    def __init__(self, callback_func: Callable):
        self.callback_func: Callable = callback_func

    def send_midi(self, content: Any, **_kwargs):
        self.callback_func(content)

    def send_audio(self, content: Any, **kwargs):
        self.callback_func(content)

    def send_state(self, content: Any, **kwargs):
        self.callback_func(content)

    def send_gui(self, content: Any, **kwargs):
        self.callback_func(content)
