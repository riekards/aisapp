import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from trainer import Trainer

class MemoryHandler(FileSystemEventHandler):
    """
    Watches the memory_store folder. When a new JSON appears,
    checks if memory size exceeds threshold and calls fine-tune.
    """
    def __init__(self, trainer: Trainer, threshold: int = 100):
        super().__init__()
        self.trainer = trainer
        self.threshold = threshold

    def on_created(self, event):
        # Called when a new file is created in memory_store/
        memory_buffer = self.trainer.memory.buffer
        if len(memory_buffer) >= self.threshold:
            print(f"[SelfImprove] Memory size {len(memory_buffer)} ≥ {self.threshold}. Triggering fine-tune.")
            self.trainer.fine_tune()

def start_self_improvement(config_path: str = "configs/default.yaml", threshold: int = 100):
    """
    Launches a watchdog observer on memory_store/ and runs indefinitely in a background thread.
    """
    trainer = Trainer(config_path=config_path)
    memory_path = trainer.memory.storage_path

    event_handler = MemoryHandler(trainer=trainer, threshold=threshold)
    observer = Observer()
    observer.schedule(event_handler, path=memory_path, recursive=False)
    observer.start()

    print(f"[SelfImprove] Monitoring '{memory_path}' for new memory files.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    # If someone runs this script directly, start the watcher
    start_self_improvement()
