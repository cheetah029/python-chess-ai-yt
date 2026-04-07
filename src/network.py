"""
Neural network for position evaluation.

Takes an encoded board state (21 channels × 8×8) and outputs a win probability
(0.0 = current player loses, 1.0 = current player wins).

Architecture:
  - Convolutional layers to detect spatial patterns
  - Residual connections for deeper learning
  - Dense layers to combine features into a single value

The network learns entirely from self-play outcomes — no human-defined
evaluation features.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from encoding import NUM_CHANNELS


class ResidualBlock(nn.Module):
    """Residual block with two conv layers and skip connection."""

    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + residual
        return F.relu(out)


class ValueNetwork(nn.Module):
    """Predicts win probability from board state.

    Input: (batch, 21, 8, 8) encoded board state
    Output: (batch, 1) win probability for current player
    """

    def __init__(self, in_channels=NUM_CHANNELS, conv_channels=128,
                 num_res_blocks=6, fc_size=256):
        super().__init__()

        # Initial convolution
        self.input_conv = nn.Sequential(
            nn.Conv2d(in_channels, conv_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(conv_channels),
            nn.ReLU(),
        )

        # Residual tower
        self.res_blocks = nn.Sequential(
            *[ResidualBlock(conv_channels) for _ in range(num_res_blocks)]
        )

        # Value head
        self.value_head = nn.Sequential(
            nn.Conv2d(conv_channels, 1, kernel_size=1),
            nn.BatchNorm2d(1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(8 * 8, fc_size),
            nn.ReLU(),
            nn.Linear(fc_size, 1),
            nn.Sigmoid(),  # output in [0, 1]
        )

    def forward(self, x):
        x = self.input_conv(x)
        x = self.res_blocks(x)
        return self.value_head(x)

    def predict(self, board_tensor):
        """Predict win probability for a single board state.

        Args:
            board_tensor: numpy array of shape (21, 8, 8) or torch tensor

        Returns:
            float: win probability in [0, 1]
        """
        self.eval()
        with torch.no_grad():
            if not isinstance(board_tensor, torch.Tensor):
                board_tensor = torch.FloatTensor(board_tensor)
            if board_tensor.dim() == 3:
                board_tensor = board_tensor.unsqueeze(0)
            board_tensor = board_tensor.to(next(self.parameters()).device)
            return self.forward(board_tensor).item()

    def predict_batch(self, board_tensors):
        """Predict win probabilities for a batch of board states.

        Args:
            board_tensors: numpy array of shape (N, 21, 8, 8) or torch tensor

        Returns:
            numpy array of shape (N,) with win probabilities
        """
        self.eval()
        with torch.no_grad():
            if not isinstance(board_tensors, torch.Tensor):
                board_tensors = torch.FloatTensor(board_tensors)
            board_tensors = board_tensors.to(next(self.parameters()).device)
            return self.forward(board_tensors).squeeze(-1).cpu().numpy()

    def save(self, path):
        """Save model weights."""
        torch.save({
            'model_state_dict': self.state_dict(),
            'config': {
                'conv_channels': self.input_conv[0].out_channels,
                'num_res_blocks': len(self.res_blocks),
                'fc_size': self.value_head[4].out_features,
            }
        }, path)

    @classmethod
    def load(cls, path, device='cpu'):
        """Load model from saved weights."""
        checkpoint = torch.load(path, map_location=device)
        config = checkpoint['config']
        model = cls(
            conv_channels=config['conv_channels'],
            num_res_blocks=config['num_res_blocks'],
            fc_size=config['fc_size'],
        )
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(device)
        return model
