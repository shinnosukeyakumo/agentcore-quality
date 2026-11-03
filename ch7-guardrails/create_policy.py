"""勤怠のツールに、本人の記録だけを照会させる policy を作る。

Policy エンジンと Gateway は AgentCore CLI がデプロイで作る。
policy の本文には Gateway の ARN が要るので、デプロイの後に
このスクリプトで ARN を差し込んで作る（ARN をリポジトリに残さない）。
同じ名前の policy があれば、本文を更新する。

  uv run python ch7-guardrails/create_policy.py
"""

import time

from shared.common import APP_DIR, client

ENGINE_NAME = "agentcorequality_helpdesk_policy"
POLICY_NAME = "self_only"
CEDAR = APP_DIR / "agentcore/policies/self_only.cedar"
GATEWAY_NAME = "agentcorequality-tools"


def find(items: list, name: str, key: str) -> str:
    for item in items:
        if item["name"] == name:
            return item[key]
    raise RuntimeError(f"not found: {name}（先にデプロイしてください）")


def main():
    ctl = client("bedrock-agentcore-control")
    gateway = ctl.get_gateway(gatewayIdentifier=find(
        ctl.list_gateways()["items"], GATEWAY_NAME, "gatewayId"))
    engine_id = find(ctl.list_policy_engines()["policyEngines"],
                     ENGINE_NAME, "policyEngineId")
    statement = CEDAR.read_text().replace(
        "{gateway_arn}", gateway["gatewayArn"])
    definition = {"cedar": {"statement": statement}}

    policies = ctl.list_policies(policyEngineId=engine_id)["policies"]
    try:
        policy_id = find(policies, POLICY_NAME, "policyId")
        ctl.update_policy(policyEngineId=engine_id, policyId=policy_id,
                          definition=definition,
                          validationMode="IGNORE_ALL_FINDINGS")
        print(f"updated: {POLICY_NAME}")
    except RuntimeError:
        policy_id = ctl.create_policy(
            policyEngineId=engine_id, name=POLICY_NAME,
            definition=definition,
            validationMode="IGNORE_ALL_FINDINGS")["policyId"]
        print(f"created: {POLICY_NAME}")

    # 作成と更新は非同期。ACTIVE になるまで待つ
    while True:
        policy = ctl.get_policy(policyEngineId=engine_id,
                                policyId=policy_id)
        if policy["status"] not in ("CREATING", "UPDATING"):
            break
        time.sleep(3)
    print(f"status: {policy['status']}")
    if policy["status"] != "ACTIVE":
        raise SystemExit(policy.get("statusReasons"))


if __name__ == "__main__":
    main()
