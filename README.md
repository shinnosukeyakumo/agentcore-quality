# agentcore-quality

技術書典21で頒布する合同誌『AWSではじめるAIエージェントプロダクト開発』（書名は仮）の第2部「AIエージェントの評価とガードレール」のサンプルコードです。

本文と同じ状態のコードは、タグ `tbf21-v1.0` を参照してください（入稿時に付与します）。

## フォルダと本の章の対応

| フォルダ | 本の章 | 中身 |
|---|---|---|
| `01-quality-app/` | 第2部の1つめの章（AIエージェントの品質） | 題材の問い合わせチャット。エージェント、Runtime へのデプロイ設定、マニュアル、KB を作るスクリプト |
| `02-evaluation/` | 第2部の2つめの章（AIエージェントの評価） | ゴールデン QA セット、自作の根拠チェック、質問を流して採点するスクリプトと結果 |
| `03-guardrails/` | 第2部の3つめの章（ガードレール） | Guardrail の設定、攻撃用の質問、止めた割合と止めすぎを数えるスクリプトと結果 |
| `04-online-evaluation/` | 第2部の4つめの章（本番運用での評価） | オンライン評価の設定と結果 |
| `shared/` | ― | 各章のスクリプトが共通で使う設定と、片付けのスクリプト |

手順と実行の順番は、このあとの「動かし方」にまとめています。

## 何をするサンプルか

社内の勤怠システムの使い方マニュアル（15枚）を検索して答える、社内ヘルプデスクの問い合わせチャットです。普通の RAG エージェントを Amazon Bedrock AgentCore Runtime に載せ、次のことを行います。

- AgentCore Evaluations で、正解つきの質問セット（ゴールデン QA セット）を使って答えを採点する
- 自作の評価器（根拠チェック）で、答えがマニュアルに書かれていることだけでできているかを確かめる
- Amazon Bedrock Guardrails で、プロンプトインジェクション、他の社員の情報を聞き出す質問、個人情報を止める
- 本番の会話を、オンライン評価で採点し続ける

マニュアルは本書のために作った架空のものです。

```
スクリプト（質問を送る）
 │
 ▼
AgentCore Runtime（東京）
 └ 問い合わせチャット（Strands Agents）
    ├ Guardrails（呼び出しごとに付け外し）
    ├ 検索ツール ─▶ Bedrock Managed Knowledge Base
    │               └ マニュアル15枚（S3）
    └ Claude Sonnet 4.6（jp. 推論プロファイル）
 │ トレース
 ▼
CloudWatch（Transaction Search）
 │
 ▼
AgentCore Evaluations
 ├ オンデマンド評価：ゴールデン QA セット30問
 └ オンライン評価：本番の会話を採点し続ける
```

## 検証環境

| 項目 | 内容 |
|---|---|
| 検証日 | 2026-09-27 |
| AWS リージョン | 東京（ap-northeast-1） |
| モデル | `jp.anthropic.claude-sonnet-4-6` |
| 使用サービス | Amazon Bedrock AgentCore（Runtime、Evaluations）、Amazon Bedrock（Managed Knowledge Base、Guardrails）、Amazon S3、Amazon CloudWatch |
| ライブラリ | strands-agents 1.57.1、bedrock-agentcore 1.23.1、boto3 1.43.103、aws-opentelemetry-distro 0.18.0 |
| CLI | AgentCore CLI（`@aws/agentcore`）0.30.0、uv 0.11 |

## ファイル

### `01-quality-app/`（AIエージェントの品質）

| パス | 内容 |
|---|---|
| `help/` | 勤怠システムの使い方マニュアル 15 枚（Markdown） |
| `app/helpdesk/main.py` | エージェント本体 |
| `app/helpdesk/search.py` | マニュアルを検索するツール |
| `app/helpdesk/resources.py` | KB と Guardrail の ID を名前から引き当てる |
| `agentcore/` | AgentCore CLI のプロジェクト設定と CDK。実行ロールに KB と Guardrail の権限を足してある（`cdk/lib/cdk-stack.ts`） |
| `create_kb.py` | S3 にマニュアルを置き、Managed KB を作る |

### `02-evaluation/`（AIエージェントの評価）

| パス | 内容 |
|---|---|
| `questions.jsonl` | ゴールデン QA セット 30 問 |
| `grounded_check.txt` | 自作の評価器（根拠チェック）の判定プロンプト |
| `create_evaluator.py` | 根拠チェックを AgentCore Evaluations に登録する |
| `run_questions.py` | 質問を Runtime 上のエージェントに流し、答えを記録する（他の章からも使う） |
| `score.py` | 記録した答えを AgentCore Evaluations で採点し、質問の種類ごとに集計する |
| `results/` | 実測の結果 |

ゴールデン QA セットの内訳は次のとおりです。ゴールデン QA セットはエージェントに見せず、評価スクリプトだけが読みます。

| `category` | 件数 | 中身 |
|---|---|---|
| `straightforward` | 20 | マニュアルを素直に読めば答えられる質問 |
| `tricky` | 5 | 間違えやすい質問。似た名前の機能、新旧の画面、社員・承認者・管理者の立場で答えが変わるもの |
| `unanswerable` | 5 | マニュアルに記載が無い質問。「記載が無い」と伝えるのが正解 |

### `03-guardrails/`（ガードレール）

| パス | 内容 |
|---|---|
| `create_guardrail.py` | Guardrail を作る |
| `attacks.jsonl` | 攻撃用の質問 12 問 |
| `count_guard.py` | Guardrail が攻撃を止めた割合と、普通の質問を止めすぎた割合を数える |
| `results/` | 実測の結果 |

### `04-online-evaluation/`（本番運用での評価）

| パス | 内容 |
|---|---|
| `create_online_eval.py` | オンライン評価を設定する |
| `live.jsonl` | 本番の会話に見立てた質問 5 問 |
| `results/` | 実測の結果 |

## 動かし方

手順は macOS で確かめました。Windows では確かめていません。Windows では PowerShell を使う前提で、macOS と違う箇所を併記しています。コマンドは、特に断りが無ければリポジトリのいちばん上のフォルダで実行します。

### 0. 準備するもの

| もの | 確かめ方 |
|---|---|
| AWS の認証情報（東京リージョンで Bedrock と AgentCore を使える権限） | `aws sts get-caller-identity` |
| Node.js 20 以上 | `node --version` |
| AgentCore CLI | `npm install -g @aws/agentcore` のあと `agentcore --version` |
| uv（Python のパッケージ管理ツール） | 下の手順で入れて `uv --version` |

Python は uv が自動で用意するので、別に入れる必要はありません。

AWS のプロファイルを使う場合は、先に環境変数で指定しておきます。

```sh
# macOS / Linux
export AWS_PROFILE=<プロファイル名>
```

```powershell
# Windows（PowerShell）
$env:AWS_PROFILE = "<プロファイル名>"
```

### 1. uv を入れる

```sh
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows（PowerShell）
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Homebrew（`brew install uv`）や WinGet（`winget install --id=astral-sh.uv -e`）でも入ります。入れたあとはターミナルを開き直してください。

### 2. 仮想環境を作る

リポジトリのいちばん上のフォルダで実行します。

```sh
uv sync
```

`uv sync` は、フォルダ直下に仮想環境（`.venv`）を作り、Python 3.12 以上と必要なライブラリを入れます。以降のコマンドは `uv run` を付けて実行するので、仮想環境を有効化（activate）する必要はありません。

自分で有効化したい場合は、OS によってコマンドが違います。

```sh
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows（PowerShell）
.venv\Scripts\activate
```

エージェント本体（`01-quality-app/app/helpdesk/`）の依存ライブラリは、デプロイのときに AgentCore CLI がまとめるので、手元に入れる必要はありません。

### 3. 題材のアプリを作る（01-quality-app）

KB と Guardrail を作ってから、エージェントを Runtime にデプロイします。エージェントは実行時に KB と Guardrail を名前で探すので、先に両方を作っておきます。

```sh
uv run python 01-quality-app/create_kb.py
uv run python 03-guardrails/create_guardrail.py
```

作ったリソースの ID は `.state.json` に書き出されます（git の管理外です）。

次に `01-quality-app/agentcore/aws-targets.json` を作り、自分のアカウント ID とリージョンを書きます（git の管理外です）。

```json
[{"name": "default", "account": "<アカウント ID>", "region": "ap-northeast-1"}]
```

AgentCore CLI は `01-quality-app` フォルダで実行します。

```sh
cd 01-quality-app
agentcore deploy -y
agentcore invoke "打刻の時刻を間違えました。自分で直せますか？"
cd ..
```

デプロイ時に、CloudWatch の Transaction Search が有効になります（評価に必須です）。

### 4. ゴールデン QA セットで採点する（02-evaluation）

```sh
uv run python 02-evaluation/create_evaluator.py
uv run python 02-evaluation/run_questions.py --label base
uv run python 02-evaluation/score.py --label base --passes 3
```

答えのトレースが CloudWatch に届くまで数分かかります。`run_questions.py` のあと 5 分ほど待ってから `score.py` を実行してください。結果は `02-evaluation/results/` に書き出されます。

### 5. Guardrail を付けて比べる（03-guardrails）

```sh
uv run python 02-evaluation/run_questions.py --label guard --guardrail --results-dir 03-guardrails/results
uv run python 02-evaluation/run_questions.py --label attacks-guard --guardrail --questions 03-guardrails/attacks.jsonl --results-dir 03-guardrails/results
uv run python 03-guardrails/count_guard.py --attacks attacks-guard --normal guard
uv run python 02-evaluation/score.py --label guard --passes 1 --results-dir 03-guardrails/results
```

### 6. オンライン評価を設定する（04-online-evaluation）

```sh
uv run python 04-online-evaluation/create_online_eval.py
uv run python 02-evaluation/run_questions.py --label live --questions 04-online-evaluation/live.jsonl --results-dir 04-online-evaluation/results
```

採点結果は CloudWatch Logs の `/aws/bedrock-agentcore/evaluations/results/<設定 ID>` に書き込まれます。会話が終わってから結果が出るまで 15 分ほどかかります。サンプルでは動きを確かめやすいよう、全セッションを採点します（本番では割合を下げてください）。

## 片付け

```sh
uv run python shared/cleanup.py
cd 01-quality-app
agentcore remove all -y
agentcore deploy -y
cd ..
```

`agentcore remove all` の後の `agentcore deploy` で、Runtime とその実行ロールを含む CloudFormation スタックが消えます。

次のものは残ります。不要なら手動で消してください。

- CloudWatch Logs のロググループ（`/aws/bedrock-agentcore/` 配下）
- CloudWatch の Transaction Search の設定（アカウントとリージョンごとの設定です。サンプルのために有効にした場合は、CloudWatch の設定画面から戻せます）

## 注意

- AWS アカウント ID、ARN、API キーはこのリポジトリに含めていません。KB と Guardrail の ID は、エージェントが実行時に名前から引き当てます
- サンプルを動かすと AWS の利用料金がかかります。試したあとはリソースを削除してください
- Guardrails で日本語を扱うため、Standard ティアを使っています。Standard ティアはクロスリージョン推論が必須で、東京からは `apac.guardrail.v1:0` を使います。Guardrail の判定はアジア太平洋の他のリージョンで処理されることがあります
- AgentCore Evaluations の組み込み評価器の判定も、アジア太平洋の他のリージョンで処理されることがあります

## ライセンス

準備中です。
