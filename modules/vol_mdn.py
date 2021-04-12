import torch
import torch.nn as nn
from torch.distributions import Categorical, Normal, MixtureSameFamily
from torch.optim.swa_utils import AveragedModel, SWALR
import pandas as pd
import numpy as np
import sqlite3


class MDN(nn.Module):
    def __init__(self, in_dim, out_dim, hidden_dim, n_components):
        """
        Mixture density network.
        in_dim: Number of input variables
        out_dim: Number of output variables
        hidden_dim: Size of hidden layer
        n_components: Number of normal distributions to use in mixture
        """
        super().__init__()
        self.n_components = n_components
        # Last layer output dimension rationale:
        # Need two parameters for each distributionm thus 2 * n_components.
        # Need each of those for each output dimension, thus that multiplication
        self.norm_network = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ELU(),
            nn.Dropout(),
            nn.Linear(hidden_dim, 2 * n_components * out_dim),
        )
        self.cat_network = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ELU(),
            nn.Dropout(),
            nn.Linear(hidden_dim, n_components * out_dim),
        )

    def forward(self, x):
        norm_params = self.norm_network(x)
        # Split so we get parameters for mean and standard deviation
        mean, std = torch.split(norm_params, norm_params.shape[1] // 2, dim=1)
        # We need rightmost dimension to be n_components for mixture
        mean = mean.view(mean.shape[0], -1, self.n_components)
        std = std.view(std.shape[0], -1, self.n_components)
        normal = Normal(mean, torch.exp(std))

        cat_params = self.cat_network(x)
        # Again, rightmost dimension must be n_components
        cat = Categorical(
            logits=cat_params.view(cat_params.shape[0], -1, self.n_components)
        )

        return MixtureSameFamily(cat, normal)


class MDNVol:
    def __init__(self, x, y):
        """
        Utility class for fitting the mixture density network for forecasting volatility on the SPX.
        Parameters have been tuned for efficieny.
        x: Input data
        y: Output data used for calculating loss function during training
        """
        self.x = torch.Tensor(x.values)
        self.y = torch.Tensor(y.values)
        self.model = MDN(x.shape[1], 1, 250, 5)

    def fit_model(self):
        """
        Fits model. Uses AdamW optimizer, model averaging, and a cosine annealing learning rate schedule.
        """
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=0.001)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, 100, 2
        )

        self.swa_model = AveragedModel(self.model)
        swa_start = 750
        swa_scheduler = SWALR(
            optimizer, swa_lr=0.001, anneal_epochs=10, anneal_strategy="cos"
        )

        self.model.train()
        self.swa_model.train()
        for epoch in range(1000):
            optimizer.zero_grad()
            output = self.model(self.x)

            loss = -output.log_prob(self.y.view(-1, 1)).sum()

            loss.backward()
            optimizer.step()

            if epoch > swa_start:
                self.swa_model.update_parameters(self.model)
                swa_scheduler.step()
            else:
                scheduler.step()

            if epoch % 10 == 0:
                print(f"Epoch {epoch} complete. Loss: {loss}")

    def output_dist(self, x):
        """
        Fits model and returns fitted distribution object.

        Returns: PyTorch MixtureNormal object
        """
        self.fit_model()
        self.swa_model.eval()
        return self.swa_model(torch.Tensor(x).view(1, -1))


def rv_calc(data):
    """
    Calculates daily realized variance using intraday data.
    data: Pandas dataframe with datetime index

    Returns: Pandas series
    """
    results = {}

    for idx, data in data.groupby(data.index.date):
        returns = np.log(data["close"]) - np.log(data["close"].shift(1))
        results[idx] = np.sum(returns ** 2)

    return pd.Series(results)


def create_lags(series, lags, name="x"):
    """
    Creates a dataframe with lagged values of the given series.
    Generates columns named x_t-n which means the value of each row is the value of the original series lagged n times
    series: Pandas series
    lags: number of lagged values to include
    name: String to put as prefix for each column name

    Returns: Pandas dataframe
    """
    result = pd.DataFrame(index=series.index)
    result[f"{name}_t"] = series

    for n in range(lags):
        result[f"{name}_t-{n+1}"] = series.shift((n + 1))

    return result


class Data:
    def __init__(self):
        """
        Gets data for training the MDNVol network. Also outputs data for out-of-sample forecasting.
        """
        spx_minute = pd.read_csv(
            "SPX_1min.csv",
            header=0,
            names=["datetime", "open", "high", "low", "close"],
            index_col="datetime",
            parse_dates=True,
        )
        self.spx_variance = rv_calc(spx_minute)

        conn = sqlite3.Connection("data.db")
        spx_data = pd.read_sql(
            "SELECT * FROM prices WHERE ticker='^GSPC'",
            conn,
            index_col="date",
            parse_dates="date",
        )
        spx_returns = np.log(spx_data["close"]) - np.log(spx_data["close"].shift(1))
        self.spx_returns = spx_returns.dropna()

        vix_data = pd.read_sql(
            "SELECT * FROM prices WHERE ticker='^VIX'",
            conn,
            index_col="date",
            parse_dates="date",
        )
        # This puts it into units of daily standard deviation
        self.vix = vix_data["close"] / np.sqrt(252) / 100

        vix_lags = create_lags(np.log(self.vix), 21, name="vix")
        return_lags = create_lags(self.spx_returns, 21, name="returns")
        rv_lags = create_lags(np.log(self.spx_variance), 21, name="rv")

        self.x = pd.concat([vix_lags, return_lags, rv_lags], axis=1).dropna()

    def get_training_data(self):
        """
        Gets data for training the network
        """
        # Calculates variance realized over the next 5 days. Logged for better distributional qualities.
        y = np.log(self.spx_variance.rolling(5).sum().shift(-5)).dropna()
        # Find common index between our input and output data so everything matches.
        common_index = self.x.index.intersection(y.index)
        x = self.x.loc[common_index]
        y = y.loc[common_index]

        return x, y

    def get_forecast_data(self):
        """
        Gets last input row to use for out-of-sample forecasting.
        """
        return self.x.iloc[-1]
