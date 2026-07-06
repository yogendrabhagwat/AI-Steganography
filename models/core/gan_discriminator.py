try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
if TORCH_AVAILABLE:

    class SpectralConv(nn.Module):

        def __init__(self, in_ch, out_ch, kernel=3, stride=1, pad=1):
            super().__init__()
            self.conv = nn.utils.spectral_norm(
                nn.Conv2d(in_ch, out_ch, kernel, stride=stride, padding=pad, bias=False))

        def forward(self, x):
            return self.conv(x)

    class SteganalysisDiscriminator(nn.Module):

        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(SpectralConv(3, 32, 3, 1, 1), nn.LeakyReLU(0.2, inplace=True), SpectralConv(32, 64, 3, 2, 1), nn.BatchNorm2d(64), nn.LeakyReLU(0.2, inplace=True), SpectralConv(64, 128, 3, 2, 1), nn.BatchNorm2d(
                128), nn.LeakyReLU(0.2, inplace=True), SpectralConv(128, 256, 3, 2, 1), nn.BatchNorm2d(256), nn.LeakyReLU(0.2, inplace=True), SpectralConv(256, 512, 3, 2, 1), nn.BatchNorm2d(512), nn.LeakyReLU(0.2, inplace=True), nn.AdaptiveAvgPool2d(4))
            self.classifier = nn.Sequential(nn.Flatten(), nn.Linear(
                512 * 16, 1024), nn.LeakyReLU(0.2), nn.Dropout(0.3), nn.Linear(1024, 1), nn.Sigmoid())

        def forward(self, x):
            return self.classifier(self.features(x))

    class GANLoss(nn.Module):

        def __init__(self, lambda_adv=0.1, lambda_rec=1.0, lambda_perceptual=0.01):
            super().__init__()
            self.lambda_adv = lambda_adv
            self.lambda_rec = lambda_rec
            self.lambda_perceptual = lambda_perceptual
            self.bce = nn.BCELoss()
            self.mse = nn.MSELoss()

        def generator_loss(self, cover, stego, secret, secret_recovered, disc_pred):
            adv = self.bce(disc_pred, torch.ones_like(disc_pred))
            cover_mse = self.mse(stego, cover)
            sec_rec = self.mse(secret_recovered, secret)
            return self.lambda_adv * adv + self.lambda_rec * cover_mse + self.lambda_perceptual * sec_rec

        def discriminator_loss(self, real_pred, fake_pred):
            real_loss = self.bce(real_pred, torch.ones_like(real_pred))
            fake_loss = self.bce(fake_pred, torch.zeros_like(fake_pred))
            return (real_loss + fake_loss) * 0.5
else:

    class SteganalysisDiscriminator:
        pass

    class GANLoss:
        pass
