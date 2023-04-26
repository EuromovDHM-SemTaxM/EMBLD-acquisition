import itertools
import re
from random import randint

from embld.configuration import APP_PARAMETERS

__composition_types = APP_PARAMETERS["composition_types"]


def generate_actions():
    action_lists = []
    left_for_action = []
    total_left = 0
    for action in APP_PARAMETERS["actions"].values():
        local_actions = _process_action(action)
        action_lists.append(local_actions)
        left_for_action.append(len(local_actions))
        total_left += len(local_actions)

    final_actions = []
    while total_left > 0:
        for i in range(len(action_lists)):
            if left_for_action[i] > 0:
                final_actions.append(
                    action_lists[i][len(action_lists[i]) - left_for_action[i]]
                )
                left_for_action[i] -= 1
                total_left -= 1
    return final_actions


def _process_atomic_action(action, mod: str = None):
    local_actions = []
    rand_modifier_param_pattern = re.compile(r"rand\((\d+),(\d+)\)")
    if "modifiers" in action:
        for variant in action["modifiers"]:
            v_action = action.copy()
            v_action.update(variant)
            del v_action["modifiers"]
            # instruction = v_action['instruction']
            instr_arguments = __extract_instruction_arguments(v_action["instruction"])
            for inst_arg in instr_arguments:
                if inst_arg == "{mod}":
                    param_value = mod or ""
                else:
                    arg_key = inst_arg[1:-1]
                    param_field = v_action[arg_key]
                    rand_match = None
                    if isinstance(param_field, str):
                        rand_match = rand_modifier_param_pattern.match(param_field)
                    if rand_match:
                        param_value = str(
                            randint(int(rand_match.group(1)), int(rand_match.group(2)))
                        )
                    elif len(param_field) == 1:
                        param_value = APP_PARAMETERS[arg_key][param_field[0]]["label"]
                    else:
                        param_value = ",".join(
                            [
                                APP_PARAMETERS[arg_key][param]["label"]
                                for param in param_field
                            ]
                        )
                v_action["instruction"] = v_action["instruction"].replace(
                    inst_arg, param_value
                )
            local_actions.append(v_action)
    else:
        local_actions.append(action)
    return local_actions


def _process_composite_action(action):
    local_actions = []
    composition_type = __composition_types[action["composition_type"]]
    constituents = action["constituents"]
    constituents = [APP_PARAMETERS["actions"][c] for c in constituents]
    constituent_actions = []
    for ci in range(len(constituents)):
        mod = composition_type["modifiers"][ci]
        constituent_actions.append(_process_action(constituents[ci], mod))
    combinations = list(itertools.product(*constituent_actions))
    syntactic_pattern = composition_type["syntactic_patterns"][str(len(constituents))]
    syntactic_pattern_args = __extract_instruction_arguments(syntactic_pattern)
    for c in combinations:
        v_action = action.copy()
        v_action["instruction"] = syntactic_pattern
        for arg_index in range(len(syntactic_pattern_args)):
            for key in c[arg_index]:
                if key not in ["instructions", "id"]:
                    v_action[f"{key}_{str(arg_index)}"] = c[arg_index][key]
            v_action["instruction"] = v_action["instruction"].replace(
                syntactic_pattern_args[arg_index], c[arg_index]["instruction"]
            )
        local_actions.append(v_action)
    return local_actions


def _process_action(action, mod: str = None):
    local_actions = []
    action_type = action["type"]
    if action_type == "atomic":
        local_actions = _process_atomic_action(action, mod)
    elif action_type == "composite":
        local_actions = _process_composite_action(action)
    return local_actions


def __extract_instruction_arguments(instruction):
    return re.findall(r"\{[^}]*\}", instruction)
