class SubprocVecEnv:
    def __init__(self, env_fns):
        self.env_fns = env_fns

class DummyVecEnv(SubprocVecEnv):
    pass
