# 開発コンテナを使わずに手元で動かす人向けの準備（Windows / PowerShell）。
# 必要なツールがそろっているかを確かめ、足りないものの入れ方を表示する。
# そろっていれば uv sync で Python の環境まで作る。

$missing = $false

function Check-Tool($name, $hint) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) {
        $version = (& $name --version 2>&1 | Select-Object -First 1)
        Write-Host ("  ok   {0,-10} {1}" -f $name, $version)
    } else {
        Write-Host ("  なし {0,-10} 入れ方: {1}" -f $name, $hint)
        $script:missing = $true
    }
}

Write-Host "必要なツールを確かめます"
Check-Tool "uv" 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
Check-Tool "node" "https://nodejs.org/ から Node.js 20 以上を入れる"
Check-Tool "agentcore" "npm install -g @aws/agentcore@0.30.0"
Check-Tool "aws" "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"

if (Get-Command node -ErrorAction SilentlyContinue) {
    $major = [int](node -p "process.versions.node.split('.')[0]")
    if ($major -lt 20) {
        Write-Host "  Node.js は 20 以上が必要です（今は $(node --version)）"
        $missing = $true
    }
}

if ($missing) {
    Write-Host ""
    Write-Host "足りないツールを入れてから、もう一度 .\setup.ps1 を実行してください。"
    exit 1
}

Write-Host ""
Write-Host "Python の環境を作ります（uv sync）"
uv sync
Write-Host ""
Write-Host "準備ができました。次は: uv run python shared/setup_all.py"
