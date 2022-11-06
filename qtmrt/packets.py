import logging
import struct
from abc import ABC, abstractmethod
from enum import Enum
from typing import List

from qtmrt import QTMEvent
from util.xml import dict_to_etree, XmlDictConfig


class QTMPacket(ABC):
    def __init__(self, type: int, payload: bytes):
        self._type = type
        self.payload = payload
        self._logger = logging.getLogger("Packet")


class ErrorPacket(QTMPacket):
    def __init__(self, message: str):
        frmt = f"<ii{len(message)}s"
        super().__init__(0, struct.pack(frmt, struct.calcsize(frmt), 0, message.encode("ascii")))
        self.message = message

    def __str__(self):
        return "Error Packet : " + self.message


class CommandPacket(QTMPacket):
    def __init__(self, command: str, args: List[str]):
        message = (command + " " + " ".join(args)).strip()
        frmt = f"<ii{len(message)}sB"
        super().__init__(1, struct.pack(frmt, struct.calcsize(frmt), 1, message.encode("ascii"), 0))
        self._logger.debug(message.encode("ascii"))
        self._logger.debug(f"Sent Size {struct.calcsize(frmt)}")
        self.message = message

    def __str__(self) -> str:
        return "Command - " + self.message


class XMLPacket(QTMPacket):
    def __init__(self, xml_string: str):
        frmt = f"<ii{len(xml_string)}sB"
        super().__init__(2, struct.pack(frmt, struct.calcsize(frmt), 1, xml_string.encode("ascii"), 0))
        self.message = xml_string
        self._logger.debug(xml_string.encode("ascii"))
        self._logger.debug(f"Sent Size {struct.calcsize(frmt)}")

    @staticmethod
    def create_from_dict(xml_dict):
        from lxml import etree
        xml_tree = dict_to_etree(xml_dict)
        etree.tostring(xml_tree.getroot(), xml_declaration=False)

    def as_etree(self):
        from lxml import etree
        return etree.fromstring(self.message)

    def as_dict(self):
        return XmlDictConfig(self.as_etree())


class EventPacket(QTMPacket):
    def __init__(self, event: QTMEvent):
        super().__init__(6, struct.pack("<iiB", 9, 6, event.value))
