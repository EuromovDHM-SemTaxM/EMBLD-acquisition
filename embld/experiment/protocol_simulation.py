import logging
import os
import threading

from PyQt5.QtCore import QThread, pyqtSignal, QReadWriteLock
import debugpy

# from util.playsound import playsound

logger = logging.getLogger()


def _play(path):
    os.system(f'mpg123.exe "{path}"')


class ProtocolSimulationThread(QThread):
    status_signal = pyqtSignal(str)
    status_signal_label = pyqtSignal(str)
    wait_for_next_signal = pyqtSignal()
    stop_experiment_signal = pyqtSignal()

    def __init__(self, env, steps, timer) -> None:
        super().__init__()
        self.env = env
        self.steps = steps
        self.trial_event = None
        self.ready_event = None
        self.sounds = {}
        self.timer = timer
        self.lock = QReadWriteLock()
        self.post_wait = False
        logger.debug("Protocol: Initializing protocol thread...")

    def run(self):
        logger.debug("Protocol: Creating event lock and setting it...")
        # self.wait_for_next_signal.emit()
        self.trial_event = threading.Event()
        self.ready_event = threading.Event()
        self.not_ready()
        self.next_trial()
        for step in self.steps:
            self.post_wait = False
            self.not_ready()
            self.trial_event.wait(timeout=None)
            self.wait_for_next_trial()
            logger.debug("Protocol: \tUnlocking...")
            key = (
                step["instruction"]
                .lower()
                .replace(",", "_")
                .replace(" ", "_")
                .replace(".", "")
            )
            num_segments = 1 if step["type"] == "atomic" else 2
            self.status_signal.emit(str(self.timer.now()))
            self.status_signal.emit(step["id"] + "@" + str(num_segments))
            self.status_signal_label.emit(step["instruction"])
            logger.debug(f"Protocol: Playing sound for {step['id']}")

            self.lock.lockForRead()
            beep_sound = self.sounds["beep"]
            current_sound = self.sounds[key]
            self.lock.unlock()

            _play(current_sound)

            self.ready_event.wait(timeout=None)
            logger.debug(
                f"Protocol: Resuming after sync: PW={self.post_wait} L={self.ready_event._flag}"
            )

            _play(beep_sound)
            self.wait_for_next_signal.emit()
        self.stop_experiment_signal.emit()
        self.exec_()

    def wait_for_next_trial(self):
        if self.trial_event is not None:
            self.trial_event.clear()

    def next_trial(self):
        self.post_wait = False
        self.ready()
        self.trial_event.set()

    def not_ready(self):
        if self.ready_event is not None:
            self.ready_event.clear()
        self.post_wait = True

    def ready(self):
        if not self.post_wait:
            self.ready_event.set()

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
