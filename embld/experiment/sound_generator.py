import logging
from pathlib import Path

from PyQt5.QtCore import QThread
from gtts import gTTS
from pydub import AudioSegment
from tqdm import tqdm

from embld.configuration import APP_PARAMETERS

logger = logging.getLogger()


class SoundGenerationThread(QThread):

    def __init__(self, generated_configurations, protocol_instance) -> None:
        super().__init__()
        logger.info("Initializing time thread...")
        self.__generated_configurations = generated_configurations
        self.protocol_instance = protocol_instance

    def run(self):
        sound_location = APP_PARAMETERS['sound_location']

        self.protocol_instance.add_sound("beep", AudioSegment.from_file(f'{sound_location}/beep.wav', format="wav"))
        for configuration in tqdm(self.__generated_configurations, desc="Loading sounds in the background..."):
            instruction = configuration['instruction']
            hash_key = instruction.lower().replace(",", "_").replace(" ", "_").replace(".", "")
            filename = sound_location + str(hash_key) + ".mp3"
            if not Path(filename).exists():
                try:
                    gTTS(configuration['instruction']).save(filename)
                except Exception as e:
                    pass
            self.protocol_instance.add_sound(hash_key, AudioSegment.from_file(filename, format="mp3"))

        self.exec_()
