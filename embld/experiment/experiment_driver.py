from collections import defaultdict
import itertools
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


def _all_different(item) -> bool:
    return (len(item) != 2 or item[0]["id"] != item[1]["id"]) and (
        len(item) != 3
        or not item[0]["id"] == item[1]["id"] == item[2]["id"]
        and item[0]["id"] != item[1]["id"]
        and item[0]["id"] != item[2]["id"]
        and item[1]["id"] != item[2]["id"]
    )


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
    return (
        body_parts_1.issubset(body_parts_2)
        or body_parts_2.issubset(body_parts_1)
        or body_parts_2 == body_parts_1
    )


def _successive_actions_key(action_tuple):
    return "_then_".join([action["id"] for action in action_tuple])


def _max_repetitions_reached(action, repetitions, max_repetitions):
    if action["type"] == "atomic":
        return repetitions[action["id"]] >= max_repetitions
    # The code is checking if the number of repetitions of the first element in the list
    # "constituents" is greater than or equal to a certain maximum value "max_repetitions". If it is,
    # then the function returns True.
    constituents = action["constituents"]
    if repetitions[constituents[0]] >= max_repetitions:
        return True


def _update_repetitions(action, repetitions):
    if action["type"] == "atomic":
        repetitions[action["id"]] += 1
    else:
        constituents = action["constituents"]
        repetitions[constituents[0]] += 1

    return repetitions


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

    def generate_configurations(
        self, include_successions=None, symmetric_combinations=True
    ):
        if include_successions is None:
            include_successions = [2, 3]
        generated_actions = generate_actions()

        self.generated_configurations = []

        for current_succession_len in include_successions:

            if symmetric_combinations:
                prod = list(
                    itertools.combinations(generated_actions, current_succession_len)
                )
                prod.extend(reversed(prod.copy()))
            else:
                prod_input = [generated_actions for _ in range(current_succession_len)]
                prod = itertools.product(*prod_input)

            prod = [item for item in prod if _all_different(item)]
            for item in prod:
                key = _successive_actions_key(item)
                self.__actions[key] = {
                    "id": key,
                    "type": "composite",
                    "composition_type": "successive",
                    "constituents": [action["id"] for action in item],
                }

        generated_actions = generate_actions()
        self.generated_configurations = [
            action
            for action in generated_actions
            if action["type"] == "atomic"
            or (
                action["type"] == "composite"
                and action["composition_type"] == "successive"
            )
        ]

        return len(self.generated_configurations)

    def sample(self, list: list, number: int, seed):
        rng = np.random.default_rng(seed=seed)
        radius = len(list) / 3
        engine = qmc.PoissonDisc(radius=radius, dim=1, rng=rng)
        draw = engine.integers(0, len(list), n=number)
        indices = [item[0] for item in draw]
        return [list[i] for i in indices]

    def sample_configurations_ratio(
        self,
        ratio: float,
        seed,
        atomic_first=True,
        order_subset_number=1,
        exclusion_list=None,
        sampling_criteria=None,
    ):
        return self.sample_configurations(
            int(len(self.generated_configurations) * ratio, atomic_first),
            seed,
            atomic_first,
            order_subset_number,
            exclusion_list,
            sampling_criteria,
        )

    def sample_configurations(
        self,
        number: int,
        seed,
        order_subset_number=1,
        exclusion_list=None,
        sampling_criteria=None,
    ):
        random.seed(seed)

        # max_repetitions = APP_PARAMETERS["max_repetitions"]

        if exclusion_list is None:
            exclusion_list = []
        if sampling_criteria is None:
            sampling_criteria = [
                {
                    "name": "atomic_first",
                    "condition": lambda x: x["type"] == "atomic",
                    "strategy": "exhaustive",
                },
                {
                    "name": "two_successive",
                    "condition": lambda x: x["type"] == "composite"
                    and x["composition_type"] == "successive"
                    and len(x["constituents"]) == 2,
                    "strategy": "order_subset_pick",
                    "modalities": ["unique"],
                    "skip": 33,
                    "max_repetitions": 4,
                },
                {
                    "name": "three_successive",
                    "condition": lambda x: x["type"] == "composite"
                    and x["composition_type"] == "successive"
                    and len(x["constituents"]) == 3,
                    "strategy": "order_subset_pick",
                    "modalities": ["unique"],
                    "skip": 200,
                    "max_repetitions": 5,
                },
            ]
        configurations = self.generated_configurations.copy()
        configurations = [
            configuration
            for configuration in configurations
            if configuration["id"] not in exclusion_list
        ]
        sampled_configurations = []
        filtered_configurations_to_sample = {}

        filtered_configurations_to_pick_by_subset_order = []
        filtered_configurations_to_pick_by_subset_order_criteria = []
        for criterion in sampling_criteria:
            criterion_configurations = [
                configuration
                for configuration in configurations
                if criterion["condition"](configuration)
            ]
            if criterion["strategy"] == "exhaustive":
                sampled_configurations.extend(criterion_configurations)
            else:
                if "modalities" in criterion and "unique" in criterion["modalities"]:
                    unique_ids = {
                        configuration["id"]
                        for configuration in criterion_configurations
                    }
                    criterion_configurations = [
                        configuration
                        for configuration in criterion_configurations
                        if configuration["id"] in unique_ids
                    ]

                if criterion["strategy"] == "sample":
                    filtered_configurations_to_sample[
                        criterion["name"]
                    ] = criterion_configurations
                elif criterion["strategy"] == "order_subset_pick":
                    filtered_configurations_to_pick_by_subset_order.append(
                        criterion_configurations
                    )
                    filtered_configurations_to_pick_by_subset_order_criteria.append(
                        criterion
                    )

        # Sampling pick
        draws_left = number - len(sampled_configurations)
        items_left = len(filtered_configurations_to_sample)
        for filtered_configurations in filtered_configurations_to_sample.values():
            sampled = sample(filtered_configurations, int(draws_left / items_left))
            draws_left -= len(sampled)
            items_left -= 1

            sampled_configurations.extend(sampled)

        # Order subset pick
        draws_left = number - len(sampled_configurations)
        items_left = len(filtered_configurations_to_pick_by_subset_order)
        for filtered_configurations_index in range(
            len(filtered_configurations_to_pick_by_subset_order)
        ):
            repetition_dict = defaultdict(int)
            filtered_configurations = filtered_configurations_to_pick_by_subset_order[
                filtered_configurations_index
            ]
            number_of_items = int(draws_left / items_left)
            # skip = len(filtered_configurations) // number_of_items
            skip = filtered_configurations_to_pick_by_subset_order_criteria[
                filtered_configurations_index
            ]["skip"]
            max_repetitions = filtered_configurations_to_pick_by_subset_order_criteria[
                filtered_configurations_index
            ]["max_repetitions"]
            next_index = order_subset_number
            sampled = []
            while number_of_items > 0:
                sample = filtered_configurations[
                    next_index % len(filtered_configurations)
                ]

                while _max_repetitions_reached(
                    sample, repetition_dict, max_repetitions
                ):
                    next_index += 1
                    sample = filtered_configurations[
                        next_index % len(filtered_configurations)
                    ]
                repetition_dict = _update_repetitions(sample, repetition_dict)
                sampled.append(sample)
                next_index += skip
                number_of_items -= 1
            draws_left -= len(sampled)
            items_left -= 1
            sampled_configurations.extend(sampled)

        return sampled_configurations

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
        resume=None,
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
                sample_value, seed, order_subset_number=metadata["configuration"]
            )
        else:
            configurations = self.sample_configurations(
                sample_value, seed, order_subset_number=metadata["configuration"]
            )

        self.protocol = ProtocolSimulationThread(
            env, configurations, self.timer_thread, resume=resume
        )

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
