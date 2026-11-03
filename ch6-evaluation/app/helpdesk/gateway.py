"""AgentCore Gateway のツールを MCP で使う。

Gateway の URL は、デプロイ時に環境変数で渡される。
Gateway は IAM 認証なので、Runtime の実行ロールで SigV4 署名する。
"""

import os

from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client
from strands.tools.mcp import MCPClient

from resources import REGION

GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_TOOLS_URL")


def gateway_tools() -> list:
    # ローカルで動かすときなど、URL が無ければ Gateway のツールは使わない
    if not GATEWAY_URL:
        return []
    return [
        MCPClient(
            lambda: aws_iam_streamablehttp_client(
                endpoint=GATEWAY_URL,
                aws_region=REGION,
                aws_service="bedrock-agentcore",
            )
        )
    ]
