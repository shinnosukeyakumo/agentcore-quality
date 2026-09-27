"""質問を Runtime 上のエージェントに流し、答えを記録する。

1 問ごとに新しいセッションで呼ぶ。セッション ID は、
あとで AgentCore Evaluations で採点するときに使う。

  uv run python run_questions.py --label base
  uv run python run_questions.py --label guard --guardrail
"""

import argparse
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parent
REGION = "ap-northeast-1"
STATE = ROOT / "agentcore/.cli/deployed-state.json"


def runtime_arn() -> str:
    state = json.loads(STATE.read_text())
    target = state["targets"]["default"]["resources"]
    return target["runtimes"]["helpdesk"]["runtimeArn"]


def ask(client, arn, q: dict, guardrail: bool) -> dict:
    session_id = str(uuid.uuid4())
    res = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": q["question"],
                            "guardrail": guardrail}),
    )
    body = json.loads(res["response"].read())
    return {**q, "session_id": session_id,
            "guardrail": guardrail, **body}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--label", required=True)
    p.add_argument("--questions",
                   default="eval/questions.jsonl")
    p.add_argument("--guardrail", action="store_true")
    args = p.parse_args()

    lines = (ROOT / args.questions).read_text().splitlines()
    qs = [json.loads(line) for line in lines]
    client = boto3.client("bedrock-agentcore",
                          region_name=REGION)
    arn = runtime_arn()
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(
            lambda q: ask(client, arn, q, args.guardrail), qs))

    out = ROOT / "results" / f"{args.label}.jsonl"
    out.parent.mkdir(exist_ok=True)
    out.write_text("".join(
        json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"wrote {out} ({len(rows)} answers)")


if __name__ == "__main__":
    main()
