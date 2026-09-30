"""ゴールデン QA セットで採点するまでを、まとめて行う。

自作の評価器を登録し、30 問をエージェントに流し、
トレースが届くのを待ってから、3 回採点して集計する。

  uv run python ch6-evaluation/offline/evaluate.py
"""

from shared.common import run, wait_for_traces

HERE = "ch6-evaluation/offline"


def main():
    run(f"{HERE}/create_evaluator.py")
    run(f"{HERE}/run_questions.py", "--label", "base")
    wait_for_traces()
    run(f"{HERE}/score.py", "--label", "base", "--passes", "3")


if __name__ == "__main__":
    main()
