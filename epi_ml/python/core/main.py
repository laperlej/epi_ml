import os
import sys
import warnings
warnings.simplefilter("ignore")
import data
import model
import trainer
import config
import os.path
import matplotlib.pyplot as plt
from scipy import signal
import h5py
import numpy as np
import visualisation

def spectro_hg(path):
    f = h5py.File(path)
    for group in f:
        md5=group
        break
    array = np.array([])
    for i in ["chr1","chr2","chr3","chr4","chr5","chr6","chr7","chr8","chr9","chr10","chr11","chr12","chr13","chr14","chr15","chr16","chr17","chr18","chr19","chr20","chr21","chr22","chrX"]:
        array = np.concatenate((array, f[md5][i][...]), axis=0)
    norm = (array - array.mean()) / array.std()
    #print(norm.size)
    spectro(norm)

def spectro(x):
        f, t, Sxx = signal.spectrogram(x, window=("tukey",0.005), noverlap=40, nfft=80, nperseg=64, fs=16000)
        #f, t, Sxx = signal.spectrogram(x, window=("gaussian",5), nperseg=2**16)
        #f, t, Sxx = signal.spectrogram(x)
        #plt.figure()
        #plt.plot(x)
        plt.figure()
        plt.pcolormesh(t, f, np.log10(Sxx))
        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        plt.show()

def main(args):
    #test_path = "/Users/Jon/Projects/epi_ml/epi_ml/python/core/1110b4cbcd3f8659d2c479b8889e3eeb_1kb_all_none.hdf5"
    #test_path = "/Users/Jon/Projects/epi_ml/epi_ml/python/core/66638a9c6899bf55f60a8b95dca0eee4_1kb_all_none.hdf5"
    #spectro_hg(test_path)

    my_data = data.EpiData("assay")
    #my_data = data.EpiData("assay_category", oversample=True)
    #my_data = data.EpiData("publishing_group")

    #spectro(my_data.test.signals[55])

    input_size = my_data.train.signals[0].size
    ouput_size = my_data.train.labels[0].size

    my_model = model.Dense(input_size, ouput_size)
    #my_model = model.Cnn(41*49, ouput_size, (41, 49))
    #my_model = model.BidirectionalRnn(input_size, ouput_size)

    my_trainer = trainer.Trainer(my_data, my_model)
    my_trainer.train()
    my_trainer.metrics()

    vis = visualization.Mds(my_data)
    my_trainer.visualise(vis)
    #my_trainer.importance() #TODO: generalize, probably put in model

if __name__ == "__main__":
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    main(sys.argv[1:])
