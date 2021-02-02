import pandas as pd
import numpy as np
import pystan
from abc import ABC, abstractmethod


class ModelBase(ABC):
    """
    Abstract class for models to follow.
    """

    @abstractmethod
    def fit(self):
        pass

    @abstractmethod
    def forecast(self, oos_periods):
        """
        This function returns a forecast from the model. For generalizing to multi-period out-of-sample forecasts,
        this must act like a generator and yield the multi-period forecast one step at a time. This is relevant
        for the LoopModelTester in backtesting.py
        """
        yield NoneType


class StochVol(ModelBase):
    """
    Class for predicting realized volatility of returns.
    """

    def __init__(self):
        model_spec = """
            data {
                int len;
                vector[len] returns;
            }
            parameters {
                real mu;
                real<lower=-1, upper=1> phi;
                real<lower=0> sigma;
                vector[len] h_std;
            }
            transformed parameters {
                vector[len] h = h_std * sigma;          // Now normal(0, sigma)
                h[1] /= sqrt(1 - phi^2);                // Scale h[1]
                h += mu;                                // Now normal(mu, sigma)
                for (t in 2:len) {                      // Apply phi autoregression
                    h[t] += phi * (h[t-1] - mu);
                }
            }
            model {
                phi ~ uniform(-1, 1);
                sigma ~ cauchy(0, 5);
                mu ~ cauchy(0, 10);
                h_std ~ std_normal();
                returns ~ normal(0, exp(h/2));
            }
        """

        self.model = pystan.StanModel(model_code=model_spec)

    def fit(self, returns):
        """
        Fits Stan model using given returns
        """
        params = {"len": len(returns), "returns": returns}
        self.sample = self.model.sampling(data=params, chains=4, warmup=250, iter=1500)

    def forecast(self, oos_periods):
        """
        Forecast out-of-sample using fitted model
        """
        output = np.zeros((5000, oos_periods))

        sample_data = self.sample.extract()
        # Select most recent fitted volatility value
        h = sample_data["h"][:, -1]
        mu = sample_data["mu"]
        phi = sample_data["phi"]
        sigma = sample_data["sigma"]

        for _ in range(oos_periods):
            resids = sigma * np.random.randn(5000)
            forward_vol = mu + phi * (h - mu) + resids
            yield forward_vol
            # Set new 'most recent' vol value to our new predicted value so we can
            # do multi-period ahead forecasting
            h = forward_vol

        return output