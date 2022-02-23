import pytorch_lightning as pl
import pytorch_lightning.callbacks as torch_callbacks
import numpy as np
import pandas

import os.path
from scipy import signal
from abc import ABC
import math
from datetime import datetime

from .data import DataSet
from core.pytorch_model_test import LightningDenseClassifier

class MyTrainer(pl.Trainer):

    def __init__(self, general_log_dir : str, last_trained_model : pl.LightningModule, **kwargs):
        """Metrics expect probabilities and not logits"""
        super().__init__(**kwargs)

        self.best_checkpoint_file = os.path.join(
            general_log_dir,
            "best_checkpoint.list"
            )

        self.model = last_trained_model

    def save_model_path(self):
        """Save best checkpoint path to a file."""
        print("Saving model to {}".format(self.checkpoint_callback.best_model_path))
        with open(self.best_checkpoint_file, "a") as ckpt_file:
            ckpt_file.write("{} {}\n".format(self.checkpoint_callback.best_model_path, datetime.now()))

    def print_hyperparameters(self):
        """Print training hyperparameters."""
        stop_callback = self.early_stopping_callback
        print("--TRAINING HYPERPARAMETERS--")
        print("L2 scale : {}".format(self.model.l2_scale))
        print("Dropout rate : {}".format(self.model.dropout_rate))
        print("Learning rate : {}".format(self.model.learning_rate))
        print("Patience : {}".format(stop_callback.patience))
        print("Monitored value : {}".format(stop_callback.monitor))
        print("Batch size : {}".format(self.num_training_batches))


def define_callbacks(early_stop_limit: int):
    """Returns list of PyTorch trainer callbacks.

    RichModelSummary, EarlyStopping, ModelCheckpoint, RichProgressBar
    """
    summary = torch_callbacks.RichModelSummary(max_depth=3)

    monitored_value="valid_loss"
    mode="min"

    early_stop = torch_callbacks.EarlyStopping(
        monitor=monitored_value,
        mode=mode,
        patience=early_stop_limit,
        check_on_train_epoch_end=False
    )

    checkpoint = torch_callbacks.ModelCheckpoint(
        monitor=monitored_value,
        mode=mode,
        save_last=True,
        auto_insert_metric_name=True,
        every_n_epochs=1,
        save_top_k=2,
        save_on_train_epoch_end=False
    )

    bar = torch_callbacks.RichProgressBar()

    return [summary, early_stop, checkpoint, bar]
