import logging
import time

from PyQt5.QtCore import QThread, pyqtSignal, QMutex

logger = logging.getLogger()


def now_relative(origin_time):
    return time.monotonic() * 1000 - origin_time


def now_absolute():
    return time.monotonic() * 1000


class TimerEventThread(QThread):
    __protocol_timer = pyqtSignal(float)

    def __init__(self) -> None:
        super().__init__()
        logger.info("Initializing time thread...")
        self._mutex = QMutex()
        self._start = 0

    def run(self):
        logger.info("Starting Timer...")
        self._start = time.monotonic() * 1000
        while True:
            self.msleep(1)
            now = self.now()
            self.__protocol_timer.emit(float(now))

        self.exec_()

    def now(self):
        return time.monotonic() * 1000 - self._start

    def start_time(self):
        return self._start

    def connect_timer_signal(self, slot):
        self.__protocol_timer.connect(slot)
