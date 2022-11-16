import logging
from random import sample

import simpy.rt
from PyQt5.QtCore import QObject
from tqdm import trange

from embld.configuration import APP_PARAMETERS
from embld.experiment.action_parser import generate_actions
from embld.experiment.simulation import ProtocolSimulationThread
from embld.experiment.sound_generator import SoundGenerationThread
from util.timer import TimerEventThread

logger = logging.getLogger()


class EMBLDAcquisitionDriver(QObject):

    def __init__(self, lsl_outlet):
        super().__init__()

        self.__actions = APP_PARAMETERS['actions']
        self.__body_parts = APP_PARAMETERS['body_parts']
        self.__directions = APP_PARAMETERS['directions']
        self.__composition_types = APP_PARAMETERS['composition_types']
        self.__time_factor = 0.1
        self.__sounds = {}
        self.timer_thread = None
        self.protocol = None
        self.lsl_outlet = lsl_outlet

    # def send_sync_event(self):
    #     self.__push_lsl_event("sync")

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
                                         action['type'] == "composite" and action['composition_type'] == "successive"]
        return len(self.generated_configurations)

    def sample_configurations(self):
        configurations = self.generated_configurations.copy()
        return sample(configurations, len(configurations))

    def next_step(self):
        self.protocol.next_segment()

    def pause_until_next_step(self):
        self.protocol.wait_for_next()

    def run_experiment(self, timer_slot, qtm_status_slot, lsl_status_slot, status_label_slot, waiting_next_slot):
        env = simpy.rt.RealtimeEnvironment(factor=0.1)
        self.timer_thread = TimerEventThread()
        if len(self.generated_configurations) == 0:
            logger.info("Generating configurations...")
            self.generate_configurations()
        configurations = self.sample_configurations()

        self.protocol = ProtocolSimulationThread(env, configurations)

        generator = SoundGenerationThread(configurations, self.protocol)
        generator.start()
        generator.wait(3000)

        if qtm_status_slot is not None:
            self.connect_protocol_status(qtm_status_slot)
        if lsl_status_slot is not None:
            def __push_lsl_event(event: str):
                lsl_status_slot.push_sample([event])

            self.connect_protocol_status(__push_lsl_event)

        self.connect_timer(timer_slot)
        self.connect_protocol_status_label(status_label_slot)
        self.connect_wait_for_next_step(waiting_next_slot)

        logger.info("Starting protocol and timer threads...")
        self.protocol.start()
        self.timer_thread.start()
        return len(configurations)

    def stop_threads(self):
        self.timer_thread.exit()
        self.protocol.exit()

    def connect_timer(self, slot):
        print(f"Connect {slot}")
        self.timer_thread.connect_timer_signal(slot)

    def connect_protocol_status_label(self, slot):
        self.protocol.connect_status_label_signal(slot)

    def connect_protocol_status(self, slot):
        self.protocol.connect_status_signal(slot)

    def connect_experiment_end(self, slot):
        self.protocol.connect_stop_experiment_signal(slot)

    def connect_wait_for_next_step(self, slot):
        self.protocol.connect_wait_for_next_signal(slot)
