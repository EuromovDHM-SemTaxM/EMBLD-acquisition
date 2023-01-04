import threading
from abc import abstractmethod, ABC
from pathlib import Path

from PyQt5.QtCore import QThread, QReadWriteLock, pyqtSignal
from tqdm import trange

from util.timer import now_absolute


class TrialRecorder(QThread):
    ready_for_next_signal = pyqtSignal()

    def __init__(self, metadata,
                 trial_segments: int = 2,
                 base_output_path="."):
        super(TrialRecorder, self).__init__()
        self.ongoing_start_time = None
        self.trial_start_event = None
        self.terminated = False
        self.trial_segments = trial_segments
        self.current_trial_id = ""
        self.annotation_onsets = []
        self.annotation_durations = []
        self.annotation_descriptions = []
        self.current_segment = 1
        self.base_output_path = Path(base_output_path)
        self.metadata = metadata
        self.ongoing_start_time = now_absolute()
        self.trial_number = 1
        self.next_segment = False
        self.mutex = QReadWriteLock()
        self.segment_completed = False

    @abstractmethod
    def start_acquisition(self):
        pass

    @abstractmethod
    def end_acquisition(self):
        pass

    @abstractmethod
    def acquire(self, num_samples):
        pass

    @abstractmethod
    def coalesce_and_save(self, raws):
        pass

    def run(self) -> None:
        self.trial_start_event = threading.Event()
        while not self.terminated:
            self.trial_start_event.wait(timeout=None)
            self.start_acquisition()
            self.wait_for_next_trial()
            print("Locking write mutex")
            self.mutex.lockForWrite()
            self.ongoing_start_time = now_absolute()
            self.current_segment = 1
            self.annotation_onsets.clear()
            self.annotation_durations.clear()
            self.annotation_descriptions.clear()
            self.next_segment = False
            self.mutex.unlock()
            print("Unlocking mutex")
            raws = []
            for i in trange(self.trial_segments):
                print("Iterating over segments")
                raws.extend(self.acquire(25))
                self.mutex.lockForWrite()
                self.next_segment = False
                self.mutex.unlock()
            self.end_acquisition()

            self.coalesce_and_save(raws)
            self.trial_number += 1

    def handle_protocol_events(self, event_name: str) -> None:
        if self.current_segment <= self.trial_segments and not self.segment_completed:
            if event_name == "sync":
                if self.current_segment == 1:
                    duration = (now_absolute() - self.ongoing_start_time) / 1000.0
                    onset = 0
                    print(f"First segment sync o={0} d={duration}")

                elif (1 < self.current_segment < self.trial_segments) or self.current_segment == self.trial_segments:
                    onset = self.annotation_onsets[-1] + self.annotation_durations[-1]
                    duration = (now_absolute() - self.ongoing_start_time) / 1000.0
                    print(f"Intermediary or final sync o={onset} d={duration}")

                self.mutex.lockForWrite()
                self.annotation_onsets.append(onset)
                self.annotation_durations.append(duration)
                self.annotation_descriptions.append(event_name)
                self.ongoing_start_time = now_absolute()

                self.next_segment = True
                self.mutex.unlock()
                if self.current_segment == self.trial_segments:
                    self.segment_completed = True
                    # self.wait_for_next_trial()
                    self.ready_for_next_signal.emit()
                else:
                    self.current_segment += 1
                self.mutex.unlock()
        if event_name != "sync" and "_" in event_name:
            print("Initiating new segment " + event_name)
            parts = event_name.split("@")
            self.ongoing_start_time = now_absolute()
            self.current_trial_id = parts[0]
            self.trial_segments = int(parts[1])
            self.current_segment = 1
            self.segment_completed = False
            self.next_trial()

    def wait_for_next_trial(self):
        if self.trial_start_event is not None:
            self.trial_start_event.clear()

    def next_trial(self):
        self.trial_start_event.set()

    def connect_ready_for_next(self, slot):
        self.ready_for_next_signal.connect(slot)

