"""社内ヘルプデスクの問い合わせチャット。"""

from datetime import datetime
from zoneinfo import ZoneInfo

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models.bedrock import BedrockModel

from gateway import gateway_tools
from resources import REGION, guardrail
from search import search_manual

MODEL_ID = "jp.anthropic.claude-sonnet-4-6"

SYSTEM_PROMPT = """\
あなたは社内ヘルプデスクの担当者です。
社員からの、勤怠システムの使い方に関する質問に答えます。

- 答える前に、必ず search_manual でマニュアルを検索する
- マニュアルに書かれていることだけを根拠に答える
- マニュアルに記載が無いことは推測で答えない。
  「マニュアルに記載がありません」と伝え、
  人事部の勤怠担当者に問い合わせるよう案内する
- 答えの最後に、根拠にしたマニュアルのファイル名を
  「出典：」として付ける
- 質問者の社員番号は E0001 です。質問者自身の勤怠の記録
  （残業時間、有給休暇の残りなど）を聞かれたら、
  get_attendance で調べて答える。出典は「勤怠の記録」とする
"""

app = BedrockAgentCoreApp()


def build_model(use_guardrail: bool) -> BedrockModel:
    options = {}
    if use_guardrail:
        gid, version = guardrail()
        options = {"guardrail_id": gid,
                   "guardrail_version": version}
    return BedrockModel(
        model_id=MODEL_ID, region_name=REGION,
        temperature=0, **options)


def today() -> str:
    return datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")


def tool_calls(messages: list) -> list[dict]:
    """呼んだツールと引数、結果の成否。Policy の確かめに使う。"""
    calls, status = [], {}
    for message in messages:
        for block in message["content"]:
            if "toolUse" in block:
                calls.append(block["toolUse"])
            if "toolResult" in block:
                result = block["toolResult"]
                status[result["toolUseId"]] = result["status"]
    return [{"name": c["name"], "input": c["input"],
             "status": status.get(c["toolUseId"])} for c in calls]


@app.entrypoint
def invoke(payload: dict) -> dict:
    agent = Agent(
        model=build_model(payload.get("guardrail", False)),
        # 「今月」「10月」が何年のことか分かるように、今日の日付を渡す
        system_prompt=SYSTEM_PROMPT + f"\n今日は {today()} です。\n",
        tools=[search_manual, *gateway_tools()],
        callback_handler=None,
    )
    result = agent(payload["prompt"])
    return {"answer": str(result),
            "stop_reason": result.stop_reason,
            "tool_calls": tool_calls(agent.messages)}


if __name__ == "__main__":
    app.run()
