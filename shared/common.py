"""各章のスクリプトが共通で使う設定と記録。"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import boto3

REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
ROOT = Path(__file__).resolve().parent.parent
PREFIX = "agentcore-quality"

APP_DIR = ROOT / "ch2-evaluation/app"
# setup スクリプトが作ったリソースの ID（アカウント ID を含む）
STATE = ROOT / ".state.json"
# AgentCore CLI が書き出すデプロイ結果（ARN を含む）
DEPLOYED = APP_DIR / "agentcore/.cli/deployed-state.json"


def client(name: str):
    return boto3.client(name, region_name=REGION)


def account_id() -> str:
    return client("sts").get_caller_identity()["Account"]


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {}


def save_state(**kv) -> dict:
    state = load_state() | kv
    STATE.write_text(json.dumps(state, indent=2))
    return state


def runtime() -> dict:
    """デプロイ済みの Runtime の ID と ARN。"""
    target = json.loads(DEPLOYED.read_text())["targets"]
    resources = target["default"]["resources"]
    return resources["runtimes"]["helpdesk"]


def run(script: str, *args: str):
    """リポジトリのいちばん上から Python のスクリプトを実行する。"""
    print(f"\n$ uv run python {script} {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, script, *args], cwd=ROOT,
                   check=True)


def wait_for_traces(minutes: int = 5):
    """トレースが CloudWatch に届くのを待つ。"""
    print(f"\nトレースが CloudWatch に届くのを {minutes} 分待ちます",
          flush=True)
    for left in range(minutes, 0, -1):
        print(f"  あと {left} 分", flush=True)
        time.sleep(60)
