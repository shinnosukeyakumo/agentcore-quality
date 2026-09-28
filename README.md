# agentcore-quality

技術書典21で頒布する合同誌『AWSではじめるAIエージェントプロダクト開発』（書名は仮）の第2部「AIエージェントの評価とガードレール」のサンプルコードです。

本文と同じ状態のコードは、タグ `tbf21-v1.0` を参照してください（入稿時に付与します）。

## フォルダと本の章の対応

| フォルダ | 本の章 | 中身 |
|---|---|---|
| `ch2-evaluation/` | 第2章「AIエージェントの評価」 | 題材のアプリ（`app/`）、出す前の評価（`offline/`）、本番環境での評価（`online/`） |
| `ch3-guardrails/` | 第3章「ガードレール」 | Guardrail の設定、攻撃用の質問、止めた割合と止めすぎの測定 |
| `shared/` | ― | 共通の設定と、セットアップ・片付けをまとめたスクリプト |

フォルダ名の章番号（ch2、ch3）は仮です。本の第1部の章の数が決まると変わることがあります。

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

### `ch2-evaluation/app/`（題材のアプリ）

| パス | 内容 |
|---|---|
| `help/` | 勤怠システムの使い方マニュアル 15 枚（Markdown） |
| `helpdesk/main.py` | エージェント本体 |
| `helpdesk/search.py` | マニュアルを検索するツール |
| `helpdesk/resources.py` | KB と Guardrail の ID を名前から引き当てる |
| `agentcore/` | AgentCore CLI のプロジェクト設定と CDK。実行ロールに KB と Guardrail の権限を足してある（`cdk/lib/cdk-stack.ts`） |
| `create_kb.py` | S3 にマニュアルを置き、Managed KB を作る |

### `ch2-evaluation/offline/`（出す前の評価）

| パス | 内容 |
|---|---|
| `questions.jsonl` | ゴールデン QA セット 30 問 |
| `grounded_check.txt` | 自作の評価器（根拠チェック）の判定プロンプト |
| `create_evaluator.py` | 根拠チェックを AgentCore Evaluations に登録する |
| `run_questions.py` | 質問を Runtime 上のエージェントに流し、答えを記録する（第3章からも使う） |
| `score.py` | 記録した答えを AgentCore Evaluations で採点し、質問の種類ごとに集計する |
| `evaluate.py` | 上の三つを順に実行する（タスク 3） |
| `results/` | 実測の結果 |

ゴールデン QA セットの内訳は次のとおりです。ゴールデン QA セットはエージェントに見せず、評価スクリプトだけが読みます。

| `category` | 件数 | 中身 |
|---|---|---|
| `straightforward` | 20 | マニュアルを素直に読めば答えられる質問 |
| `tricky` | 5 | 間違えやすい質問。似た名前の機能、新旧の画面、社員・承認者・管理者の立場で答えが変わるもの |
| `unanswerable` | 5 | マニュアルに記載が無い質問。「記載が無い」と伝えるのが正解 |

### `ch2-evaluation/online/`（本番環境での評価）

| パス | 内容 |
|---|---|
| `create_online_eval.py` | オンライン評価を設定する |
| `live.jsonl` | 本番の会話に見立てた質問 5 問 |
| `start.py` | オンライン評価を設定し、`live.jsonl` の質問を流す（タスク 5） |
| `results/` | 実測の結果 |

### `ch3-guardrails/`（ガードレール）

| パス | 内容 |
|---|---|
| `create_guardrail.py` | Guardrail を作る |
| `attacks.jsonl` | 攻撃用の質問 12 問 |
| `count_guard.py` | Guardrail が攻撃を止めた割合と、普通の質問を止めすぎた割合を数える |
| `compare.py` | Guardrail ありで質問と攻撃を流し、数えて採点する（タスク 4） |
| `results/` | 実測の結果 |

### `shared/` と、準備のためのファイル

| パス | 内容 |
|---|---|
| `shared/setup_all.py` | 題材のアプリを動かすところまでをまとめて準備する（タスク 2） |
| `shared/teardown.py` | サンプルで作った AWS のリソースをまとめて消す（タスク 6） |
| `shared/common.py` | 各章のスクリプトが共通で使う設定 |
| `shared/cleanup.py` | 各章のスクリプトで作ったリソースを消す（`teardown.py` から呼ぶ） |
| `setup.sh`、`setup.ps1` | 必要なツールがそろっているかを確かめる（タスク 1） |
| `.vscode/tasks.json` | VS Code のタスクの定義 |

## 動かし方

VS Code でリポジトリを開き、メニューの「ターミナル」→「タスクの実行」から、番号の順にタスクを選ぶだけで動きます。コマンドを打ちたい人のために、各タスクの中身も書いておきます。コマンドは、リポジトリのいちばん上のフォルダで実行します。

手順は macOS（Apple シリコン）で確かめました（2026-09-29）。Windows では確かめていません。

### 準備するもの

| もの | 中身 |
|---|---|
| AWS アカウント | 東京リージョン（ap-northeast-1）で、Amazon Bedrock（Anthropic のモデル、Knowledge Bases、Guardrails）、Amazon Bedrock AgentCore、IAM、S3、CloudFormation、CloudWatch を使える権限。サンプルは IAM ロールも作るので、管理者に近い権限を想定しています |
| AWS の認証情報 | ターミナルで `aws sts get-caller-identity` が通る状態。プロファイルを使う場合は、環境変数 `AWS_PROFILE` を設定してから VS Code を起動します |
| VS Code | タスクを使う場合 |
| uv | Python のパッケージ管理ツール。Python は uv が自動で用意します |
| Node.js 20 以上 | AgentCore CLI と CDK が使います |
| AgentCore CLI 0.30.0 | `npm install -g @aws/agentcore@0.30.0` |
| AWS CLI v2 | 認証情報の確かめとログインに使います |

足りないものは、タスク 1 が教えてくれます。

### タスクの一覧

| タスク | 中で行うこと | コマンド |
|---|---|---|
| 1. 準備の確認 | uv、Node.js（20 以上か）、AgentCore CLI、AWS CLI がそろっているかを確かめ、足りないものの入れ方を表示する。そろっていれば `uv sync` で Python の環境を作る | macOS / Linux は `./setup.sh`、Windows は `.\setup.ps1` |
| 2. セットアップ | KB と Guardrail を作り、デプロイ先を書き出し、エージェントを Runtime にデプロイして、1 問で動作を確かめる | `uv run python shared/setup_all.py` |
| 3. 質問セットで採点する（第2章） | 自作の評価器を登録し、ゴールデン QA セット 30 問を流し、トレースを 5 分待ってから 3 回採点して集計する（約 10 分） | `uv run python ch2-evaluation/offline/evaluate.py` |
| 4. Guardrail を付けて比べる（第3章） | Guardrail ありでゴールデン QA セットと攻撃用の質問を流し、止めた割合と止めすぎた割合を数え、採点する（約 10 分） | `uv run python ch3-guardrails/compare.py` |
| 5. オンライン評価を設定する（第2章） | オンライン評価を設定し、本番に見立てた質問を 5 問流す | `uv run python ch2-evaluation/online/start.py` |
| 6. 片付け | サンプルで作った AWS のリソースをまとめて消す | `uv run python shared/teardown.py` |

### タスク 2（セットアップ）の中身

次の順に進みます。途中で失敗しても、もう一度流せば続きから進みます（作成済みのリソースは作り直しません）。

1. S3 にマニュアルを置き、Managed KB を作る（`ch2-evaluation/app/create_kb.py`）
2. Guardrail を作る（`ch3-guardrails/create_guardrail.py`）
3. デプロイ先（アカウント ID とリージョン）を `ch2-evaluation/app/agentcore/aws-targets.json` に書き出す。アカウント ID は認証情報から自動で取ります
4. エージェントを AgentCore Runtime にデプロイする（`agentcore deploy`）
5. 1 問だけ聞いて、動作を確かめる（`agentcore invoke`）

作ったリソースの ID は `.state.json` に書き出されます（git の管理外です）。デプロイ時に、CloudWatch の Transaction Search が有効になります（評価に必須です）。

### 結果の見方

- タスク 3 の結果は `ch2-evaluation/offline/results/`、タスク 4 の結果は `ch3-guardrails/results/` に書き出されます
- タスク 5 の採点結果は、会話が終わってから 15 分ほどで CloudWatch Logs の `/aws/bedrock-agentcore/evaluations/results/<設定 ID>` に出ます。サンプルでは動きを確かめやすいよう全セッションを採点します（本番では割合を下げてください）
- Guardrail の設定（`ch3-guardrails/create_guardrail.py`）を変えたときは、`uv run python ch3-guardrails/create_guardrail.py --update` で新しいバージョンとして公開します

## 片付け

タスク 6（`uv run python shared/teardown.py`）で、評価器、オンライン評価、Guardrail、KB、S3 バケット、IAM ロールを消してから、`agentcore remove all` と `agentcore deploy` で Runtime とその実行ロールを含む CloudFormation スタックを消します。

次のものは残ります。不要なら手動で消してください。

- CloudWatch Logs のロググループ（`/aws/bedrock-agentcore/` 配下。エージェントのログと、オンライン評価の結果）
- CloudWatch の Transaction Search の設定（アカウントとリージョンごとの設定です。サンプルのために有効にした場合は、CloudWatch の設定画面から戻せます）
- CDK の準備用スタック（CDKToolkit）。デプロイのときに作られた場合は残ります

## 注意

- AWS アカウント ID、ARN、API キーはこのリポジトリに含めていません。KB と Guardrail の ID は、エージェントが実行時に名前から引き当てます。デプロイ先のアカウント ID は、セットアップのときに認証情報から自動で取ります
- サンプルを動かすと AWS の利用料金がかかります。試したあとはリソースを削除してください
- Guardrails で日本語を扱うため、Standard ティアを使っています。Standard ティアはクロスリージョン推論が必須で、東京からは `apac.guardrail.v1:0` を使います。Guardrail の判定はアジア太平洋の他のリージョンで処理されることがあります
- AgentCore Evaluations の組み込み評価器の判定も、アジア太平洋の他のリージョンで処理されることがあります

## ライセンス

準備中です。
