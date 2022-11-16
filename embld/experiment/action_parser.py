import itertools
import re
from random import randint

from embld.configuration import APP_PARAMETERS

__body_parts = APP_PARAMETERS['body_parts']
__directions = APP_PARAMETERS['directions']
__composition_types = APP_PARAMETERS['composition_types']


def generate_actions():
    final_actions = []
    for action in APP_PARAMETERS['actions'].values():
        local_actions = __process_action(action)
        final_actions.extend(local_actions)
    return final_actions


def __process_action(action, mod: str = None):
    local_actions = []
    type = action['type']
    rand_modifier_param_pattern = re.compile(r"rand\((\d+),(\d+)\)")

    if type == "atomic":
        for variant in action['modifiers']:
            v_action = action.copy()
            v_action.update(variant)
            del v_action['modifiers']
            # instruction = v_action['instruction']
            instr_arguments = __extract_instruction_arguments(v_action['instruction'])
            for inst_arg in instr_arguments:
                if inst_arg == "{mod}":
                    if mod:
                        param_value = mod
                    else:
                        param_value = ""
                else:
                    arg_key = inst_arg[1:-1]
                    param_field = v_action[arg_key]
                    rand_match = None
                    if isinstance(param_field, str):
                        rand_match = rand_modifier_param_pattern.match(param_field)
                    if rand_match:
                        param_value = str(randint(int(rand_match.group(1)), int(rand_match.group(2))))
                    else:
                        if len(param_field) == 1:
                            param_value = APP_PARAMETERS[arg_key][param_field[0]]['label']
                        else:
                            param_value = \
                                ",".join([APP_PARAMETERS[arg_key][param]['label'] for param in param_field])
                v_action['instruction'] = v_action['instruction'].replace(inst_arg, param_value)
            local_actions.append(v_action)
            pass

    elif type == "composite":
        composition_type = __composition_types[action['composition_type']]
        constituents = action['constituents']
        constituents = [APP_PARAMETERS['actions'][c] for c in constituents]
        constituent_actions = []
        for ci in range(len(constituents)):
            mod = composition_type['modifiers'][ci]
            constituent_actions.append(__process_action(constituents[ci], mod))
        combinations = list(itertools.product(*constituent_actions))
        syntactic_pattern = composition_type['syntactic_pattern']
        syntactic_pattern_args = __extract_instruction_arguments(syntactic_pattern)
        for c in combinations:
            v_action = action.copy()
            v_action['instruction'] = syntactic_pattern
            for arg_index in range(len(syntactic_pattern_args)):
                v_action['instruction'] = v_action['instruction'].replace(syntactic_pattern_args[arg_index],
                                                                          c[arg_index]['instruction'])
            local_actions.append(v_action)

    return local_actions


def __extract_instruction_arguments(instruction):
    return re.findall(r"\{[^}]*\}", instruction)
