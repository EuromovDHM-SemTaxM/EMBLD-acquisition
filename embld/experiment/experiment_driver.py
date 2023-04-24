import json
import logging
from pathlib import Path
from random import sample
import random
import numpy as np

import simpy.rt
from PyQt5.QtCore import QObject, pyqtSignal
from tqdm import trange

from embld.configuration import APP_PARAMETERS
from embld.experiment.action_parser import generate_actions
from embld.experiment.protocol_simulation import ProtocolSimulationThread
from embld.experiment.sound_generator import SoundGenerationThread
from embld.experiment.utils import subject_string_global
from util.timer import TimerEventThread

from PyQt5.QtCore import QThread

# from scipy.stats import qmc

logger = logging.getLogger()


def _same_body_parts(action_1, action_2):
    body_parts_1 = []
    body_parts_2 = []
    if action_1["type"] == "atomic":
        if "body_parts" in action_1:
            body_parts_1.extend(action_1["body_parts"])
    else:
        if "body_parts_0" in action_1:
            body_parts_1.extend(action_1["body_parts_0"])
        if "body_parts_1" in action_1:
            body_parts_1.extend(action_1["body_parts_1"])

    if action_2["type"] == "atomic":
        if "body_parts" in action_2:
            body_parts_2.extend(action_2["body_parts"])
    else:
        if "body_parts_0" in action_2:
            body_parts_2.extend(action_2["body_parts_0"])
        if "body_parts_1" in action_2:
            body_parts_2.extend(action_2["body_parts_1"])

    body_parts_1 = set(body_parts_1)
    body_parts_2 = set(body_parts_2)
    if not body_parts_1 or not body_parts_2:
        return True
    return (body_parts_1.issubset(body_parts_2)
            or body_parts_2.issubset(body_parts_1)
            or body_parts_2 == body_parts_1)


class EMBLDAcquisitionDriver(QObject):
    sync_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.__actions = APP_PARAMETERS["actions"]
        self.__body_parts = APP_PARAMETERS["body_parts"]
        self.__directions = APP_PARAMETERS["directions"]
        self.__composition_types = APP_PARAMETERS["composition_types"]
        self.__time_factor = 0.1
        self.__sounds = {}
        self.timer_thread = None
        self.protocol = None
        self.recorder_threads = {}

    def generate_configurations(self):
        generated_actions = generate_actions()
        self.generated_configurations = []
        for i in trange(len(generated_actions)):
            for j in range(len(generated_actions)):
                a_1 = generated_actions[i]
                a_2 = generated_actions[j]
                id_1 = a_1["id"]
                id_2 = a_2["id"]
                if id_1 != id_2:
                    if (a_1["type"] == "composite"
                            and a_2["type"] != "composite"
                            and id_2 in a_1["constituents"]):
                        continue
                    elif (a_1["type"] != "composite"
                          and a_2["type"] == "composite"
                          and id_1 in a_2["constituents"]):
                        continue
                    elif a_1["type"] == "composite" and a_2[
                            "type"] == "composite":
                        continue

                    # if _same_body_parts(a_1, a_2):
                    #     continue

                    self.__actions[f"{id_1}_then_{id_2}"] = {
                        "id": f"{id_1}_then_{id_2}",
                        "type": "composite",
                        "composition_type": "successive",
                        "constituents": [id_1, id_2],
                    }
                    
        # for i in trange(len(generated_actions)):
        #     for j in range(len(generated_actions)):
        #         for k in range(len(generated_actions)):
        #             a_1 = generated_actions[i]
        #             a_2 = generated_actions[j]
        #             a_3 = generated_actions[j]
                    
        #             id_1 = a_1["id"]
        #             id_2 = a_2["id"]
        #             id_3 = a_3["id"]
        #             if id_1 != id_2 and id_2 != id_3 and id_1 != id_3:
        #                 if (a_1["type"] == "composite"
        #                         and a_2["type"] != "composite"
        #                         and id_2 in a_1["constituents"]):
        #                     continue
        #                 elif (a_1["type"] != "composite"
        #                     and a_2["type"] == "composite"
        #                     and id_1 in a_2["constituents"]):
        #                     continue
        #                 elif a_1["type"] == "composite" and a_2[
        #                         "type"] == "composite":
        #                     continue

        #                 # if _same_body_parts(a_1, a_2):
        #                 #     continue

        #                 self.__actions[f"{id_1}_then_{id_2}"] = {
        #                     "id": f"{id_1}_then_{id_2}",
        #                     "type": "composite",
        #                     "composition_type": "successive",
        #                     "constituents": [id_1, id_2],
        #                 }
        generated_actions = generate_actions()
        self.generated_configurations = [
            action for action in generated_actions
            if action["type"] == "atomic" or (
                action["type"] == "composite"
                and action["composition_type"] == "successive")
        ]

        return len(self.generated_configurations)

    def sample(self, list: list, number: int, seed):
        rng = np.random.default_rng(seed=seed)
        radius = len(list) / 3
        engine = qmc.PoissonDisc(radius=radius, dim=1, rng=rng)
        draw = engine.integers(0, len(list), n=number)
        indices = [item[0] for item in draw]
        return [list[i] for i in indices]

    def sample_configurations_ratio(self,
                                    ratio: float,
                                    seed,
                                    atomic_first=True):
        return self.sample_configurations(
            int(len(self.generated_configurations) * ratio, atomic_first), seed)

    def sample_configurations(self, number: int, seed, atomic_first=True):
        configurations = self.generated_configurations.copy()
        if atomic_first:
            atomic_configurations = [
                configuration for configuration in configurations
                if configuration["type"] == "atomic"
            ]

            simple_successive = [
                configuration for configuration in configurations
                if configuration["type"] == "composite"
                and configuration["composition_type"] == "successive"
                and APP_PARAMETERS["actions"][configuration["constituents"][0]]
                ["type"] == "atomic" and APP_PARAMETERS["actions"][
                    configuration["constituents"][1]]["type"] == "atomic"
            ]

            composite_configurations = [
                configuration for configuration in configurations
                if configuration["type"] == "composite"
                and configuration["composition_type"] == "successive" and
                ((APP_PARAMETERS["actions"][configuration["constituents"][0]]
                  ["type"] == "composite" and APP_PARAMETERS["actions"]
                  [configuration["constituents"][1]]["type"] == "composite") or
                 (APP_PARAMETERS["actions"][configuration["constituents"][0]]
                  ["type"] == "composite" and APP_PARAMETERS["actions"][
                      configuration["constituents"][1]]["type"] == "atomic") or
                 (APP_PARAMETERS["actions"][configuration["constituents"][0]]
                  ["type"] == "atomic" and APP_PARAMETERS["actions"]
                  [configuration["constituents"][1]]["type"] == "composite"))
            ]
            random.seed(seed)
            num_simple = int(
                min((number - len(atomic_configurations)) / 2,
                    len(simple_successive)))
            atomic_configurations.extend(
                sample(simple_successive, num_simple))
            num_complex = int(
                min(number - len(atomic_configurations),
                    len(composite_configurations)))
            atomic_configurations.extend(
                sample(composite_configurations, num_complex))
            return atomic_configurations
        return sample(configurations,
                      min(number, len(configurations)))

    def next_step(self):
        self.protocol.next_trial()

    def pause_until_next_step(self):
        self.protocol.wait_for_next_trial()

    def run_experiment(
        self,
        timer_slot,
        status_label_slot,
        waiting_next_slot,
        ready_for_next_slot,
        increment_segment_slot,
        metadata,
        recorders=None,
        resume = None
    ):

        if recorders is None:
            recorders = {}

        seed = hash(metadata["id"]) + hash(metadata["session"])

        env = simpy.rt.RealtimeEnvironment(factor=0.1)
        self.timer_thread = TimerEventThread()
        if len(self.generated_configurations) == 0:
            logger.info("Generating configurations...")
            self.generate_configurations()
        sample_value = APP_PARAMETERS["sample"]
        if isinstance(sample_value, float):
            configurations = self.sample_configurations_ratio(
                sample_value, seed)
        else:
            configurations = self.sample_configurations(sample_value, seed)

        self.protocol = ProtocolSimulationThread(env, configurations,
                                                 self.timer_thread, resume = resume)

        generator = SoundGenerationThread(configurations, self.protocol)
        generator.start()
        generator.wait(3000)

        base_output_path = APP_PARAMETERS["base_output_path"]
        Path(base_output_path).mkdir(exist_ok=True)

        actions_metadata_path = Path(
            Path(base_output_path),
            f"{subject_string_global(metadata)}-actions_sampled.json",
        )
        with open(actions_metadata_path, "w") as fp:
            json.dump(configurations, fp, indent=4)

        actions_metadata_path_full = Path(
            Path(base_output_path),
            f"{subject_string_global(metadata)}-actions_full.json",
        )
        with open(actions_metadata_path_full, "w") as fp:
            json.dump(self.generated_configurations, fp, indent=4)

        self.recorder_threads = {}
        for recorder_name in recorders:
            recorder = recorders[recorder_name]
            thread = QThread()
            recorder.moveToThread(thread)
            thread.started.connect(recorder.run)
            self.recorder_threads[recorder_name] = thread
            self.__connect_recorder(recorder, ready_for_next_slot)

        self.__register_metadata_connection(recorders)

        self.sync_signal.connect(increment_segment_slot)

        self.protocol.connect_stop_experiment_signal

        def protocol_ready():
            self.protocol.ready()

        self.sync_signal.connect(protocol_ready)

        self.timer_thread.connect_timer_signal(timer_slot)
        self.protocol.connect_status_label_signal(status_label_slot)

        self.protocol.connect_wait_for_next_signal(waiting_next_slot)

        logger.info("Starting protocol and timer threads...")
        self.protocol.start()
        self.timer_thread.start()
        for recorder_thread in self.recorder_threads.values():
            recorder_thread.start()

        return len(configurations)

    def __register_metadata_connection(self, recorders):
        if "metadata" in recorders:
            recorder = recorders["metadata"]

            def handle_event_label(event):
                recorder.receive_label(event)

            self.protocol.connect_status_label_signal(handle_event_label)

    def __connect_recorder(self, recorder, ready_for_next_slot):

        def handle_event(event):
            recorder.handle_protocol_events(event)

        self.protocol.connect_status_signal(handle_event)

        self.sync_signal.connect(handle_event)
        recorder.connect_ready_for_next(ready_for_next_slot)

    def emit_sync(self):
        self.sync_signal.emit("sync")

    def stop_threads(self):
        self.timer_thread.exit()
        self.protocol.exit()

    def end_experiment(self):
        self.stop_threads()

    def connect_experiment_end(self, slot):
        self.protocol.connect_stop_experiment_signal(slot)
        self.protocol.connect_stop_experiment_signal(self.end_experiment)
