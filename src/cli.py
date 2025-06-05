import argparse
import threading
from agent import Agent
from trainer import Trainer
from self_improve import start_self_improvement


def main():
    parser = argparse.ArgumentParser(description="Local AI Assistant CLI")
    parser.add_argument(
        "--train",
        action="store_true",
        help="Fine-tune the model on memory buffer (once)"
    )
    parser.add_argument(
        "--self-improve",
        action="store_true",
        help="Launch continuous self-improvement (watch memory_store/)"
    )
    args = parser.parse_args()

    if args.self_improve:
        # Start self-improvement watcher (blocking)
        print("Starting self-improvement watcher...")
        start_self_improvement()
        return

    agent = Agent()
    trainer = Trainer()

    if args.train:
        print("Starting one-time fine-tuning...")
        trainer.fine_tune()
        return

    print("Welcome to your Local AI Assistant. Type 'exit' to quit.")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            agent.save_memory()
            print("Goodbye!")
            break
        response = agent.respond(user_input)
        print("AI:", response)


if __name__ == "__main__":
    main()
