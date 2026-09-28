#!/usr/bin/env bash
# 開発コンテナを作ったときに一度だけ実行する準備。
set -euo pipefail

# ボリュームは root 所有で作られるので、作業ユーザーに渡す
sudo chown -R "$(id -u):$(id -g)" \
  01-quality-app/agentcore/cdk/node_modules

# uv（Python のパッケージ管理ツール）
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# AgentCore CLI（本書で確かめた版に固定する）
npm install -g @aws/agentcore@0.30.0

# Python の環境
uv sync

# デプロイに使う CDK の依存パッケージ
(cd 01-quality-app/agentcore/cdk && npm ci)

echo
echo "準備ができました。AWS の認証情報を用意してから、"
echo "uv run python shared/setup_all.py を実行してください。"
