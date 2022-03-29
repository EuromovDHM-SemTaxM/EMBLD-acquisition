import datetime
import glob
import queue
import time
import timeit
import typing
from random import randint, shuffle

import simpy.rt
from PyQt5.QtCore import pyqtSignal, QObject, QThread
from pyo import Server, SndTable, Osc

from embld.configuration import APP_PARAMETERS
from qtmrt.client import QTMRTClient


class TimerEventThread(QThread):

    def __init__(self, signal) -> None:
        super().__init__()
        self.signal = signal

    def run(self):
        start = time.monotonic() * 1000
        while True:
            self.msleep(1)
            now = time.monotonic() * 1000 - start
            seconds, ms = divmod(now, 1000)
            minutes, seconds = divmod(seconds, 60)
            self.signal.emit(f"{minutes:02.0f}'{seconds:02.0f}''{ms:03.0f}")

        self.exec_()


class AudioPlayer(QThread):

    def __init__(self, sound_server) -> None:
        super().__init__()
        self.sound_server = sound_server
        self.queue = queue.Queue()

    def play_audio(self, sound_table):
        self.queue.put(sound_table, block=False)

    def run(self):
        while True:
            t = self.queue.get()
            a = Osc(table=t, freq=t.getRate(), mul=1).out()
            self.sound_server.start()
            self.msleep(int(t.getDur() * 1000))
            print(int(t.getDur() * 1000))
            self.sound_server.stop()
        self.exec_()


class ProtocolSimulationThread(QThread):

    def __init__(self, env, status_signal, position_signal, steps, beep_sound, audio_player) -> None:
        super().__init__()
        self.env = env
        self.status_signal = status_signal
        self.position_signal = position_signal
        self.steps = steps
        self.audio_player = audio_player
        self.beep_sound = beep_sound

    def run(self):
        for step in self.steps:
            # configuration = step['configuration']

            duration = step['duration']
            sound_duration = step['sound_duration'] + self.beep_sound.getDur()
            print(duration, sound_duration)

            # Playing STOP beep
            self.audio_player.play_audio(self.beep_sound)
            self.status_signal.emit("STOP")

            # Playing Instructions and emitting start marker
            self.audio_player.play_audio(step['sound'])
            self.msleep(int(sound_duration * 1000))
            self.status_signal.emit(step['label'])
            self.position_signal.emit(f"{step['position'][0]}, {step['position'][1]}")
            self.msleep(int(duration))

        self.exec_()


class EMBLDAcquisitionDriver(QObject):
    protocol_event = pyqtSignal(str)
    position_event = pyqtSignal(str)
    protocol_timer = pyqtSignal(str)
    stop_experiment = pyqtSignal()

    def __init__(self, qtm_client: QTMRTClient):
        super().__init__()
        # self.__locomotion = APP_PARAMETERS['locomotion']
        self.__modifiers = APP_PARAMETERS['modifiers']
        self.__transitions = APP_PARAMETERS['transitions']
        self.__actions = APP_PARAMETERS['actions']
        self.__sound_server = Server(buffersize=1024, duplex=0, winhost="directsound").boot()
        self.__sound_server.deactivateMidi()
        self.__qtm_client = qtm_client
        self.__sounds = {}
        self.__preload_sounds()
        self.__generate_configurations()
        self.__time_factor = 0.1

    def __generate_configurations(self):
        self.generated_configurations = []
        # for i in range(len(self.__locomotion)):
        for j in range(len(self.__modifiers)):
            for p in range(len(self.__transitions)):
                for k in range(len(self.__actions)):
                    self.generated_configurations.append(
                        {'transition': self.__transitions[p], 'modifier': self.__modifiers[j],
                         'action': self.__actions[k]})

    def __preload_sounds(self):
        sound_location = APP_PARAMETERS['sound_location']
        for filename in glob.iglob(f'{sound_location}/*.wav'):
            basename = filename.split("\\")[-1].split(".")[0]
            self.__sounds[basename] = f"{filename}"

    @staticmethod
    def __generate_random_sequence(max_value, seq_len):
        sequence = []
        a = max_value
        b = a * 0.2
        m = randint(0, a - b)
        N = seq_len
        for i in range(0, int(N / 2)):
            sequence.append(m + randint(0, b))
        for i in range(int(N / 2), N):
            sequence.append(a - m - randint(0, b))

        shuffle(sequence)
        return sequence

    def sample_configurations(self):
        """
        0,0 lower left corner
        """
        baseline_duration = APP_PARAMETERS['segment_duration']
        random_delay_sequence = self.__generate_random_sequence(1000,
                                                                len(self.generated_configurations))
        configurations = self.generated_configurations.copy()
        current_position = (0, 0)
        generated_sequence = []
        i = 0
        while len(configurations) > 0:
            next_configuration, current_position, configurations = self.__sample_next(current_position,
                                                                                      configurations)
            transition = "transition_" + list(next_configuration['transition'].keys())[0].replace(" ", "_")
            # locomotion = "locomotion_" + next_configuration['locomotion'].replace(" ", "_")
            modifier = "modifier_" + next_configuration['modifier'].replace(" ", "_")
            action = "action_" + next_configuration['action'].replace(" ", "_")
            sound = SndTable()
            sound.append(self.__sounds[transition])
            # sound.append(self.__sounds[locomotion])
            if "none" not in modifier:
                sound.append(self.__sounds[modifier])
            if "none" not in action:
                sound.append(self.__sounds[action])
            sound.append(self.__sounds["beep"])

            generated_sequence.append(
                {'configuration': next_configuration, 'position': current_position,
                 'duration': baseline_duration + random_delay_sequence[i], 'sound': sound,
                 'sound_duration': sound.getDur(),
                 'label': list(next_configuration['transition'].keys())[0].replace(" ", "_") + "_" +
                          next_configuration['modifier'].replace(" ", "_") + "_" +
                          next_configuration['action'].replace(" ", "_")})
            i += 1

        return generated_sequence

    @staticmethod
    def __sample_next(current_position, remaining_configurations):
        found_valid_sample = False
        next_configuration = None
        already_drawn = []
        next_position = current_position
        while not found_valid_sample:
            r = randint(0, len(remaining_configurations) - 1)
            if r in already_drawn:
                continue
            already_drawn.append(r)
            next_configuration = remaining_configurations[r]
            orientation = next_configuration['transition'][list(next_configuration['transition'].keys())[0]][0][
                'orientation']
            # If along leftmost edge, cannot go left
            if current_position[0] == 0:
                if orientation == -90:
                    continue
            if current_position[0] == 1:  # If along rightmost edge, cannot go right
                if orientation == 90:
                    continue
            if current_position[1] == 0 and abs(orientation) == 180:
                # If at the beginning of the area, cannot turnaround (wall)
                continue
            if current_position[1] == 2 and (orientation == 0 or orientation == 360):
                # If at the very end of the area, cannot keep going forward (wall)
                continue

            if orientation == 0 or orientation == 360:
                next_position = (next_position[0], next_position[1] + 1)
            if orientation == 90:
                next_position = (next_position[0] + 1, next_position[1])
            if orientation == -90:
                next_position = (next_position[0] - 1, next_position[1])
            if abs(orientation) == 180:
                next_position = (next_position[0], next_position[1] - 1)

            found_valid_sample = True  # If no constraints invalidate the configuration, we keep it
            del remaining_configurations[r]
        return next_configuration, next_position, remaining_configurations

    def run_experiment(self):
        env = simpy.rt.RealtimeEnvironment(factor=0.1)
        timer_thread = TimerEventThread(self.protocol_timer)
        audio_player = AudioPlayer(self.__sound_server)
        audio_player.start()
        protocol = ProtocolSimulationThread(env, self.protocol_event, self.position_event, self.sample_configurations(),
                                            SndTable(self.__sounds["beep"]), audio_player)
        protocol.start()
        timer_thread.start()
