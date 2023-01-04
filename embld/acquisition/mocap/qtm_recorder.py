import json
import threading
from pathlib import Path

import ezc3d
import numpy as np
from PyQt5.QtCore import QThread, QReadWriteLock, pyqtSignal
from pylsl import pylsl
from tqdm import trange

from embld.acquisition import TrialRecorder
from embld.experiment.utils import subject_string_trial
from util.timer import now_absolute


def _start_lsl_client(stream_host, stream_type, buffer_size):
    streams = pylsl.resolve_streams(wait_time=min(0.1, 10))
    ids = []
    for stream_info in streams:
        ids.append(stream_info.source_id())
        print(stream_info.as_xml())
        if stream_info.name() == stream_host and stream_info.type() == stream_type:
            break
    else:
        raise RuntimeError(f'{stream_host} not found in streams: {ids}')
    print(f'Found QTM stream {repr(stream_info.name())} via '
          f'{stream_info.source_id()}...')
    return pylsl.StreamInlet(info=stream_info,
                             max_buflen=buffer_size)


def _write_metadata_and_annotations(metadata, trial_order, trial_id, trial_label, annotation_onsets,
                                    annotation_durations, target_path):
    metadata = metadata.copy()
    metadata['trial_id'] = trial_id
    metadata['trial_order'] = trial_order
    metadata['instruction'] = trial_label
    metadata['segments'] = []

    for i in range(len(annotation_onsets)):
        metadata['segments'].append({"position": i, "onset": annotation_onsets[i], "duration": annotation_durations[i]})
    with open(target_path, "w") as fp:
        json.dump(metadata, fp)


def _extract_channels(info_structure):
    channels = []
    ch = info_structure.desc().child("setup").child("markers").child("marker")
    for k in range(info_structure.channel_count()):
        label = ch.child_value("label")
        if len(label) > 0:
            channels.append(label)
        ch = ch.next_sibling()

    return channels


def _extract_units(info_structure):
    ch = info_structure.desc().child("channels").child("channel")
    return ch.child_value("unit")


#
# class MocapRecorder(QThread):
#     read_for_next_signal = pyqtSignal()
#
#     def __init__(self, metadata, stream_host="Qualisys", stream_type="Mocap",
#                  trial_segments: int = 2,
#                  base_output_path=".", buffer_size=1000, sampling_rate=50):
#         super(MocapRecorder, self).__init__()
#         self.current_trial_label = None
#         self.ongoing_start_time = None
#         self.trial_start_event = None
#         self.terminated = False
#         self.trial_segments = trial_segments
#         self.current_trial_id = ""
#         self.annotation_onsets = []
#         self.annotation_durations = []
#         self.annotation_descriptions = []
#         self.current_segment = 1
#         self.base_output_path = Path(base_output_path)
#         self.metadata = metadata
#         self.ongoing_start_time = now_absolute()
#         self.trial_number = 1
#         self.next_segment = False
#         self.channels = None
#         self.sampling_rate = sampling_rate
#         self.client = None
#         self.stream_host = stream_host
#         self.stream_type = stream_type
#         self.buffer_size = buffer_size
#         self.unit = None
#         self.segment_completed = False
#
#         self.mutex = QReadWriteLock()
#
#     def run(self) -> None:
#         self.trial_start_event = threading.Event()
#
#         while not self.terminated:
#             self.trial_start_event.wait(timeout=None)
#             self.client = _start_lsl_client(self.stream_host, self.stream_type, self.buffer_size)
#             self.wait_for_next_trial()
#             print("Locking write mutex")
#             self.mutex.lockForWrite()
#             self.ongoing_start_time = now_absolute()
#             self.current_segment = 1
#             self.annotation_onsets.clear()
#             self.annotation_durations.clear()
#             self.annotation_descriptions.clear()
#             self.next_segment = False
#             self.channels = None
#             self.mutex.unlock()
#             print("Unlocking mutex")
#             raws = []
#             for i in trange(self.trial_segments):
#                 print("Iterating over segments")
#                 while not self.next_segment:
#                     if self.channels is None:
#                         self.channels = _extract_channels(self.client.info())
#                         self.unit = _extract_units(self.client.info())
#                     wait_time = 25 * 5. / 50
#                     samples, _ = self.client.pull_chunk(max_samples=25,
#                                                         timeout=wait_time)
#                     multiplier = 1.0
#                     if self.unit == "meters":
#                         multiplier = 1000.0
#                     data = np.vstack(samples).T
#                     x_data = data[::3].copy() * multiplier
#                     y_data = data[1::3].copy() * multiplier
#                     z_data = data[2::3].copy() * multiplier
#                     hom = np.ones(z_data.shape)
#                     data = np.moveaxis(np.stack([x_data, y_data, z_data, hom], 2), 2, 0)
#                     raws.append(data)
#                 self.mutex.lockForWrite()
#                 self.next_segment = False
#                 self.mutex.unlock()
#             self.client.close_stream()
#
#             c3d = ezc3d.c3d()
#             print("Merging raws...")
#             merged_raw = np.concatenate(raws, 2)
#             c3d['data']['points'] = merged_raw
#             c3d['parameters']['POINT']['RATE']['value'] = [self.sampling_rate]
#             c3d['parameters']['POINT']['LABELS']['value'] = tuple(self.channels)
#             c3d['parameters']['POINT']['USED']['value'] = tuple(self.channels)
#
#             subject_str = subject_string_trial(self.metadata, self.trial_number, self.current_trial_id)
#             target_path_meta = Path(self.base_output_path, subject_str + "_annotation.json")
#             _write_metadata_and_annotations(self.metadata, self.trial_number, self.current_trial_id,
#                                             self.current_trial_label, self.annotation_onsets, self.annotation_durations,
#                                             str(target_path_meta))
#             print(f"Metadata saved under {str(target_path_meta)}")
#
#             target_path_mocap = Path(self.base_output_path, subject_str + "_mocap.c3d")
#             c3d.write(str(target_path_mocap))
#
#             self.trial_number += 1
#
#     def handle_protocol_events(self, event_name: str) -> None:
#         if self.current_segment <= self.trial_segments and not self.segment_completed:
#             if event_name == "sync" and self.current_segment == 1:
#                 duration = (now_absolute() - self.ongoing_start_time) / 1000.0
#                 print(f"First segment sync o={0} d={duration}")
#                 self.mutex.lockForWrite()
#                 self.annotation_onsets.append(0)
#                 self.annotation_durations.append(duration)
#                 self.annotation_descriptions.append(event_name)
#                 self.ongoing_start_time = now_absolute()
#                 self.current_segment += 1
#                 self.next_segment = True
#                 self.mutex.unlock()
#             elif (event_name == "sync" and 1 < self.current_segment < self.trial_segments) or (
#                     event_name == "sync" and self.current_segment == self.trial_segments):
#                 onset = self.annotation_onsets[-1] + self.annotation_durations[-1]
#                 duration = (now_absolute() - self.ongoing_start_time) / 1000.0
#                 print(f"Intermediary or final sync o={onset} d={duration}")
#                 self.mutex.lockForWrite()
#                 self.annotation_onsets.append(onset)
#                 self.annotation_durations.append(duration)
#                 self.annotation_descriptions.append(event_name)
#                 self.next_segment = True
#                 if self.current_segment == self.trial_segments:
#                     print("All segments completed")
#                     self.segment_completed = True
#                     self.current_segment = 1
#                     self.read_for_next_signal.emit()
#                 else:
#                     self.current_segment += 1
#                 self.mutex.unlock()
#         if event_name != "sync" and "_" in event_name:
#             print("Initiating new segment " + event_name)
#             parts = event_name.split("@")
#             self.ongoing_start_time = now_absolute()
#             self.current_trial_id = parts[0]
#             self.trial_segments = int(parts[1])
#             self.current_segment = 1
#             self.segment_completed = False
#             self.next_trial()
#
#     def receive_label(self, label):
#         self.current_trial_label = label
#
#     def wait_for_next_trial(self):
#         if self.trial_start_event is not None:
#             self.trial_start_event.clear()
#
#     def next_trial(self):
#         self.trial_start_event.set()
#
#     def connect_ready_for_next(self, slot):
#         self.read_for_next_signal.connect(slot)


class MocapRecorder(TrialRecorder):


    def get_info(self):
        lsl_info = self.client.info()
        print(lsl_info.as_xml())

    def start_acquisition(self):
        self.client = _start_lsl_client(self.stream_host, self.stream_type, self.buffer_size)

    def end_acquisition(self):
        self.client.close_stream()

    def acquire(self, num_samples):
        raws = []
        while not self.next_segment:
            if self.channels is None:
                self.channels = _extract_channels(self.client.info())
                self.unit = _extract_units(self.client.info())
            wait_time = 25 * 5. / 50
            samples, _ = self.client.pull_chunk(max_samples=num_samples,
                                                timeout=wait_time)
            multiplier = 1.0
            if self.unit == "meters":
                multiplier = 1000.0
            data = np.vstack(samples).T
            x_data = data[::3].copy() * multiplier
            y_data = data[1::3].copy() * multiplier
            z_data = data[2::3].copy() * multiplier
            hom = np.ones(z_data.shape)
            data = np.moveaxis(np.stack([x_data, y_data, z_data, hom], 2), 2, 0)
            raws.append(data)
        return raws

    def coalesce_and_save(self, raws):
        c3d = ezc3d.c3d()
        print("Merging raws...")
        merged_raw = np.concatenate(raws, 2)
        c3d['data']['points'] = merged_raw
        c3d['parameters']['POINT']['RATE']['value'] = [self.sampling_rate]
        c3d['parameters']['POINT']['LABELS']['value'] = tuple(self.channels)
        c3d['parameters']['POINT']['USED']['value'] = tuple(self.channels)

        c3d.add_parameter("EVENT", "USED", len(self.annotation_onsets))
        c3d.add_parameter("EVENT", "LABELS", list(self.annotation_descriptions))
        c3d.add_parameter("EVENT", "TIMES", [self.sampling_rate * onset for onset in self.annotation_onsets])

        subject_str = subject_string_trial(self.metadata, self.trial_number, self.current_trial_id)
        target_path_meta = Path(self.base_output_path, subject_str + "_annotation.json")
        _write_metadata_and_annotations(self.metadata, self.trial_number, self.current_trial_id,
                                        self.current_trial_label, self.annotation_onsets, self.annotation_durations,
                                        str(target_path_meta))
        print(f"Metadata saved under {str(target_path_meta)}")

        target_path_mocap = Path(self.base_output_path, subject_str + "_mocap.c3d")
        c3d.write(str(target_path_mocap))

    def __init__(self, metadata, stream_host="Qualisys", stream_type="Mocap",
                 trial_segments: int = 2,
                 base_output_path=".", buffer_size=1000, sampling_rate=50):
        super(MocapRecorder, self).__init__(metadata, trial_segments, base_output_path)
        self.unit = None
        self.client = None
        self.stream_host = stream_host
        self.stream_type = stream_type
        self.buffer_size = buffer_size
        self.sampling_rate = sampling_rate
        self.current_trial_label = None
        self.channels = None

    def receive_label(self, label):
        self.current_trial_label = label

