# Self-Improving RL Agent

This project contains a reinforcement learning agent that learns how to tune its self-improvement loop. The key scripts are `train_rl.py` and `batch_self_improve.py`.

## Setup

Install dependencies into your Python environment:

```bash
pip install -r requirements.txt
```

## Stub Training

`batch_self_improve.py` launches multiple stubbed environments in parallel. It uses `Agent(use_real_llm=False)` so that no external language model is called. Run it to generate an initial policy:

```bash
python batch_self_improve.py
```

Checkpoints and metrics are written to the `checkpoints/` directory. The script ends by consolidating the model and printing the mean reward.

## Fine‑tuning on the Real Environment

After stub training, fine‑tune in the real environment. Edit `train_rl.py` to instantiate `Agent(use_real_llm=True)` and pass `use_real_llm=True` to `SelfImproveEnv`. Then run:

```bash
python train_rl.py
```

This uses the `Monitor` wrapper so rewards are logged to `logs/monitor.csv`.

## Reward Metrics

Before using the agent in production, inspect `logs/monitor.csv` and ensure that the PPO training achieves an average episode reward (`ep_rew_mean`) of at least **0**. Lower rewards indicate the agent is not reliably improving the codebase.

