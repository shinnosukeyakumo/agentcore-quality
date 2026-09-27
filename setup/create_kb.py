"""ヘルプ文書を入れた Managed KB を作る。

S3 バケット → KB 用 IAM ロール → Managed KB → データソース
→ 取り込み、の順に作る。何度実行しても同じ状態になる。
作ったリソースの ID は .state.json に書き出す。
"""

import json
import time

from botocore.exceptions import ClientError
from common import (
    PREFIX,
    REGION,
    ROOT,
    account_id,
    client,
    save_state,
)

ACCOUNT = account_id()
BUCKET = f"{PREFIX}-help-{ACCOUNT}"
ROLE = f"{PREFIX}-kb-role"
KB_NAME = f"{PREFIX}-help"
DS_NAME = f"{PREFIX}-help-s3"

s3 = client("s3")
iam = client("iam")
agent = client("bedrock-agent")


def ensure_bucket():
    try:
        s3.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={
                "LocationConstraint": REGION},
        )
        print(f"created bucket {BUCKET}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        pass
    for path in sorted((ROOT / "help").glob("*.md")):
        s3.upload_file(str(path), BUCKET, f"help/{path.name}")
    print("uploaded help/*.md")


def ensure_role() -> str:
    trust = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {"StringEquals": {
                "aws:SourceAccount": ACCOUNT}},
        }],
    }
    access = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow",
             "Action": "bedrock:InvokeModel",
             "Resource": "*"},
            {"Effect": "Allow",
             "Action": ["s3:GetObject", "s3:ListBucket"],
             "Resource": [f"arn:aws:s3:::{BUCKET}",
                          f"arn:aws:s3:::{BUCKET}/*"]},
        ],
    }
    try:
        arn = iam.create_role(
            RoleName=ROLE,
            AssumeRolePolicyDocument=json.dumps(trust),
        )["Role"]["Arn"]
        print(f"created role {ROLE}")
    except iam.exceptions.EntityAlreadyExistsException:
        arn = iam.get_role(RoleName=ROLE)["Role"]["Arn"]
    iam.put_role_policy(
        RoleName=ROLE, PolicyName="kb-access",
        PolicyDocument=json.dumps(access),
    )
    return arn


def find(items, key, name):
    return next((i for i in items if i["name"] == name), None)


def ensure_kb(role_arn: str) -> str:
    kbs = agent.list_knowledge_bases(maxResults=100)
    kb = find(kbs["knowledgeBaseSummaries"], "name", KB_NAME)
    if not kb:
        # 作ったばかりのロールは IAM の反映待ちで弾かれるので
        # 少し待ってやり直す
        for _ in range(12):
            try:
                kb = agent.create_knowledge_base(
                    name=KB_NAME, roleArn=role_arn,
                    knowledgeBaseConfiguration={
                        "type": "MANAGED",
                        "managedKnowledgeBaseConfiguration": {
                            "embeddingModelType": "MANAGED"},
                    },
                )["knowledgeBase"]
                break
            except ClientError as e:
                if "ValidationException" not in str(e):
                    raise
                print(f"  waiting for IAM: {e}")
                time.sleep(10)
        print(f"created KB {kb['knowledgeBaseId']}")
    kb_id = kb["knowledgeBaseId"]
    wait(lambda: agent.get_knowledge_base(
        knowledgeBaseId=kb_id)["knowledgeBase"]["status"],
        "ACTIVE")
    return kb_id


def ensure_data_source(kb_id: str) -> str:
    dss = agent.list_data_sources(knowledgeBaseId=kb_id)
    ds = find(dss["dataSourceSummaries"], "name", DS_NAME)
    if not ds:
        params = {
            "type": "S3", "version": "1",
            "filterConfiguration": {
                "inclusionPrefixes": ["help/"]},
            "connectionConfiguration": {
                "bucketName": BUCKET,
                "bucketOwnerAccountId": ACCOUNT},
        }
        ds = agent.create_data_source(
            knowledgeBaseId=kb_id, name=DS_NAME,
            dataDeletionPolicy="DELETE",
            dataSourceConfiguration={
                "type": "MANAGED_KNOWLEDGE_BASE_CONNECTOR",
                "managedKnowledgeBaseConnectorConfiguration": {
                    "connectorParameters": params},
            },
        )["dataSource"]
        print(f"created data source {ds['dataSourceId']}")
    ds_id = ds["dataSourceId"]
    wait(lambda: agent.get_data_source(
        knowledgeBaseId=kb_id, dataSourceId=ds_id,
    )["dataSource"]["status"], "AVAILABLE")
    return ds_id


def ingest(kb_id: str, ds_id: str):
    job_id = agent.start_ingestion_job(
        knowledgeBaseId=kb_id, dataSourceId=ds_id,
    )["ingestionJob"]["ingestionJobId"]
    job = wait(lambda: agent.get_ingestion_job(
        knowledgeBaseId=kb_id, dataSourceId=ds_id,
        ingestionJobId=job_id)["ingestionJob"],
        ("COMPLETE", "FAILED", "STOPPED"), key="status")
    print(f"ingestion {job['status']}: {job.get('statistics')}")
    if job["status"] != "COMPLETE":
        raise SystemExit(job.get("failureReasons"))


def wait(get, done, key=None, tries=120):
    done = done if isinstance(done, tuple) else (done,)
    for _ in range(tries):
        value = get()
        status = value[key] if key else value
        if status in done:
            return value
        if status in ("FAILED", "DELETE_UNSUCCESSFUL"):
            raise SystemExit(f"status {status}")
        time.sleep(5)
    raise SystemExit(f"timeout waiting for {done}")


if __name__ == "__main__":
    ensure_bucket()
    role_arn = ensure_role()
    kb_id = ensure_kb(role_arn)
    ds_id = ensure_data_source(kb_id)
    ingest(kb_id, ds_id)
    save_state(region=REGION, bucket=BUCKET, role=ROLE,
               kb_id=kb_id, ds_id=ds_id)
    print("done. wrote .state.json")
