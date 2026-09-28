"""質問を Runtime 上のエージェントに流し、答えを記録する。

1 問ごとに新しいセッションで呼ぶ。セッション ID は、
あとで AgentCore Evaluations で採点するときに使う。

答えは --results-dir（既定は ch2-evaluation/offline/results）に
<label>.jsonl として書き出す。

  uv run python ch2-evaluation/offline/run_questions.py --label base
"""

import argparse
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from shared.common import ROOT, client, runtime

HERE = Path(__file__).resolve().parent


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
                   default=HERE / "questions.jsonl")
    p.add_argument("--results-dir",
                   default=HERE / "results")
    p.add_argument("--guardrail", action="store_true")
    args = p.parse_args()

    lines = (ROOT / args.questions).read_text().splitlines()
    qs = [json.loads(line) for line in lines]
    agentcore = client("bedrock-agentcore")
    arn = runtime()["runtimeArn"]
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(
            lambda q: ask(agentcore, arn, q, args.guardrail),
            qs))

    out = ROOT / args.results_dir / f"{args.label}.jsonl"
    out.parent.mkdir(exist_ok=True)
    out.write_text("".join(
        json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"wrote {out} ({len(rows)} answers)")


if __name__ == "__main__":
    main()
