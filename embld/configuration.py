import json

APP_PARAMETERS = {}
with open("config.json", "r") as stream:
    try:
        parameters = json.load(stream)
        APP_PARAMETERS.update(parameters)
    except Exception as exc:
        print(exc)
