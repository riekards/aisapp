class PPO:
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls, path, env=None):
        return cls()

    def save(self, path):
        pass

    def learn(self, *args, **kwargs):
        pass

    def predict(self, obs, deterministic=True):
        return [0.0], None

__all__ = ["PPO"]
