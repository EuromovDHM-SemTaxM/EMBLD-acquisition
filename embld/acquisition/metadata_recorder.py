import json
import logging
from pathlib import Path
import threading
from time import sleep

from embld.acquisition import TrialRecorder
from embld.experiment.utils import subject_string_trial

logger = logging.getLogger("Metadata Recorder")

def _write_metadata_and_annotations(
    metadata,
    trial_order,
    trial_id,
    trial_label,
    annotation_onsets,
    annotation_durations,
    target_path,
):
    metadata = metadata.copy()
    metadata["trial_id"] = trial_id
    metadata["trial_order"] = trial_order
    metadata["instruction"] = trial_label
    metadata["segments"] = []

    for i in range(len(annotation_onsets)):
        metadata["segments"].append(
            {
                "position": i,
                "onset": annotation_onsets[i],
                "duration": annotation_durations[i],
            }
        )
    with open(target_path, "w") as fp:
        json.dump(metadata, fp)


class MetadataRecorder(TrialRecorder):
    def start_acquisition(self):
        logger.debug("Acquistion started for trial {self.trial_number}")


    def end_acquisition(self):
        logger.debug(f"Acquistion ended for trial {self.trial_number}")
        pass

    def acquire(self, num_samples):
        while not self.next_segment:
            sleep_time = int(num_samples/self.sampling_rate)
            sleep(sleep_time)
        return []

    def coalesce_and_save(self, raws):
        subject_str = subject_string_trial(
            self.metadata, self.trial_number, self.current_trial_id
        )
        target_path_meta = Path(
            self.base_output_path, "recordings", f"{subject_str}_annotation.json"
        )
        _write_metadata_and_annotations(
            self.metadata,
            self.trial_number,
            self.current_trial_id,
            self.current_trial_label,
            self.annotation_onsets,
            self.annotation_durations,
            str(target_path_meta),
        )
        logger.info(f"Metadata saved under {str(target_path_meta)}")

    def __init__(self, metadata, trial_segments: int = 2, base_output_path=".", inst=1,  sampling_rate = 50):
        super(MetadataRecorder, self).__init__(
            metadata, trial_segments, base_output_path
        )
        self.unit = None
        self.sampling_rate = sampling_rate
        self.current_trial_label = None

    def receive_label(self, label):
        self.current_trial_label = label
