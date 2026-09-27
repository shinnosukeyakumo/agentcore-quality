"""KB と Guardrail の ID を名前から引き当てる。

ID をコードや設定に書かないので、読者は setup を
実行するだけで同じ名前のリソースに接続できる。
"""

import os
from functools import cache

import boto3

REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
KB_NAME = os.environ.get("KB_NAME", "agentcore-quality-help")
GUARDRAIL_NAME = os.environ.get(
    "GUARDRAIL_NAME", "agentcore-quality-guardrail")


@cache
def knowledge_base_id() -> str:
    agent = boto3.client("bedrock-agent", region_name=REGION)
    kbs = agent.list_knowledge_bases(maxResults=100)
    for kb in kbs["knowledgeBaseSummaries"]:
        if kb["name"] == KB_NAME:
            return kb["knowledgeBaseId"]
    raise RuntimeError(f"knowledge base not found: {KB_NAME}")


@cache
def guardrail() -> tuple[str, str]:
    """(ID, 最新の公開バージョン) を返す。"""
    bedrock = boto3.client("bedrock", region_name=REGION)
    for g in bedrock.list_guardrails()["guardrails"]:
        if g["name"] == GUARDRAIL_NAME:
            versions = bedrock.list_guardrails(
                guardrailIdentifier=g["id"])["guardrails"]
            latest = max(int(v["version"]) for v in versions
                         if v["version"] != "DRAFT")
            return g["id"], str(latest)
    raise RuntimeError(f"guardrail not found: {GUARDRAIL_NAME}")
