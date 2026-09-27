"""setup/ で作ったリソースを消す。

Runtime とその実行ロールは AgentCore CLI で消す
（README の「片付け」を参照）。このスクリプトは
オンライン評価、評価器、Guardrail、KB、S3、IAM ロールを消す。
"""

import time

from shared.common import PREFIX, client, load_state

control = client("bedrock-agentcore-control")
bedrock = client("bedrock")
agent = client("bedrock-agent")
s3 = client("s3")
iam = client("iam")


def safe(label, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        print(f"deleted {label}")
    except Exception as e:  # noqa: BLE001
        print(f"skip {label}: {type(e).__name__}")


def delete_role(name: str):
    try:
        names = iam.list_role_policies(RoleName=name)["PolicyNames"]
        for p in names:
            iam.delete_role_policy(RoleName=name, PolicyName=p)
    except iam.exceptions.NoSuchEntityException:
        return
    safe(f"role {name}", iam.delete_role, RoleName=name)


def main():
    st = load_state()
    # 評価器はオンライン評価で使われている間は消せないので先に消す
    if "online_eval_id" in st:
        safe("online evaluation",
             control.delete_online_evaluation_config,
             onlineEvaluationConfigId=st["online_eval_id"])
        time.sleep(10)
    if "evaluator_id" in st:
        safe("evaluator", control.delete_evaluator,
             evaluatorId=st["evaluator_id"])
    if "guardrail_id" in st:
        safe("guardrail", bedrock.delete_guardrail,
             guardrailIdentifier=st["guardrail_id"])
    if "kb_id" in st:
        safe("data source", agent.delete_data_source,
             knowledgeBaseId=st["kb_id"], dataSourceId=st["ds_id"])
        time.sleep(10)
        safe("knowledge base", agent.delete_knowledge_base,
             knowledgeBaseId=st["kb_id"])
    if "bucket" in st:
        objs = s3.list_objects_v2(Bucket=st["bucket"])
        for o in objs.get("Contents", []):
            s3.delete_object(Bucket=st["bucket"], Key=o["Key"])
        safe(f"bucket {st['bucket']}", s3.delete_bucket,
             Bucket=st["bucket"])
    delete_role(f"{PREFIX}-kb-role")
    delete_role(f"{PREFIX}-online-eval-role")


if __name__ == "__main__":
    main()
