# This is a sample Python script.


# Press the green button in the gutter to run the script.
import timeit

from tqdm import trange

from embld.experiment.protocol import EMBLDAcquisitionDriver

if __name__ == '__main__':
    driver = EMBLDAcquisitionDriver()
    start = timeit.default_timer()
    for i in trange(1000000):
        sequence = driver.sample_configurations()
        # print(sequence)
    end = timeit.default_timer()
    print(end-start)
