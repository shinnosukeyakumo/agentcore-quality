"""オンライン評価を設定し、本番に見立てた質問を流す。

採点結果は、会話が終わってから 15 分ほどで CloudWatch Logs の
/aws/bedrock-agentcore/evaluations/results/<設定 ID> に出る。

  uv run python ch6-evaluation/online/start.py
"""

from shared.common import run

HERE = "ch6-evaluation/online"


def main():
    run(f"{HERE}/create_online_eval.py")
    run("ch6-evaluation/offline/run_questions.py",
        "--label", "live", "--questions", f"{HERE}/live.jsonl",
        "--results-dir", f"{HERE}/results")
    print("\n採点結果は 15 分ほどで CloudWatch Logs に出ます。")


if __name__ == "__main__":
    main()
