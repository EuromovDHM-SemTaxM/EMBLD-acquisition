import ruamel.yaml as yaml

APP_PARAMETERS = {}
with open("config.yaml", "r") as stream:
    try:
        parameters = yaml.safe_load(stream)
        APP_PARAMETERS.update(parameters)
    except yaml.YAMLError as exc:
        print(exc)
