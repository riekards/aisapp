import os
import requests
import json
from app.memory import Memory
from app.snapshot import SnapshotManager
from app.self_improve import SelfImproveEngine

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

class Agent:
    def __init__(self):
        self.memory = Memory("memory.db")
        self.snapshot = SnapshotManager("app", "backups")
        self.improver = SelfImproveEngine(self, test_cmd="pytest")

    def get_features(self):
        """Return the list of requested features from memory."""
        return self.memory.list_features()

    def handle(self, text):
        # store user message
        self.memory.save_message("user", text)

        # self-improve trigger
        if text.lower() == "self improve":
            success = self.improver.run_cycle()
            return ("Self-improvement successful." if success
                    else "Self-improvement failed; rolled back.")

        # normal chat
        response = self.ask_llm(text)
        self.memory.save_message("ai", response)
        return response

    def ask_llm(self, prompt):
        """
        Call Ollama's streaming API, collect JSON lines, and concatenate assistant content.
        """
        payload = {
            "model": "mistral",
            "messages": [{"role": "user", "content": prompt}]
        }
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True)
        r.raise_for_status()

        collected = []
        # each line is a JSON object
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                part = json.loads(line)
            except json.JSONDecodeError:
                continue
            # streaming format: part['message']['content']
            msg = part.get('message', {})
            content = msg.get('content')
            done = part.get('done', False)
            if content:
                collected.append(content)
            if done:
                break

        if not collected:
            # fallback to raw text
            return r.text.strip()
        return ''.join(collected)
