"""題材のアプリを動かすところまでを、まとめて準備する。

KB と Guardrail を作り、デプロイ先の設定を書き、
AgentCore Runtime にデプロイして、1 問だけ試しに聞く。
途中で失敗しても、もう一度流せば続きから進む
（作成済みのリソースは作り直さない）。

  uv run python shared/setup_all.py
"""

import json
import runpy
import shutil
import subprocess
import sys

from shared.common import APP_DIR, REGION, ROOT, account_id

TARGETS = APP_DIR / "agentcore" / "aws-targets.json"
QUESTION = "打刻の時刻を間違えました。自分で直せますか？"


def step(n: int, title: str):
    print(f"\n[{n}/5] {title}", flush=True)


def agentcore(*args: str):
    """ch6-evaluation/app で AgentCore CLI を実行する。"""
    exe = shutil.which("agentcore")
    if exe is None:
        sys.exit("agentcore が見つかりません。"
                 "npm install -g @aws/agentcore@0.30.0 "
                 "で入れてください。")
    subprocess.run([exe, *args], cwd=APP_DIR, check=True)


def write_targets():
    """デプロイ先（アカウントとリージョン）を書き出す。"""
    want = [{"name": "default", "account": account_id(),
             "region": REGION}]
    if TARGETS.exists() and json.loads(TARGETS.read_text()) == want:
        print("exists: aws-targets.json")
        return
    TARGETS.write_text(json.dumps(want, indent=2) + "\n")
    print(f"wrote {TARGETS.relative_to(ROOT)}")


def main():
    step(1, "Managed KB を作る")
    runpy.run_path(str(APP_DIR / "create_kb.py"),
                   run_name="__main__")
    step(2, "Guardrail を作る")
    runpy.run_path(str(ROOT / "ch7-guardrails/create_guardrail.py"),
                   run_name="__main__")
    step(3, "デプロイ先を書き出す")
    write_targets()
    step(4, "エージェントを Runtime にデプロイする")
    agentcore("deploy", "-y")
    step(5, "動作を確かめる")
    agentcore("invoke", QUESTION)
    print("\nセットアップが終わりました。")


if __name__ == "__main__":
    main()
