import logging
import socket
import time

import struct

from qtmrt import QTMException
from qtmrt.packets import QTMPacket, ErrorPacket, CommandPacket, EventPacket, QTMEvent


class QTMRTClient:
    def __init__(self, host: str, port: int, password: str = None):
        self.__host = host
        self.__port = port + 1
        self.__password = password
        self.__socket = None
        self.__logger = logging.getLogger("QTMRTClient")

    def connect(self):
        self.__socket = socket.create_connection((self.__host, self.__port), 2000)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)

        if self.__socket is None:
            self.__logger.error(f"Could not connect to QTM RT Server at {self.__host}:{self.__port}")
            raise QTMException(f"Could not connect to QTM RT Server at {self.__host}:{self.__port}")

        greeting = self._read_response()
        if isinstance(greeting, CommandPacket) and "QTM RT Interface connected" not in greeting.message:
            self.__logger.error(f"Error while establishing connection: {greeting}. Closing socket...")
            self.__close()
            raise QTMException(f"Error while establishing connection: {greeting}. Closing socket...")

        tk_args = []
        if self.__password is not None:
            tk_args = [self.__password]
        take_control_packet = CommandPacket("TakeControl", args=tk_args)
        self._send_packet(take_control_packet)
        response_packet = self._read_response()
        if isinstance(response_packet, ErrorPacket):
            self.__logger.error(f"Impossible to take control of QTM: {response_packet.message}. Closing socket...")
            self.__close()
            # return
            raise QTMException(f"Impossible to take control of QTM: {response_packet.message}. Closing socket...")
        else:
            self.__logger.info("Successfully taken control of QTM.")

    def _send_packet(self, packet: QTMPacket):
        payload = packet.payload
        total_sent = 0
        message_length = len(payload)
        self.__logger.debug(f"Payload: {message_length} - {payload}\n")
        while total_sent < message_length:
            sent = self.__socket.send(payload[total_sent:])
            if sent == 0:
                self.__logger.error("Send interrupted or failed! Aborting connection!")
            total_sent = total_sent + sent

    def _read_response(self) -> QTMPacket:
        payload_size = struct.unpack("<i", self.__socket.recv(4))
        payload_type = struct.unpack("<i", self.__socket.recv(4))
        string_size = payload_size[0] - 8
        if string_size > 0:
            payload = struct.unpack(f"<{string_size}s", self.__socket.recv(string_size))[0].decode("ascii")
            if payload_type[0] == 0:
                return ErrorPacket(payload)
            elif payload_type[0] == 1:
                message_parts = payload.split(" ")
                return CommandPacket(message_parts[0], message_parts[1:])
        elif payload_type[0] == 6:
            return EventPacket(QTMEvent(payload_type[0]))

    def is_connected(self):
        return self.__socket is not None

    def disconnect(self):
        if self.is_connected():
            release_control_packet = CommandPacket("ReleaseControl", args=[])
            self._send_packet(release_control_packet)
            response_packet = self._read_response()
            if isinstance(response_packet, ErrorPacket):
                self.__logger.error(f"Error while attempting to release control...")
                raise QTMException(f"Error while attempting to release control...")
            else:
                self.__logger.info("Successfully released control of QTM.")
            self.__close()

    def calibrate(self):
        pass

    def send_event(self, label) -> str:
        event_command = CommandPacket("SetQTMEvent", [label])
        self._send_packet(event_command)
        response = self._read_response()
        if isinstance(response, ErrorPacket):
            self.__logger.error(f"Error while sending event {label}...")
            raise QTMException(f"Error while sending event {label}...")
        elif "Event set" in response.message:
            self.__logger.info(f"Sent event {label}")
        return response.message

    def new_measurement(self) -> str:
        new_command = CommandPacket("New", [])
        self._send_packet(new_command)
        response = self._read_response()
        if isinstance(response, ErrorPacket):
            self.__logger.error(f"Error while starting new measurement: {response.message}...")
            raise QTMException(f"Error while starting new measurement: {response.message}...")
        elif "Event set" in response.message:
            self.__logger.info(f"Started new measurement")
        return response.message

    def close_measurement(self) -> str:
        new_command = CommandPacket("Close", [])
        self._send_packet(new_command)
        response = self._read_response()
        if isinstance(response, ErrorPacket):
            self.__logger.error(f"Error while ending measurement: {response.message}...")
            raise QTMException(f"Error while ending measurement: {response.message}...")
        elif "Closing" in response.message:
            self.__logger.info(f"Closed measurement")
        return response.message

    def start_capture(self, from_file: bool = False):
        args = []
        if from_file:
            args = ["RTFromFile"]
        start_command = CommandPacket("Start", args)
        self._send_packet(start_command)
        response = self._read_response()
        if isinstance(response, ErrorPacket):
            self.__logger.error(f"Error while starting new capture: {response.message}...")
            raise QTMException(f"Error while starting new capture: {response.message}...")
        elif "Starting" in response.message:
            self.__logger.info(f"Started capture")
        return response.message

    def stop_capture(self):
        start_command = CommandPacket("Stop", [])
        self._send_packet(start_command)
        response = self._read_response()
        if isinstance(response, ErrorPacket):
            self.__logger.error(f"Error while stopping capture: {response.message}...")
            raise QTMException(f"Error while stopping capture: {response.message}...")
        elif "Stopping " in response.message:
            self.__logger.info(f"Stopping capture")
        return response.message

    def save_capture(self, filename):
        save_command = CommandPacket("Save", [filename])
        self._send_packet(save_command)
        response = self._read_response()
        if isinstance(response, ErrorPacket):
            self.__logger.error(f"Error while saving capture : {response.message}...")
            raise QTMException(f"Error while saving capture: {response.message}...")
        elif "Stopping " in response.message:
            self.__logger.info(f"Stopping capture")
        return response.message

    def __close(self):
        self.__socket.close()
        self.__socket = None
