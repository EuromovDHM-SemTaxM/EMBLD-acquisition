import logging
import struct
from abc import ABC, abstractmethod
from enum import Enum
from typing import List


class QTMPacket(ABC):
    def __init__(self, type: int, payload: bytes):
        self._type = type
        self.payload = payload
        self.__logger = logging.getLogger("Packet")

    def send(self, socket):
        self.__send(socket, self.payload)

    def __send(self, socket, msg):
        totalsent = 0
        msglen = len(msg)
        while totalsent < msglen:
            sent = socket.send(msg[totalsent:])
            if sent == 0:
                self.__logger.error("Send interrupted or failed! Aborting connection!")
            totalsent = totalsent + sent


class ErrorPacket(QTMPacket):
    def __init__(self, message: str):
        super().__init__(0, struct.pack("<iis", struct.calcsize(f"<ii{len(message)}s"), 0, message))
        self.message = message

    def __str__(self):
        return "Error Packet : " + self.message


class CommandPacket(QTMPacket):
    def __init__(self, command: str, args: List[str]):
        message = command + " " + " ".join(args)
        super().__init__(0, struct.pack("<iis", struct.calcsize(f"<ii{len(message)}s"), 0, message.encode("ascii")))
        self.message = message

    def __str__(self) -> str:
        return "Command - " + self.message


class QTMEvent(Enum):
    CONNECTED = 1,
    CONNECTION_CLOSED = 2,
    CAPTURE_STARTED = 3,
    CAPTURE_STOPPED = 4,
    NOT_USED = 5,
    CALIBRATION_STARTED = 6,
    CALIBRATION_STOPPED = 7,
    RT_FROM_FILE_STARTED = 8,
    RT_FROM_FILE_STOPPED = 9,
    WAITING_FOR_TRIGGER = 10,
    CAMERA_SETTINGS_CHANGED = 11,
    QTM_SUTTING_DOWN = 12,
    CAPTURE_SAVED = 13,
    REPROCESSING_STARTED = 14,
    REPROCESSING_STOPPED = 15,
    TRIGGER = 16


class EventPacket(QTMPacket):

    def __init__(self, event: QTMEvent):
        super().__init__(6, struct.pack("<iiB", 9, 6, event.value))
