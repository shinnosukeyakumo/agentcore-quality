"""社内ヘルプデスクの問い合わせチャット。"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models.bedrock import BedrockModel

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


@app.entrypoint
def invoke(payload: dict) -> dict:
    agent = Agent(
        model=build_model(payload.get("guardrail", False)),
        system_prompt=SYSTEM_PROMPT,
        tools=[search_manual],
        callback_handler=None,
    )
    result = agent(payload["prompt"])
    return {"answer": str(result),
            "stop_reason": result.stop_reason}


if __name__ == "__main__":
    app.run()
