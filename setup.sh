#!/usr/bin/env bash
# 開発コンテナを使わずに手元で動かす人向けの準備（macOS / Linux）。
# 必要なツールがそろっているかを確かめ、足りないものの入れ方を表示する。
# そろっていれば uv sync で Python の環境まで作る。
set -u

missing=0

check() {
  # check <コマンド> <入れ方>
  if command -v "$1" >/dev/null 2>&1; then
    printf '  ok   %-10s %s\n' "$1" "$("$1" --version 2>&1 | head -n 1)"
  else
    printf '  なし %-10s 入れ方: %s\n' "$1" "$2"
    missing=1
  fi
}

echo "必要なツールを確かめます"
check uv "curl -LsSf https://astral.sh/uv/install.sh | sh"
check node "https://nodejs.org/ から Node.js 20 以上を入れる"
check agentcore "npm install -g @aws/agentcore@0.30.0"
check aws "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"

if command -v node >/dev/null 2>&1; then
  major=$(node -p 'process.versions.node.split(".")[0]')
  if [ "$major" -lt 20 ]; then
    echo "  Node.js は 20 以上が必要です（今は $(node --version)）"
    missing=1
  fi
fi

if [ "$missing" -ne 0 ]; then
  echo
  echo "足りないツールを入れてから、もう一度 ./setup.sh を実行してください。"
  exit 1
fi

echo
echo "Python の環境を作ります（uv sync）"
uv sync
echo
echo "準備ができました。次は: uv run python shared/setup_all.py"
