import logging

from PyQt5.QtCore import QThread, pyqtSignal
import time

logger = logging.getLogger()

class TimerEventThread(QThread):
    __protocol_timer = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        logger.info("Initializing time thread...")

    def run(self):
        logger.info("Starting Timer...")
        start = time.monotonic() * 1000
        while True:
            self.msleep(1)
            now = time.monotonic() * 1000 - start
            seconds, ms = divmod(now, 1000)
            minutes, seconds = divmod(seconds, 60)
            self.__protocol_timer.emit(f"{minutes:02.0f}'{seconds:02.0f}''{ms:03.0f}")

        self.exec_()

    def connect_timer_signal(self, slot):
        self.__protocol_timer.connect(slot)
