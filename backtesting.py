class LoopModelTester:
    def __init__(self, data, model, oos_periods, warmup=252):
        self.data = data
        self.model = model
        self.warmup = warmup
        self.oos_periods = oos_periods
    
    def _calc_iterations(self):
        length = len(self.data)
        