from pathlib import Path

from mne import Annotations, concatenate_raws
from mne.io import Raw
from mne_realtime import LSLClient

from embld.acquisition import TrialRecorder
from embld.experiment.utils import subject_string_trial


def _add_annotations_to_raw(
    raw: Raw, annotation_onsets, annotation_durations, annotation_descriptions
):
    annotations = Annotations(
        annotation_onsets, annotation_durations, annotation_descriptions
    )
    raw.set_annotations(annotations)
    return raw


class ArtinisFNIRSRecorder(TrialRecorder):
    def start_acquisition(self):
        self.lsl_client.start()

    def end_acquisition(self):
        self.lsl_client.stop()

    def acquire(self, num_samples):
        raws = []
        while not self.next_segment:
            raws.append(self.lsl_client.get_data_as_raw(25))
        return raws

    def coalesce_and_save(self, raws):
        print("Merging raws...")
        merged_raw = concatenate_raws(raws)  # type: Raw
        _add_annotations_to_raw(
            merged_raw,
            self.annotation_onsets,
            self.annotation_durations,
            self.annotation_descriptions,
        )
        subject_str = subject_string_trial(
            self.metadata, self.trial_number, self.current_trial_id
        )
        target_path = Path(self.base_output_path, f"{subject_str}-raw.fif")
        merged_raw.save(str(target_path))
        print(f"Signals saved under {str(target_path)}")

    def __init__(
        self,
        metadata,
        stream_host="OxySoft",
        stream_type="NIRS",
        trial_segments: int = 2,
        base_output_path=".",
    ):
        super(ArtinisFNIRSRecorder, self).__init__(
            metadata, trial_segments, base_output_path
        )
        self.lsl_client = LSLClient(
            host=stream_host, stream_type=stream_type, buffer_size=0
        )
