# agentcore-quality

技術書典21で頒布する合同誌『AWSではじめるAIエージェントプロダクト開発』（書名は仮）の第2部「AIエージェントの評価とガードレール」のサンプルコードです。

本文と同じ状態のコードは、タグ `tbf21-v1.0` を参照してください（入稿時に付与します）。

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

## 構成

| パス | 内容 |
|---|---|
| `help/` | 勤怠システムの使い方マニュアル 15 枚（Markdown） |
| `app/helpdesk/` | エージェント本体。`main.py`（エージェント）、`search.py`（検索ツール）、`resources.py`（KB と Guardrail の ID を名前から引く） |
| `agentcore/` | AgentCore CLI のプロジェクト設定と CDK。実行ロールに KB と Guardrail の権限を足してある（`cdk/lib/cdk-stack.ts`） |
| `setup/` | KB、Guardrail、自作の評価器、オンライン評価を作るスクリプトと、片付けのスクリプト |
| `eval/questions.jsonl` | ゴールデン QA セット 30 問 |
| `eval/attacks.jsonl` | 攻撃用の質問 12 問 |
| `eval/live.jsonl` | 本番の会話に見立てた質問 5 問（オンライン評価の確認用） |
| `eval/grounded_check.txt` | 自作の評価器（根拠チェック）の判定プロンプト |
| `run_questions.py` | 質問を Runtime 上のエージェントに流し、答えを `results/` に記録する |
| `score.py` | 記録した答えを AgentCore Evaluations で採点し、質問の種類ごとに集計する |
| `count_guard.py` | Guardrail が攻撃を止めた割合と、普通の質問を止めすぎた割合を数える |
| `results/` | 検証日に取った実測の結果 |

### ゴールデン QA セットの内訳

| `category` | 件数 | 中身 |
|---|---|---|
| `straightforward` | 20 | マニュアルを素直に読めば答えられる質問 |
| `tricky` | 5 | 間違えやすい質問。似た名前の機能、新旧の画面、社員・承認者・管理者の立場で答えが変わるもの |
| `unanswerable` | 5 | マニュアルに記載が無い質問。「記載が無い」と伝えるのが正解 |

ゴールデン QA セットはエージェントに見せません。評価スクリプトだけが読みます。

## 動かし方

前提として、AWS の認証情報（東京リージョンで Bedrock と AgentCore を使える権限）、Python 3.12 以上、[uv](https://docs.astral.sh/uv/)、Node.js 20 以上、AgentCore CLI（`npm install -g @aws/agentcore`）が必要です。

### 1. KB、Guardrail、評価器を作る

```sh
uv sync
cd setup
uv run python create_kb.py
uv run python create_guardrail.py
uv run python create_evaluator.py
cd ..
```

作ったリソースの ID は `.state.json` に書き出されます（git の管理外です）。

### 2. エージェントを Runtime にデプロイする

`agentcore/aws-targets.json` に自分のアカウント ID とリージョンを書いてから、デプロイします。

```json
[{"name": "default", "account": "<アカウント ID>", "region": "ap-northeast-1"}]
```

```sh
agentcore deploy -y
agentcore invoke '{"prompt": "打刻の時刻を間違えました。自分で直せますか？"}'
```

デプロイ時に、CloudWatch の Transaction Search が有効になります（評価に必須です）。

### 3. ゴールデン QA セットで採点する

```sh
uv run python run_questions.py --label base
# トレースが CloudWatch に届くまで数分待つ
uv run python score.py --label base --passes 3
```

### 4. Guardrail を付けて比べる

```sh
uv run python run_questions.py --label guard --guardrail
uv run python run_questions.py --label attacks-guard \
    --questions eval/attacks.jsonl --guardrail
uv run python count_guard.py --attacks attacks-guard --normal guard
uv run python score.py --label guard --passes 1
```

### 5. オンライン評価を設定する

```sh
cd setup && uv run python create_online_eval.py && cd ..
uv run python run_questions.py --label live --questions eval/live.jsonl
```

採点結果は CloudWatch Logs の `/aws/bedrock-agentcore/evaluations/results/<設定 ID>` に書き込まれます。サンプルでは動きを確かめやすいよう、全セッションを採点します（本番では割合を下げてください）。

## 片付け

```sh
cd setup && uv run python cleanup.py && cd ..
agentcore remove all -y
agentcore deploy -y
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
