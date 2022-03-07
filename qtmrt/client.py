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

        greeting = str(self.__recv_timeout(2000), 'ascii')
        if "QTM RT Interface connected" not in greeting:
            self.__logger.error(f"Error while establishing connection: {greeting}. Closing socket...")
            self.__close()
            raise QTMException(f"Error while establishing connection: {greeting}. Closing socket...")

        tk_args = []
        if self.__password is not None:
            tk_args = [self.__password]
        take_control_packet = CommandPacket("TakeControl", args=tk_args)
        take_control_packet.send(self.__socket)
        response_packet = self._read_response()
        if isinstance(response_packet, ErrorPacket):
            self.__logger.error(f"Impossible to take control of QTM: {response_packet.message}. Closing socket...")
            self.__close()
            raise QTMException(f"Impossible to take control of QTM: {response_packet.message}. Closing socket...")
        else:
            self.__logger.info("Successfully taken control of QTM.")

    @staticmethod
    def __parse_packet(bytes) -> QTMPacket:
        packet = struct.unpack("<iis", bytes)
        if packet[1] == 0:
            return ErrorPacket(packet[2])
        elif packet[1] == 1:
            message_parts = packet[2].split(" ")
            return CommandPacket(message_parts[0], message_parts[1:])
        elif packet[1] == 6:
            return EventPacket(QTMEvent(packet[2]))

    def _read_response(self) -> QTMPacket:
        buffer = self.__recv_timeout()
        return self.__parse_packet(buffer)

    def is_connected(self):
        return self.__socket is not None

    def disconnect(self):
        release_control_packet = CommandPacket("ReleaseControl", args=[])
        release_control_packet.send(self.__socket)
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
        response = event_command.send(self.__socket)
        if isinstance(response, ErrorPacket):
            self.__logger.error(f"Error while sending event {label}...")
            raise QTMException(f"Error while sending event {label}...")
        elif "Event set" in response.message:
            self.__logger.info(f"Sent event {label}")
        return response.message

    def new_measurement(self) -> str:
        new_command = CommandPacket("New", [])
        response = new_command.send(self.__socket)
        if isinstance(response, ErrorPacket):
            self.__logger.error(f"Error while starting new measurement: {response.message}...")
            raise QTMException(f"Error while starting new measurement: {response.message}...")
        elif "Event set" in response.message:
            self.__logger.info(f"Started new measurement")
        return response.message

    def close_measurement(self) -> str:
        new_command = CommandPacket("Close", [])
        response = new_command.send(self.__socket)
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
        response = start_command.send(self.__socket)
        if isinstance(response, ErrorPacket):
            self.__logger.error(f"Error while starting new capture: {response.message}...")
            raise QTMException(f"Error while starting new capture: {response.message}...")
        elif "Starting" in response.message:
            self.__logger.info(f"Started capture")
        return response.message

    def stop_capture(self):
        start_command = CommandPacket("Stop", [])
        response = start_command.send(self.__socket)
        if isinstance(response, ErrorPacket):
            self.__logger.error(f"Error while stopping capture: {response.message}...")
            raise QTMException(f"Error while stopping capture: {response.message}...")
        elif "Stopping " in response.message:
            self.__logger.info(f"Stopping capture")
        return response.message

    def save_capture(self, filename):
        pass

    def __close(self):
        self.__socket.close()
        self.__socket = None

    def __recv_timeout(self, timeout=2):
        # make socket non blocking
        self.__socket.setblocking(0)

        # total data partwise in an array
        total_data = []
        data = ''

        # beginning time
        begin = time.time()
        while 1:
            # if you got some data, then break after timeout
            if total_data and time.time() - begin > timeout:
                break

            # if you got no data at all, wait a little longer, twice the timeout
            elif time.time() - begin > timeout * 2:
                break

            # recv something
            try:
                data = self.__socket.recv(8192)
                if data:
                    total_data.append(data)
                    # change the beginning time for measurement
                    begin = time.time()
                else:
                    # sleep for sometime to indicate a gap
                    time.sleep(0.1)
            except:
                pass

        # join all parts to make final string
        return b''.join(total_data)
