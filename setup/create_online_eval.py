"""本番の会話を採点し続けるオンライン評価を設定する。

本番の質問には正解が無いので、正解を使わない評価器
（自作の根拠チェックと Builtin.Refusal）だけを回す。
サンプルでは動きを確かめやすいよう、全セッションを採点する。
"""

import json
import time

from common import (
    PREFIX,
    REGION,
    ROOT,
    account_id,
    client,
    load_state,
    save_state,
)

NAME = "helpdesk_online"
ROLE = f"{PREFIX}-online-eval-role"
SAMPLING_PERCENT = 100.0

iam = client("iam")
control = client("bedrock-agentcore-control")


def runtime_id() -> str:
    path = ROOT / "agentcore/.cli/deployed-state.json"
    target = json.loads(path.read_text())["targets"]["default"]
    return target["resources"]["runtimes"]["helpdesk"]["runtimeId"]


def ensure_role(log_group: str) -> str:
    acct = account_id()
    logs = f"arn:aws:logs:{REGION}:{acct}:log-group"
    spans = f"{logs}:aws/spans"
    results = f"{logs}:/aws/bedrock-agentcore/evaluations/*"
    trust = {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
        "Action": "sts:AssumeRole",
        "Condition": {"StringEquals": {"aws:SourceAccount": acct}},
    }]}
    read = ["logs:StartQuery", "logs:GetQueryResults",
            "logs:GetLogEvents", "logs:DescribeLogStreams",
            "logs:FilterLogEvents"]
    policy = {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": "logs:DescribeLogGroups",
         "Resource": "*"},
        # エージェントのログとスパンを読む
        {"Effect": "Allow", "Action": read,
         "Resource": [f"{logs}:{log_group}*", f"{spans}*"]},
        {"Effect": "Allow",
         "Action": ["logs:PutIndexPolicy",
                    "logs:DescribeIndexPolicies"],
         "Resource": spans},
        # 採点結果を書き出す
        {"Effect": "Allow",
         "Action": ["logs:CreateLogGroup", "logs:CreateLogStream",
                    "logs:PutLogEvents", "logs:DescribeLogStreams"],
         "Resource": results},
        # 自作の評価器が判定モデルを呼ぶ
        {"Effect": "Allow",
         "Action": ["bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"],
         "Resource": [
             "arn:aws:bedrock:*::foundation-model/*",
             f"arn:aws:bedrock:*:{acct}:inference-profile/*"]},
    ]}
    try:
        arn = iam.create_role(
            RoleName=ROLE,
            AssumeRolePolicyDocument=json.dumps(trust),
        )["Role"]["Arn"]
        print(f"created role {ROLE}")
        time.sleep(10)  # IAM の反映を待つ
    except iam.exceptions.EntityAlreadyExistsException:
        arn = iam.get_role(RoleName=ROLE)["Role"]["Arn"]
    iam.put_role_policy(RoleName=ROLE, PolicyName="online-eval",
                        PolicyDocument=json.dumps(policy))
    return arn


def create_with_retry(**kwargs) -> dict:
    # 付けたばかりの権限は IAM の反映待ちで弾かれるので、
    # 少し待ってやり直す
    for _ in range(12):
        try:
            return control.create_online_evaluation_config(
                **kwargs)
        except control.exceptions.ValidationException as e:
            if "permissions" not in str(e):
                raise
            print(f"  waiting for IAM: {e}")
            time.sleep(10)
    raise SystemExit("timeout waiting for IAM")


def main():
    state = load_state()
    rid = runtime_id()
    log_group = f"/aws/bedrock-agentcore/runtimes/{rid}-DEFAULT"
    service = "agentcorequality_helpdesk.DEFAULT"
    role_arn = ensure_role(log_group)
    found = next(
        (c for c in control.list_online_evaluation_configs()
         ["onlineEvaluationConfigs"]
         if c["onlineEvaluationConfigName"] == NAME), None)
    if found:
        print(f"exists: {found['onlineEvaluationConfigId']}")
        return
    cfg = create_with_retry(
        onlineEvaluationConfigName=NAME,
        rule={"samplingConfig": {
                  "samplingPercentage": SAMPLING_PERCENT},
              "sessionConfig": {"sessionTimeoutMinutes": 5}},
        dataSourceConfig={"cloudWatchLogs": {
            "logGroupNames": [log_group],
            "serviceNames": [service]}},
        evaluators=[{"evaluatorId": state["evaluator_id"]},
                    {"evaluatorId": "Builtin.Refusal"}],
        evaluationExecutionRoleArn=role_arn,
        enableOnCreate=True,
    )
    cid = cfg["onlineEvaluationConfigId"]
    save_state(online_eval_id=cid)
    print(f"created online evaluation {cid}")


if __name__ == "__main__":
    main()
