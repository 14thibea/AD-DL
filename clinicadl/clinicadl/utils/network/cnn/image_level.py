import numpy as np
import torch
from torch import nn

from clinicadl.utils.network.network import CNN
from clinicadl.utils.network.network_utils import *  # TODO: remove EarlyStopping from network_utils


class Conv5_FC3(CNN):
    """
    Classifier for a binary classification task

    Image level architecture
    """

    def __init__(self, input_shape, use_cpu=False, n_classes=2, dropout=0.5):

        super().__init__(use_cpu=use_cpu, n_classes=n_classes)
        # fmt: off
        convolutions = nn.Sequential(
            nn.Conv3d(1, 8, 3, padding=1),
            nn.BatchNorm3d(8),
            nn.ReLU(),
            PadMaxPool3d(2, 2),

            nn.Conv3d(8, 16, 3, padding=1),
            nn.BatchNorm3d(16),
            nn.ReLU(),
            PadMaxPool3d(2, 2),

            nn.Conv3d(16, 32, 3, padding=1),
            nn.BatchNorm3d(32),
            nn.ReLU(),
            PadMaxPool3d(2, 2),

            nn.Conv3d(32, 64, 3, padding=1),
            nn.BatchNorm3d(64),
            nn.ReLU(),
            PadMaxPool3d(2, 2),

            nn.Conv3d(64, 128, 3, padding=1),
            nn.BatchNorm3d(128),
            nn.ReLU(),
            PadMaxPool3d(2, 2),
        )

        # Compute the size of the first FC layer
        input_tensor = torch.zeros(input_shape).unsqueeze(0)
        output_convolutions = convolutions(input_tensor)

        self.convolutions = convolutions
        self.classifier = nn.Sequential(
            Flatten(),
            nn.Dropout(p=dropout),

            nn.Linear(np.prod(list(output_convolutions.shape)), 1300),
            nn.ReLU(),

            nn.Linear(1300, 50),
            nn.ReLU(),

            nn.Linear(50, self.n_classes)
        )
        # fmt: on
