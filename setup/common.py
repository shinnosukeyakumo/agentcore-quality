"""リージョンと、setup が作ったリソース ID の読み書き。"""

import json
import os
from pathlib import Path

import boto3

REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".state.json"
PREFIX = "agentcore-quality"


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
