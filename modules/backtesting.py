class LoopModelTester:
    def __init__(self, data, model, oos_periods, warmup=252):
        self.data = data
        self.model = model
        self.warmup = warmup
        self.oos_periods = oos_periods
        # Logic of this: many things could be coming back from the models forecast function
        # so we'll use a dict to store arbitrary objects
        self.oos_forecasts = dict.fromkeys(data.index)

    def iter_gen(self):
        length = len(self.data)
        # Number of time periods of length 'oos_periods' that we need to loop over
        iterations = (length - self.warmup) // self.oos_periods
        # To handle remainders in the above calculation, we add them to the warmup period so we get a clean
        # loop where the final loop covers the last part of the data
        new_warmup = self.warmup + (length - self.warmup) % self.oos_periods
        for t in range(iterations):
            if t == 0:
                fit_index = new_warmup
            else:
                fit_index = new_warmup + (self.oos_periods * t)
            yield fit_index

    def walk_forward_test(self):
        for index in self.iter_gen():
            fit_data = self.data[:index]
            self.model.fit(fit_data)

            t = 0
            for forecast in self.model.forecast(self.oos_periods):
                date_index = self.data.index[(index + t)]
                self.oos_forecasts[date_index] = forecast
                t += 1
