"""Like "main --predict mode", but for when no true label is available (cannot do certain analyses)."""
import comet_ml #needed because special snowflake # pylint: disable=unused-import
import pytorch_lightning as pl #in case GCC or CUDA needs it # pylint: disable=unused-import

import argparse
from datetime import datetime
import os
from pathlib import Path
import sys
import warnings

warnings.simplefilter("ignore", category=FutureWarning)

import numpy as np
from pytorch_lightning import loggers as pl_loggers
import torch
from torch.utils.data import TensorDataset

from epi_ml.python.argparseutils.directorychecker import DirectoryChecker
from epi_ml.python.core.model_pytorch import LightningDenseClassifier
from epi_ml.python.core import analysis
from epi_ml.python.core.data import Data, DataSet

from epi_ml.python.core.hdf5_loader import Hdf5Loader


def time_now():
    """Return datetime of call without microseconds"""
    return datetime.utcnow().replace(microsecond=0)


def parse_arguments(args: list) -> argparse.Namespace:
    """argument parser for command line"""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("hdf5", type=Path, help="A file with hdf5 filenames. Use absolute path!")
    arg_parser.add_argument("chromsize", type=Path, help="A file with chrom sizes.")
    arg_parser.add_argument("logdir", type=DirectoryChecker(), help="Directory for the output logs.")
    arg_parser.add_argument("--offline", action="store_true", help="Will log data offline instead of online. Currently cannot merge comet-ml offline outputs.")
    arg_parser.add_argument("--model", type=DirectoryChecker(), help="Directory from which to load the desired model. Default is logdir.")

    return arg_parser.parse_args(args)


def main(args):
    """main called from command line, edit to change behavior"""
    begin = time_now()
    print(f"begin {begin}")

    # --- PARSE params ---
    cli = parse_arguments(args)


    # --- Startup LOGGER ---
    #api key in config file
    IsOffline = cli.offline # additional logging fails with True
    exp_name = '-'.join(cli.logdir.parts[-2:])
    comet_logger = pl_loggers.CometLogger(
        project_name="EpiLaP",
        experiment_name=exp_name,
        save_dir=cli.logdir,
        offline=IsOffline,
        auto_metric_logging=False
    )
    exp_key = comet_logger.experiment.get_key()
    print(f"The current experiment key is {exp_key}")
    comet_logger.experiment.log_other("Experience key", f"{exp_key}")

    if "SLURM_JOB_ID" in os.environ:
        comet_logger.experiment.log_other("SLURM_JOB_ID", os.environ["SLURM_JOB_ID"])
        comet_logger.experiment.add_tag("Cluster")


    # --- LOAD DATA ---
    hdf5_loader = Hdf5Loader(chrom_file=cli.chromsize, normalization=True)
    hdf5_loader.load_hdf5s(data_file=cli.hdf5)
    files = hdf5_loader.signals

    md5s = []
    signals = []
    for md5, signal in files.items():
        md5s.append(md5)
        signals.append(signal)

    y = [0 for _ in md5s]
    y_str = ["No label available" for _ in y]

    test_set = Data(ids=md5s, x=signals, y=y, y_str=y_str, metadata=None)

    if test_set.num_examples == 0:
        raise Exception("Trying to test without any test data.")

    datasets = DataSet.empty_collection()
    datasets.set_test(test_set)

    test_dataset = TensorDataset(
        torch.from_numpy(test_set.signals).float(),
        torch.tensor(y, dtype=int)
        )


    # --- RESTORE model ---
    model_dir = cli.logdir
    if cli.model is not None:
        model_dir = cli.model
    my_model = LightningDenseClassifier.restore_model(model_dir)


    # --- OUTPUTS ---
    my_analyzer = analysis.Analysis(
        my_model, datasets, comet_logger,
        train_dataset=None, val_dataset=None, test_dataset=test_dataset
        )


    # --- Create prediction file ---
    my_analyzer.write_test_prediction()


    end = time_now()
    main_time = end - begin
    print(f"end {end}")
    print(f"Main() duration: {main_time}")
    comet_logger.experiment.log_other("Main duration", main_time)
    comet_logger.experiment.add_tag("Finished")

if __name__ == "__main__":
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    main(sys.argv[1:])
