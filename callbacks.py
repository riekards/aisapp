# callbacks.py
import os
import csv
from stable_baselines3.common.callbacks import BaseCallback

class EpisodeCSVLogger(BaseCallback):
    """
    After each episode, append a row [episode_number, total_timesteps, episode_reward, episode_length]
    to a CSV file.
    """
    def __init__(self, csv_path: str, verbose=0):
        super().__init__(verbose)
        self.csv_path = csv_path
        # ensure directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        # write header if new file
        if not os.path.exists(csv_path):
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["episode", "timesteps", "reward", "length"])

    def _on_step(self) -> bool:
        # nothing to do every step
        return True

    def _on_rollout_end(self) -> None:
        """
        Called after each rollout collection (i.e. after n_steps), but we only want to log
        on actual episode ends, so we'll check the Monitor info dict.
        """
        # infos is a list of info dicts from the last rollout
        for info in self.locals["infos"]:
            if "episode" in info:
                ep_info = info["episode"]
                episode_no = ep_info.get("r")  # SB3 packs reward in 'r'
                # Actually SB3 Monitor stores:
                #   info["episode"]["r"] = episode_reward
                #   info["episode"]["l"] = episode_length
                #   info["episode"]["t"] = total_timesteps at end
                reward = ep_info["r"]
                length = ep_info["l"]
                timesteps = ep_info["t"]
                # get a running count of the episode index
                self.num_episodes += 1
                with open(self.csv_path, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([self.num_episodes, timesteps, reward, length])
        return None

    def _on_training_start(self) -> None:
        # initialize counter
        self.num_episodes = 0
