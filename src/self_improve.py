import time
import threading
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from trainer import Trainer

class MemoryHandler(FileSystemEventHandler):
    """
    Watches memory_store/. When a new file appears, checks if
    memory size ≥ threshold (from config) and triggers fine-tune.
    """
    def __init__(self, trainer: Trainer, threshold: int):
        super().__init__()
        self.trainer = trainer
        self.threshold = threshold

    def on_created(self, event):
        memory_buffer = self.trainer.memory.buffer
        if len(memory_buffer) >= self.threshold:
            print(f"[SelfImprove] Memory size {len(memory_buffer)} ≥ {self.threshold}. Triggering fine-tune.")
            self.trainer.fine_tune()

def start_self_improvement(config_path: str = "configs/default.yaml"):
    """
    Launch a watcher that triggers Trainer.fine_tune() when memory reaches threshold.
    """
    # Load the same config file to retrieve threshold
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    threshold = cfg.get("trainer", {}).get("self_improve_threshold", 100)
    trainer = Trainer(config_path=config_path)
    memory_path = trainer.memory.storage_path

    event_handler = MemoryHandler(trainer=trainer, threshold=threshold)
    observer = Observer()
    observer.schedule(event_handler, path=memory_path, recursive=False)
    observer.start()

    print(f"[SelfImprove] Monitoring '{memory_path}' with threshold {threshold}.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_self_improvement()
