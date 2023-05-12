import json
from pathlib import Path

import ezc3d
import numpy as np
from pylsl import pylsl
import pydub


from embld.acquisition import TrialRecorder
from embld.experiment.utils import subject_string_trial


def _start_lsl_client(stream_name, stream_type, buffer_size):
    streams = pylsl.resolve_streams(wait_time=min(0.1, 10))
    ids = []
    for stream_info in streams:
        ids.append(stream_info.source_id())
        print(stream_info.as_xml())
        if stream_info.name() == stream_name and stream_info.type() == stream_type:
            break
    else:
        raise RuntimeError(f"{stream_name} not found in streams: {ids}")
    print(
        f"Found Microphone stream {repr(stream_info.name())} via "
        f"{stream_info.source_id()}..."
    )
    return pylsl.StreamInlet(info=stream_info, max_buflen=buffer_size)


def _write_audio(file_handle, sampling_frequency, array, normalized=False):
    """numpy array to MP3"""
    channels = 2 if (array.ndim == 2 and array.shape[1] == 2) else 1
    y = np.int16(array * 2 ** 15) if normalized else np.int16(array)
    song = pydub.AudioSegment(
        y.tobytes(), frame_rate=sampling_frequency, sample_width=2, channels=channels
    )
    song.export(file_handle, format="mp3", bitrate="320k")


class AudioRecorder(TrialRecorder):
    def get_info(self):
        lsl_info = self.client.info()
        self.sampling_rate = lsl_info.nominal_srate()
        print(lsl_info.as_xml())

    def start_acquisition(self):
        self.client = _start_lsl_client(
            self.stream_host, self.stream_type, self.buffer_size
        )
        self.get_info()

    def end_acquisition(self):
        self.client.close_stream()

    def acquire(self, num_samples):
        raws = []
        while not self.next_segment:
            wait_time = 25 * 5.0 / 50
            samples, _ = self.client.pull_chunk(
                max_samples=num_samples, timeout=wait_time
            )
            data = np.vstack(samples).T
            # print(data)
            raws.append(data)
        return raws

    def coalesce_and_save(self, raws):
        merged_raw = np.concatenate(raws, 1).swapaxes(0, 1)
        print(merged_raw.shape)
        # sampling_rate = self.get_info().nominal_srate()
        merged_raw = np.nan_to_num(merged_raw, nan=0.0)

        subject_str = subject_string_trial(
            self.metadata, self.trial_number, self.current_trial_id
        )
        target_path_audio = Path(
            self.base_output_path, "recordings", f"{subject_str}_audio.mp3"
        )
        with open(target_path_audio, "wb") as f:
            _write_audio(f, self.sampling_rate, merged_raw, normalized=False)

    def __init__(
        self,
        metadata,
        stream_host="MicrophoneInput",
        stream_type="Audio",
        trial_segments: int = 2,
        base_output_path=".",
        buffer_size=1000,
        sampling_rate=50,
    ):
        super(AudioRecorder, self).__init__(metadata, trial_segments, base_output_path)
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
