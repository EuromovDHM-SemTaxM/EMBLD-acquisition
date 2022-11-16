# This is a sample Python script.


# Press the green button in the gutter to run the script.
import time
import timeit

from pyo import Osc, pa_get_output_devices, Sine, Server
from tqdm import trange

from embld.experiment.protocol import EMBLDAcquisitionDriver, AudioPlayer
from qtmrt.client import QTMRTClient

if __name__ == '__main__':
    # # print(pa_get_output_devices())
    import embld
    from embld import configuration

    driver = EMBLDAcquisitionDriver(QTMRTClient("localhost", 22222, "toto"))
    # start = timeit.default_timer()
    # sequence = driver.sample_configurations()
    # print(len(sequence))
    # t = sequence[0]['sound']
    # player = AudioPlayer(Server(buffersize=1024, duplex=0, winhost="directsound").boot())
    # player.start()
    # for i in range(len(sequence)):
    #     player.play_audio(sequence[i]['sound'])
    # player.wait()
    #
    # end = timeit.default_timer()
    # print(end - start)

    actions = driver.__generate_actions()
    pass
