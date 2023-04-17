import json
from pathlib import Path

import ezc3d
import numpy as np
from pylsl import pylsl

from embld.acquisition import TrialRecorder
from embld.experiment.utils import subject_string_trial


def _start_lsl_client(stream_host, stream_type, buffer_size):
    streams = pylsl.resolve_streams(wait_time=min(0.1, 10))
    ids = []
    for stream_info in streams:
        ids.append(stream_info.source_id())
        print(stream_info.as_xml())
        if stream_info.name() == stream_host and stream_info.type() == stream_type:
            break
    else:
        raise RuntimeError(f"{stream_host} not found in streams: {ids}")
    print(
        f"Found QTM stream {repr(stream_info.name())} via "
        f"{stream_info.source_id()}..."
    )
    return pylsl.StreamInlet(info=stream_info, max_buflen=buffer_size)

def _extract_channels(info_structure):
    channels = []
    ch = info_structure.desc().child("setup").child("markers").child("marker")
    for _ in range(info_structure.channel_count()):
        label = ch.child_value("label")
        if len(label) > 0:
            channels.append(label)
        ch = ch.next_sibling()

    return channels


def _extract_units(info_structure):
    ch = info_structure.desc().child("channels").child("channel")
    return ch.child_value("unit")


class QTMMocapRecorder(TrialRecorder):
    def get_info(self):
        lsl_info = self.client.info()
        print(lsl_info.as_xml())

    def start_acquisition(self):
        self.client = _start_lsl_client(
            self.stream_host, self.stream_type, self.buffer_size
        )

    def end_acquisition(self):
        self.client.close_stream()

    def acquire(self, num_samples):
        raws = []
        while not self.next_segment:
            if self.channels is None:
                self.channels = _extract_channels(self.client.info())
                self.unit = _extract_units(self.client.info())
            wait_time = 25 * 5.0 / 50
            samples, _ = self.client.pull_chunk(
                max_samples=num_samples, timeout=wait_time
            )
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
        c3d["data"]["points"] = merged_raw
        c3d["parameters"]["POINT"]["RATE"]["value"] = [self.sampling_rate]
        c3d["parameters"]["POINT"]["LABELS"]["value"] = tuple(self.channels)
        c3d["parameters"]["POINT"]["USED"]["value"] = tuple(self.channels)

        c3d.add_parameter("EVENT", "USED", len(self.annotation_onsets))
        c3d.add_parameter("EVENT", "LABELS", list(self.annotation_descriptions))
        c3d.add_parameter("EVENT", "TIMES", list(self.annotation_onsets))

        subject_str = subject_string_trial(
            self.metadata, self.trial_number, self.current_trial_id
        )
        target_path_mocap = Path(self.base_output_path,"recordings", f"{subject_str}_mocap.c3d")
        c3d.write(str(target_path_mocap))

    def __init__(
        self,
        metadata,
        stream_host="Qualisys",
        stream_type="Mocap",
        trial_segments: int = 2,
        base_output_path=".",
        buffer_size=1000,
        sampling_rate=50,
    ):
        super(QTMMocapRecorder, self).__init__(
            metadata, trial_segments, base_output_path
        )
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
