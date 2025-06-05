import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from trainer import Trainer


def periodic_fine_tune(config_path: str = "configs/default.yaml"):
    """Reads config, fine-tunes on the current memory buffer every X minutes."""
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    interval_minutes = cfg.get("trainer", {}).get("self_improve_interval", 60)
    trainer = Trainer(config_path=config_path)

    scheduler = BackgroundScheduler()
    scheduler.add_job(trainer.fine_tune, "interval", minutes=interval_minutes, next_run_time=None)
    scheduler.start()

    print(f"[Scheduler] Scheduled fine-tune every {interval_minutes} minutes.")
    try:
        # Keep the scheduler thread alive indefinitely
        scheduler._event.wait()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("[Scheduler] Shutdown complete.")


if __name__ == "__main__":
    periodic_fine_tune()
