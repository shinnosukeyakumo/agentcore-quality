"""run_questions.py の結果を AgentCore Evaluations で採点する。

同じ答えを --passes 回採点して平均を取る（判定が揺れるため）。
結果は質問の種類（category）ごとに集計して表示する。

  uv run python 02-evaluation/score.py --label base --passes 3
"""

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean

from bedrock_agentcore.evaluation import (
    EvaluationClient,
    ReferenceInputs,
)

from shared.common import REGION, ROOT, load_state, runtime

HERE = Path(__file__).resolve().parent
BUILTIN = ["Builtin.Correctness", "Builtin.Refusal",
           "Builtin.Faithfulness"]


def score(client, aid, evaluators, row) -> list[dict]:
    results = client.run(
        evaluator_ids=evaluators,
        agent_id=aid,
        session_id=row["session_id"],
        reference_inputs=ReferenceInputs(
            expected_response=row["expected_response"]),
    )
    return [{"id": row["id"],
             "category": row["category"],
             "evaluator": r.get("evaluatorName")
             or r.get("evaluatorId"),
             "value": r.get("value"),
             "label": r.get("label"),
             "explanation": r.get("explanation"),
             "error": r.get("errorMessage")}
            for r in results]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--label", required=True)
    p.add_argument("--passes", type=int, default=3)
    p.add_argument("--results-dir",
                   default=HERE / "results")
    args = p.parse_args()

    results_dir = ROOT / args.results_dir
    src = results_dir / f"{args.label}.jsonl"
    rows = [json.loads(x) for x in src.read_text().splitlines()]
    client = EvaluationClient(region_name=REGION)
    aid = runtime()["runtimeId"]
    evaluators = BUILTIN + [load_state()["evaluator_id"]]

    jobs = [(n, r) for n in range(args.passes) for r in rows]
    with ThreadPoolExecutor(max_workers=8) as pool:
        out = list(pool.map(
            lambda j: [{**s, "pass": j[0]} for s in
                       score(client, aid, evaluators, j[1])],
            jobs))
    scores = [s for batch in out for s in batch]

    dst = results_dir / f"{args.label}-scores.jsonl"
    dst.write_text("".join(
        json.dumps(s, ensure_ascii=False) + "\n"
        for s in scores))
    print(f"wrote {dst} ({len(scores)} scores)")

    table = defaultdict(list)
    for s in scores:
        if s["value"] is not None:
            table[(s["evaluator"], s["category"])].append(
                s["value"])
            table[(s["evaluator"], "all")].append(s["value"])
    cats = ["straightforward", "tricky", "unanswerable", "all"]
    print("evaluator".ljust(28) + "".join(
        c[:8].rjust(10) for c in cats))
    for ev in sorted({k[0] for k in table}):
        cells = [table.get((ev, c)) for c in cats]
        print(ev[:28].ljust(28) + "".join(
            f"{mean(v):10.2f}" if v else "       -  "
            for v in cells))


if __name__ == "__main__":
    main()
