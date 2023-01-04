import json
import logging
from pathlib import Path
from random import sample

import simpy.rt
from PyQt5.QtCore import QObject, pyqtSignal
from tqdm import trange

from embld.acquisition.fnirs.fnirs_recorder import NeuroTrialRecorder
from embld.acquisition.mocap.qtm_recorder import MocapRecorder
from embld.configuration import APP_PARAMETERS
from embld.experiment.action_parser import generate_actions
from embld.experiment.simulation import ProtocolSimulationThread
from embld.experiment.sound_generator import SoundGenerationThread
from embld.experiment.utils import subject_string_global
from util.timer import TimerEventThread

logger = logging.getLogger()


def _same_body_parts(action_1, action_2):
    body_parts_1 = []
    body_parts_2 = []
    if action_1['type'] == "atomic":
        if 'body_parts' in action_1:
            body_parts_1.extend(action_1['body_parts'])
    else:
        if "body_parts_0" in action_1:
            body_parts_1.extend(action_1["body_parts_0"])
        if "body_parts_1" in action_1:
            body_parts_1.extend(action_1["body_parts_1"])

    if action_2['type'] == "atomic":
        if 'body_parts' in action_2:
            body_parts_2.extend(action_2['body_parts'])
    else:
        if "body_parts_0" in action_2:
            body_parts_2.extend(action_2["body_parts_0"])
        if "body_parts_1" in action_2:
            body_parts_2.extend(action_2["body_parts_1"])

    body_parts_1 = set(body_parts_1)
    body_parts_2 = set(body_parts_2)
    if len(body_parts_1) == 0 or len(body_parts_2) == 0:
        return True
    return body_parts_1.issubset(body_parts_2) or body_parts_2.issubset(body_parts_1) or body_parts_2 == body_parts_1


class EMBLDAcquisitionDriver(QObject):
    sync_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.__actions = APP_PARAMETERS['actions']
        self.__body_parts = APP_PARAMETERS['body_parts']
        self.__directions = APP_PARAMETERS['directions']
        self.__composition_types = APP_PARAMETERS['composition_types']
        self.__time_factor = 0.1
        self.__sounds = {}
        self.timer_thread = None
        self.protocol = None

    def generate_configurations(self):
        generated_actions = generate_actions()
        self.generated_configurations = []
        for i in trange(len(generated_actions)):
            for j in range(len(generated_actions)):
                a_1 = generated_actions[i]
                a_2 = generated_actions[j]
                id_1 = a_1['id']
                id_2 = a_2['id']
                if id_1 != id_2:
                    if a_1['type'] == "composite" and a_2['type'] != "composite" and (a_2['id'] in a_1['constituents']):
                        continue
                    elif a_1['type'] != "composite" and a_2['type'] == "composite" and a_1['id'] in a_2['constituents']:
                        continue
                    elif a_1['type'] == "composite" and a_2['type'] == "composite":
                        continue

                    # if _same_body_parts(a_1, a_2):
                    #     continue

                    self.__actions[f"{id_1}_then_{id_2}"] = {
                        "id": f"{id_1}_then_{id_2}",
                        "type": "composite",
                        "composition_type": "successive",
                        "constituents": [
                            id_1,
                            id_2
                        ]
                    }
        generated_actions = generate_actions()
        self.generated_configurations = [action for action in generated_actions if
                                         action['type'] == "composite" and action[
                                             'composition_type'] == "successive"]

        return len(self.generated_configurations)

    def sample_configurations_ratio(self, ratio: float):
        return self.sample_configurations(int(len(self.generated_configurations) * ratio))

    def sample_configurations(self, number: int):
        configurations = self.generated_configurations.copy()
        return sample(configurations, min(number, len(configurations)))

    def next_step(self):
        self.protocol.next_trial()

    def pause_until_next_step(self):
        self.protocol.wait_for_next_trial()

    def run_experiment(self, timer_slot, status_label_slot, waiting_next_slot, ready_for_next_slot,
                       increment_segment_slot,
                       metadata):
        env = simpy.rt.RealtimeEnvironment(factor=0.1)
        self.timer_thread = TimerEventThread()
        if len(self.generated_configurations) == 0:
            logger.info("Generating configurations...")
            self.generate_configurations()
        sample_value = APP_PARAMETERS['sample']
        if isinstance(sample_value, float):
            configurations = self.sample_configurations_ratio(sample_value)
        else:
            configurations = self.sample_configurations(sample_value)

        self.protocol = ProtocolSimulationThread(env, configurations, self.timer_thread)

        generator = SoundGenerationThread(configurations, self.protocol)
        generator.start()
        generator.wait(3000)

        base_output_path = APP_PARAMETERS['base_output_path']
        Path(base_output_path).mkdir(exist_ok=True)

        actions_metadata_path = Path(Path(base_output_path), subject_string_global(metadata) + "-actions_sampled.json")
        with open(actions_metadata_path, "w") as fp:
            json.dump(configurations, fp, indent=4)

        actions_metadata_path_full = Path(Path(base_output_path),
                                          subject_string_global(metadata) + "-actions_full.json")
        with open(actions_metadata_path_full, "w") as fp:
            json.dump(self.generated_configurations, fp, indent=4)

        fnirs_recorder = NeuroTrialRecorder(trial_segments=2, base_output_path=base_output_path,
                                            metadata=metadata)
        mocap_recorder = MocapRecorder(metadata=metadata, trial_segments=2,
                                       base_output_path=base_output_path)

        def handle_fnirs_event(event):
            fnirs_recorder.handle_protocol_events(event)

        def handle_mocap_event(event):
            mocap_recorder.handle_protocol_events(event)

        def handle_mocap_label(event):
            mocap_recorder.receive_label(event)

        self.protocol.connect_status_signal(handle_fnirs_event)
        self.protocol.connect_status_signal(handle_mocap_event)

        self.sync_signal.connect(handle_fnirs_event)
        self.sync_signal.connect(handle_mocap_event)

        self.sync_signal.connect(increment_segment_slot)

        mocap_recorder.connect_ready_for_next(ready_for_next_slot)

        self.timer_thread.connect_timer_signal(timer_slot)
        self.protocol.connect_status_label_signal(status_label_slot)
        self.protocol.connect_status_label_signal(handle_mocap_label)

        self.protocol.connect_wait_for_next_signal(waiting_next_slot)

        logger.info("Starting protocol and timer threads...")
        self.protocol.start()
        self.timer_thread.start()
        fnirs_recorder.start()
        mocap_recorder.start()
        return len(configurations)

    def emit_sync(self):
        self.sync_signal.emit("sync")

    def stop_threads(self):
        self.timer_thread.exit()
        self.protocol.exit()

    # def connect_experiment_end(self, slot):
    #     self.protocol.connect_stop_experiment_signal(slot)
