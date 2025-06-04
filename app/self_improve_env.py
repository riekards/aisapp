# app/self_improve_env.py
import numpy as np
import gymnasium as gym
from gymnasium import spaces

class SelfImproveEnv(gym.Env):
    """
    Gymnasium environment wrapping the self-improvement loop.
    Action: array([temperature]) in [0.0,1.0]
    Observation: [last_reward, pending_features_count]
    Reward: +1 if patch applied successfully, -1 otherwise.
    Episodes last for `max_steps` steps.
    """
    metadata = {'render_modes': ['human']}

    def __init__(self, agent, use_real_llm: bool = False, max_steps: int = 50, warmup_episodes: int = 5):
        super().__init__()
        self.agent = agent
        self.use_real_llm = use_real_llm
        self.max_steps = max_steps
        # Track episodes and steps
        self.current_episode = 0
        self.step_count = 0
        self.warmup_episodes = warmup_episodes

        # Observation: last_reward, pending_features_count
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(3,), dtype=np.float32)
        # Action: temperature in [0,1]
        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(1,), dtype=np.float32
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.last_reward = 0.0
        self.pending = len(self.agent.get_features())
        self.step_count = 0
        self.current_episode += 1

        obs = np.array([self.last_reward, self.pending, self.step_count], dtype=np.float32)
        progress = self.step_count / self.max_steps
        obs = np.array([self.last_reward, self.pending, progress], dtype=np.float32)
        info = {}
        return obs, info

    def step(self, action):
        # 1) Apply the chosen temperature
        temp = float(action[0])
        self.agent.temperature = temp

        # 2) Run the self-improve step (unless we’re still in warm-up)
        try:
            result = self.agent.improver.run_cycle() if self.current_episode > self.warmup_episodes else True
        except Exception:
            result = False

        # 3) Advance step counter and compute terminal
        self.step_count += 1
        terminated = self.step_count >= self.max_steps

        # 4) Assign reward
        if self.current_episode <= self.warmup_episodes:
            # warm-up: only reward at episode end, otherwise zero living reward
            reward = 1.0 if terminated else 0.0
        else:
            if terminated:
                # big terminal reward/penalty
                if result is True or result == 'success':
                    reward = +1.0
                elif result == 'partial':
                    reward = +0.5
                else:
                    reward = -1.0
            else:
                # small living penalty to discourage long, unproductive episodes
                reward = -0.01

        # 5) Update bookkeeping
        self.last_reward = reward
        self.pending     = len(self.agent.get_features())

        # 6) Build new observation
        obs = np.array(
            [self.last_reward, self.pending, self.step_count],
            dtype=np.float32
        )

        # 7) Return in Gymnasium v0.26+ signature
        return obs, reward, terminated, False, {}



    def render(self, mode='human'):
        print(
            f"Episode {self.current_episode} | Step {self.step_count} | "
            f"Temp {getattr(self.agent, 'temperature', None):.2f} | "
            f"Reward {self.last_reward} | Pending {self.pending}"
        )
