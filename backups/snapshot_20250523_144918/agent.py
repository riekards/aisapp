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
        """Return the list of requested features."""
        return self.memory.list_features()

    def handle(self, text):
        text = text.strip()
        self.memory.save_message("user", text)

        # Detect feature requests
        if text.lower().startswith("i want you to implement") or text.lower().startswith("please implement"):
            self.memory.save_feature(text)
            return f"Feature request received: '{text}'. I will include this in the next self-improve cycle."

        # Self-improve trigger
        if text.lower() == "self improve":
            success = self.improver.run_cycle()
            return ("Self-improvement successful." if success
                    else "Self-improvement failed; rolled back.")

        # Normal chat
        response = self.ask_llm(text)
        self.memory.save_message("ai", response)
        return response

    def ask_llm(self, prompt):
        # 1) Read in all your existing Python code under app/ as context
        code_context = []
        for dirpath, _, files in os.walk('app'):
            for fname in files:
                if fname.endswith('.py'):
                    path = os.path.join(dirpath, fname)
                    try:
                        with open(path, 'r', encoding='utf-8') as cf:
                            content = cf.read()
                        code_context.append(f"### BEGIN {path}\n{content}\n### END {path}\n")
                    except Exception:
                        continue

        # 2) Build the full prompt with code context and pending features
        full_prompt = "".join(code_context) + "\n" + prompt
        features = self.get_features()
        if features:
            feature_text = "\nImplement these features:\n" + "\n".join(f"- {f}" for f in features)
            full_prompt += feature_text

        # 3) Call the LLM
        payload = {"model": "mistral", "messages": [{"role": "user", "content": full_prompt}]}
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True)
        r.raise_for_status()

        # 4) Stream-assemble the response
        collected = []
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                part = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = part.get('message', {})
            content = msg.get('content')
            done = part.get('done', False)
            if content:
                collected.append(content)
            if done:
                break

        return "".join(collected) if collected else r.text.strip()
