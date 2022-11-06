from random import randint, shuffle

import simpy.rt
from embld.configuration import APP_PARAMETERS


class EMBLDAcquisitionDriver:
    def __init__(self):
        self.__environment = simpy.rt.RealtimeEnvironment(factor=0.001)
        self.__actions = APP_PARAMETERS['actions']
        self.__generate_configurations()

    def __generate_configurations(self):
        self.generated_configurations = []
        for k in range(len(self.__actions)):
                self.generated_configurations.append(
                    (self.__transitions[p], self.__locomotion[i], self.__modifiers[j], self.__actions[k]))

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
        TODO: Check how often we end up on impossible paths leading to an infinite loop
        """
        baseline_duration = APP_PARAMETERS['segment_duration']
        random_delay_sequence = self.__generate_random_sequence(1000, len(self.generated_configurations))
        configurations = self.generated_configurations.copy()
        current_position = (0, 0)
        generated_sequence = []
        i = 0
        while len(configurations) > 0:
            next_configuration, current_position, configurations = self.__sample_next(current_position, configurations)
            generated_sequence.append(
                (next_configuration, current_position, baseline_duration + random_delay_sequence[i]))
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
            orientation = next_configuration[0][list(next_configuration[0].keys())[0]][0]['orientation']
            # If along leftmost edge, cannot go left
            if current_position[0] == 0 and "stand" not in next_configuration[1]:
                if orientation == -90:
                    continue
            if current_position[0] == 1 and "stand" not in next_configuration[
                1]:  # If along rightmost edge, cannot go right
                if orientation == 90:
                    continue
            if current_position[1] == 0 and abs(orientation) == 180 and "stand" not in next_configuration[1]:
                # If at the beginning of the area, cannot turnaround (wall)
                continue
            if current_position[1] == 2 and (orientation == 0 or orientation == 360) and "stand" not in \
                    next_configuration[1]:
                # If at the very end of the area, cannot keep going forward (wall)
                continue

            if next_configuration[1] != "stand":
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
        pass
