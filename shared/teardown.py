"""サンプルで作った AWS のリソースを、まとめて消す。

各章のスクリプトで作ったもの（オンライン評価、評価器、
Guardrail、KB、S3、IAM ロール）を消してから、
AgentCore CLI で Runtime とその実行ロールを消す。

  uv run python shared/teardown.py
"""

import runpy

from shared.common import ROOT
from shared.setup_all import agentcore


def main():
    print("[1/2] 評価器・Guardrail・KB などを消す", flush=True)
    runpy.run_path(str(ROOT / "shared/cleanup.py"),
                   run_name="__main__")
    print("\n[2/2] Runtime を消す", flush=True)
    agentcore("remove", "all", "-y")
    agentcore("deploy", "-y")
    print("\n片付けが終わりました。")


if __name__ == "__main__":
    main()
