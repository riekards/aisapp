class Env:
    metadata = {}
    def reset(self, seed=None, options=None):
        return None, {}
    def step(self, action):
        return None, 0.0, True, False, {}

class spaces:
    class Box:
        def __init__(self, low, high, shape=None, dtype=None):
            self.low = low
            self.high = high
            self.shape = shape
            self.dtype = dtype
