# batch_self_improve.py
import os
from datetime import datetime
import json
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.evaluation import evaluate_policy

from app.agent import Agent
from app.self_improve import SelfImproveEngine
from app.self_improve_env import SelfImproveEnv



def make_env(rank):
    """
    Helper to create one env instance.
    We'll launch N of these in parallel.
    """
    def _init():
        # stub out real LLM calls during this batch run
        agent = Agent(use_real_llm=False)
        # Skip creating new backups during batch training
        agent.improver = SelfImproveEngine(agent, use_real_llm=False, skip_backups=True)
        env = SelfImproveEnv(agent, max_steps=200)
        return Monitor(env, f"logs/monitor.csv", allow_early_resets=True)
    return _init

def main():
    os.makedirs("logs", exist_ok=True)
    csv_log = "logs/training_log.csv"

    # launch 4 parallel envs (tune this to your CPU/GPU)
    n_envs = 12
    envs = [make_env(i) for i in range(n_envs)]
    vec_env = SubprocVecEnv(envs)

    model = PPO(
        "MlpPolicy",
        vec_env,
        verbose=1,
        learning_rate=5e-4,
        n_steps=800,       # rollout length per env
        batch_size=64,
        n_epochs=5,
        ent_coef=0.05,
        device="cuda",
        clip_range=0.2,
        gamma=0.995,
        gae_lambda=0.9,
    )

    timesteps_per_iteration = 100000
    max_iterations = 100

    # ensure the dir exists
    os.makedirs("checkpoints", exist_ok=True)

    # save a checkpoint every `timesteps_per_iteration` steps (across all envs)
    save_freq = timesteps_per_iteration // n_envs
    checkpoint_callback = CheckpointCallback(
        save_freq=save_freq,
        save_path="checkpoints",
        name_prefix="ppo_self_improve"
    )

    try:
        for i in range(1, max_iterations + 1):
            print(f"▶ Iteration {i}/{max_iterations}: training {timesteps_per_iteration} steps")
            model.learn(
                total_timesteps=timesteps_per_iteration,
                reset_num_timesteps=False,
                callback=checkpoint_callback,
            )
            # also snapshot at the end of each chunk
            model.save(f"checkpoints/ppo_iter_{i * timesteps_per_iteration}.zip")
    except KeyboardInterrupt:
        print("\n⏸️  Training interrupted early…")
    finally:
        # Replace the simple save with consolidation
        consolidated_path = consolidate_training(model, vec_env)
        print(f"🎯 Training complete - consolidated model at {consolidated_path}")

def consolidate_training(model, vec_env, checkpoints_dir="checkpoints"):
    """Evaluate final model and save consolidated results"""
    print("🔄 Consolidating training results...")
    
    # Create a fresh environment for evaluation
    eval_env = make_env(0)()
    
    try:
        # Evaluate final model performance
        mean_reward, std_reward = evaluate_policy(model, eval_env, n_eval_episodes=20)
        
        # Save consolidated information
        consolidated_info = {
            "mean_reward": float(mean_reward),
            "std_reward": float(std_reward),
            "training_completed": True,
            "timestamp": str(datetime.now()),
        }
        
        # Save both model and metrics in final archive
        final_path = os.path.join(checkpoints_dir, "consolidated_model.zip")
        model.save(final_path)
        
        # Save metrics alongside model
        metrics_path = os.path.join(checkpoints_dir, "consolidated_metrics.json")
        with open(metrics_path, 'w') as f:
            json.dump(consolidated_info, f, indent=2)
        
        print(f"✅ Consolidated model saved to {final_path}")
        print(f"📊 Final mean reward: {mean_reward:.2f} ± {std_reward:.2f}")
        
        # Clean up intermediate checkpoints
        for f in os.listdir(checkpoints_dir):
            if f.startswith("ppo_") and f != "consolidated_model.zip":
                os.remove(os.path.join(checkpoints_dir, f))
    
    finally:
        # Clean up evaluation environment
        eval_env.close()
    
    return final_path

if __name__ == "__main__":
    main()
