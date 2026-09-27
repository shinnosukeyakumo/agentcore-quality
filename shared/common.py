"""各章のスクリプトが共通で使う設定と記録。"""

import json
import os
from pathlib import Path

import boto3

REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
ROOT = Path(__file__).resolve().parent.parent
PREFIX = "agentcore-quality"

APP_DIR = ROOT / "01-quality-app"
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
