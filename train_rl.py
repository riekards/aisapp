from stable_baselines3 import PPO
from app.self_improve_env import SelfImproveEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv
from app.agent import Agent
import os

def main():
    # Use stub mode (no external LLM calls)
    agent = Agent(use_real_llm=False, test_cmd="pytest tests/test_smoke.py -q")
    # Set up a logs folder
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    # Wrap with Monitor to auto‐record episode reward to logs/monitor.csv
    raw_env = SelfImproveEnv(agent=agent, use_real_llm=False, max_steps=50, warmup_episodes=5)
    mon_env = Monitor(raw_env, log_dir, allow_early_resets=True)
    env = DummyVecEnv([lambda: mon_env])
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=128,
        batch_size=32,
        n_epochs=2,
        clip_range=0.2,
        ent_coef=0.001,
        device="cpu",
    )
    # Train for 10k timesteps
    model.learn(total_timesteps=100000)
    # Save the trained policy
    model.save("ppo_self_improve.zip")
    print("Training complete. Model saved as 'ppo_self_improve'.")

if __name__ == "__main__":
    main()