"""マニュアルを検索するツール。"""

from pathlib import PurePosixPath

import boto3
from strands import tool

from resources import REGION, knowledge_base_id

kb = boto3.client("bedrock-agent-runtime", region_name=REGION)


@tool
def search_manual(query: str) -> str:
    """勤怠システムの使い方マニュアルを検索する。

    Args:
        query: 調べたい内容。単語を並べず、文で書く
            （例：新画面で出勤を打刻する方法）
    """
    res = kb.retrieve(
        knowledgeBaseId=knowledge_base_id(),
        retrievalQuery={"text": query},
    )
    parts = []
    for r in res["retrievalResults"]:
        # 出典はファイル名だけにする（S3 の URL は載せない）
        uri = r["location"]["s3Location"]["uri"]
        name = PurePosixPath(uri).name
        parts.append(f"[{name}]\n{r['content']['text']}")
    return "\n\n".join(parts) or "該当する記載はありません。"
