import argparse
import threading
from self_improve import start_self_improvement


def main():
    parser = argparse.ArgumentParser(description="AISApp CLI")
    parser.add_argument('--self-improve', action='store_true', help='Run self improvement watcher and scheduler')
    args = parser.parse_args()

    if args.self_improve:
        print("Starting self-improvement (watcher + periodic)...")
        # Launch file-watcher in a new thread
        watcher_thread = threading.Thread(target=start_self_improvement)
        watcher_thread.daemon = True
        watcher_thread.start()

        # Launch periodic scheduler in the main thread
        from scheduler import periodic_fine_tune
        periodic_fine_tune()
        return

    print("No command specified")


if __name__ == '__main__':
    main()
