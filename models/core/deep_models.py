import torch
import torch.nn as nn
import torch.nn.functional as F


class NoiseLayer(nn.Module):
    # Adds slight random noise during training to improve robustness
    def forward(self, x):
        if self.training:
            x = x + torch.randn_like(x) * 0.01
        return x


class EncoderBlock(nn.Module):
    def __init__(self, in_c, out_c):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_c, out_c, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_c),
            nn.SiLU(inplace=True),
            nn.Conv2d(out_c, out_c, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_c),
            nn.SiLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class DeepStegoEncoder(nn.Module):
    def __init__(self, secret_channels=1):
        super().__init__()

        self.secret_upsample = nn.Sequential(
            nn.ConvTranspose2d(
                secret_channels, secret_channels, kernel_size=2, stride=2, bias=False
            )
        )
        nn.init.constant_(self.secret_upsample[0].weight, 1.0)

        self.entry = nn.Conv2d(3 + 1, 64, 3, padding=1, bias=False)
        self.net = nn.Sequential(EncoderBlock(64, 64), EncoderBlock(64, 64))
        self.exit = nn.Conv2d(64, 3, 3, padding=1)
        nn.init.uniform_(self.exit.weight, -0.0001, 0.0001)
        nn.init.zeros_(self.exit.bias)

    def forward(self, cover, secret):
        s_up = self.secret_upsample(secret)

        carrier = cover * 255.0

        quantized_state = torch.floor(carrier * 0.5)
        modulated_signal = carrier.clone()
        modulated_signal[:, 0:1, :, :] = (quantized_state[:, 0:1, :, :] * 2.0) + s_up

        return torch.clamp(modulated_signal / 255.0, 0.0, 1.0)


class DeepStegoDecoder(nn.Module):
    def __init__(self, secret_channels=1):
        super().__init__()
        self.noise = NoiseLayer()
        self.entry = nn.Conv2d(3, 32, 3, padding=1, bias=False)
        self.bn_entry = nn.BatchNorm2d(32)
        self.net = nn.Sequential(
            nn.Conv2d(32, 64, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.SiLU(inplace=True),
            nn.Conv2d(64, 128, 3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.SiLU(inplace=True),
            nn.Conv2d(128, 128, 3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.SiLU(inplace=True),
            nn.Conv2d(128, 64, 3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.SiLU(inplace=True),
        )
        self.exit = nn.Conv2d(64, secret_channels, 1)

    def forward(self, stego):
        signal = torch.round(stego * 255.0)

        extracted_phase = signal[:, 0:1, :, :] - 2.0 * torch.floor(
            signal[:, 0:1, :, :] * 0.5
        )

        secret_out = extracted_phase[:, :, 0::2, 0::2]

        return secret_out
