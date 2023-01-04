def subject_string_trial(metadata, sequence_id, event_name):
    return f"{sequence_id}-S_{metadata['id']}-R_{metadata['session']}-{event_name}"

def subject_string_global(metadata):
    return f"S_{metadata['id']}-R_{metadata['session']}"