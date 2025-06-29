import os
import requests
import json
from app.memory import Memory
from app.snapshot import SnapshotManager
from app.self_improve import SelfImproveEngine
from app.self_improve_env import SelfImproveEnv
from stable_baselines3 import PPO
from stable_baselines3.common.utils import check_for_correct_spaces

MODEL_PATH = "ppo_self_improve.zip"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

class Agent:
    def __init__(self, use_real_llm: bool = False, test_cmd: str = "pytest"):
        self.use_real_llm = use_real_llm
        if not self.use_real_llm:
            def stub_ask_llm(prompt: str) -> str:
                return (
                    "diff --git a/app/__init__.py b/app/__init__.py\n"
                    "index e69de29..e69de29 100644\n"
                    "--- a/app/__init__.py\n"
                    "+++ b/app/__init__.py\n"
                    "@@ -0,0 +1 @@\n"
                    " # no-op patch (stub)\n"
                )
            self.ask_llm = stub_ask_llm
        self.memory = Memory("memory.db")
        self.snapshot = SnapshotManager("app", "backups")
        from app.self_improve import SelfImproveEngine
        self.improver = SelfImproveEngine(self, use_real_llm=use_real_llm, test_cmd=test_cmd)
        self.rl_env = SelfImproveEnv(self, use_real_llm=True, max_steps=50)
        self.policy = None
        if os.path.isfile("ppo_self_improve.zip"):
            try:
                candidate = PPO.load("ppo_self_improve.zip", env=self.rl_env)
                check_for_correct_spaces(self.rl_env, candidate.observation_space, candidate.action_space)
                self.policy = candidate
                print("[Agent] Loaded existing PPO policy.")
            except Exception as e:
                print(f"[Agent] Failed to load old PPO policy {e}, starting new training.")
        self.rl_model = None
        path = os.path.join(os.getcwd(), MODEL_PATH)
        if os.path.isfile(path):
            self.rl_model = PPO.load(path)
        else:
            self.rl_model = None

    def get_features(self):
        session = self.memory.Session()
        rows = session.query(self.memory.features).all()
        session.close()
        return [(r.id, r.description) for r in rows]
    
    def delete_feature(self, feature_id):
        """Called by the GUI to remove a stored feature."""
        self.memory.delete_feature(feature_id)


    def handle(self, text):
        text = text.strip()
        self.memory.save_message("user", text)

        # —— RL policy picks a temperature before any action —— #
        obs, _ = self.rl_env.reset()  # get fresh obs [last_reward, pending]
        if self.policy is not None:
            action, _ = self.policy.predict(obs, deterministic=False)
            self.temperature = float(action[0])
            print(f"[RL] Chosen temperature: {self.temperature:.3f}")
        else:
            self.temperature = 0.5

        # —— now your existing logic —— #
        # Detect feature requests
        if text.lower().startswith("i want you to implement") \
           or text.lower().startswith("please implement"):
            self.memory.save_feature(text)
            return (f"Feature request received: '{text}'. "
                    "I will include this in the next self-improve cycle.")

        # Self-improve trigger
        if text.lower() == "self improve":
            result = self.improver.run_cycle()
            if self.rl_model is not None:
                obs = [getattr(self, "last_reward", 0),
                       len(self.memory.list_features())]
                action, _ = self.rl_model.predict(obs, deterministic=True)
                self.temperature = float(action[0])
            result = self.improver.run_cycle()
            return (
                "Self-improvement successful." if result in ("success", "partial")
                else "Self-improvement failed; rolled back."
            )

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
        try:
            r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True)
            r.raise_for_status()
        except Exception:
            if not self.use_real_llm:
                return "*** Begin patch \n*** End patch\n"
            raise

        # 4) Stream-assemble the response, handling different signatures of iter_lines()
        collected = []
        try:
            lines = r.iter_lines(decode_unicode=True)
        except TypeError:
            try:
                # some mocks expect a single positional argument
                lines = r.iter_lines(True)
            except TypeError:
                lines = r.iter_lines()
        for line in lines:
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
