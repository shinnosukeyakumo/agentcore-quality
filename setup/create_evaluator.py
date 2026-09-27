"""自作の根拠チェック評価器を登録する。

回答に含まれる事実が、すべて検索結果に書かれているかを
LLM に判定させる（LLM-as-a-judge）。判定のぶれを抑える
ため temperature は 0 にする。
"""

from common import ROOT, client, load_state, save_state

NAME = "grounded_check"
JUDGE_MODEL = "jp.anthropic.claude-sonnet-4-6"

control = client("bedrock-agentcore-control")

SCALE = [
    {"value": 1.0, "label": "根拠あり",
     "definition": "回答の事実はすべて検索結果に書かれている"},
    {"value": 0.5, "label": "一部に根拠なし",
     "definition": "検索結果に無い事実が一部に含まれる"},
    {"value": 0.0, "label": "根拠なし",
     "definition": "回答の主な事実が検索結果に書かれていない"},
]


def config() -> dict:
    path = ROOT / "eval" / "grounded_check.txt"
    instructions = path.read_text()
    return {"llmAsAJudge": {
        "instructions": instructions,
        "ratingScale": {"numerical": SCALE},
        "modelConfig": {"bedrockEvaluatorModelConfig": {
            "modelId": JUDGE_MODEL,
            "inferenceConfig": {"temperature": 0.0,
                                "maxTokens": 1024},
        }},
    }}


def ensure_evaluator() -> str:
    found = next(
        (e for e in control.list_evaluators()["evaluators"]
         if e.get("evaluatorName") == NAME), None)
    if found:
        # オンライン評価で使っている間は更新できない（ロックされる）
        # ので、すでにあれば何もしない
        print(f"exists: {found['evaluatorId']}")
        return found["evaluatorId"]
    eid = control.create_evaluator(
        evaluatorName=NAME, level="TRACE",
        description="回答の事実が検索結果に書かれているか",
        evaluatorConfig=config(),
    )["evaluatorId"]
    print(f"created evaluator {eid}")
    return eid


if __name__ == "__main__":
    load_state()
    save_state(evaluator_id=ensure_evaluator())
    print("done. wrote .state.json")
