import logging
import threading

from PyQt5.QtCore import QThread, pyqtSignal, QReadWriteLock
from playsound import playsound
from pydub.playback import play

logger = logging.getLogger()


class ProtocolSimulationThread(QThread):
    status_signal = pyqtSignal(str)
    status_signal_label = pyqtSignal(str)
    wait_for_next_signal = pyqtSignal()
    stop_experiment_signal = pyqtSignal()

    def __init__(self, env, steps) -> None:
        super().__init__()
        self.env = env
        self.steps = steps
        self.event = None
        self.sounds = {}
        self.lock = QReadWriteLock()
        logger.info("Initializing protocol thread...")

        # self.mutex.unlock()

    def run(self):
        logger.info("Creating event lock and setting it...")
        # self.wait_for_next_signal.emit()
        self.event = threading.Event()
        self.next_segment()
        for step in self.steps:
            self.event.wait(timeout=None)
            self.wait_for_next()
            logger.info("\tUnlocking...")
            key = step['instruction'].lower().replace(",", "_").replace(" ", "_").replace(".", "")
            self.status_signal_label.emit(step['instruction'])
            logger.info(f"Playing sound for {step['id']}")

            self.lock.lockForRead()
            beep_sound = self.sounds['beep']
            current_sound = self.sounds[key]
            self.lock.unlock()

            playsound(current_sound, block=True)
            playsound(beep_sound, block=True)

            self.status_signal.emit(step['id'])
            self.wait_for_next_signal.emit()
        self.stop_experiment_signal.emit()
        self.exec_()

    def wait_for_next(self):
        if self.event is not None:
            self.event.clear()

    def next_segment(self):
        self.event.set()

    def connect_status_signal(self, slot):
        self.status_signal.connect(slot)

    def connect_status_label_signal(self, slot):
        self.status_signal_label.connect(slot)

    def connect_wait_for_next_signal(self, slot):
        self.wait_for_next_signal.connect(slot)

    def connect_stop_experiment_signal(self, slot):
        self.stop_experiment_signal.connect(slot)

    def add_sound(self, key, value):
        self.lock.lockForWrite()
        self.sounds[key] = value
        self.lock.unlock()