"""Guardrail を付けたときの効き目と止めすぎを、まとめて測る。

ゴールデン QA セットと攻撃用の質問を Guardrail ありで流し、
止めた割合と止めすぎた割合を数え、採点もする。

  uv run python ch3-guardrails/compare.py
"""

from shared.common import run, wait_for_traces

HERE = "ch3-guardrails"
RUNNER = "ch2-evaluation/offline/run_questions.py"
RESULTS = ["--results-dir", f"{HERE}/results"]


def main():
    run(RUNNER, "--label", "guard", "--guardrail", *RESULTS)
    run(RUNNER, "--label", "attacks-guard", "--guardrail",
        "--questions", f"{HERE}/attacks.jsonl", *RESULTS)
    run(f"{HERE}/count_guard.py",
        "--attacks", "attacks-guard", "--normal", "guard")
    wait_for_traces()
    run("ch2-evaluation/offline/score.py", "--label", "guard",
        "--passes", "1", *RESULTS)


if __name__ == "__main__":
    main()
