# agentcore-quality

技術書典21で頒布する合同誌『AWSではじめるAIエージェントプロダクト開発』（書名は仮）の第2部「AIエージェントの評価とガードレール」のサンプルコードです。

本文と同じ状態のコードは、タグ `tbf21-v1.0` を参照してください（入稿時に付与します）。

## フォルダと本の章の対応

| フォルダ | 本の章 | 中身 |
|---|---|---|
| `01-quality-app/` | 第2部の1つめの章（AIエージェントの評価） | 題材の問い合わせチャット。エージェント、Runtime へのデプロイ設定、マニュアル、KB を作るスクリプト |
| `02-evaluation/` | 第2部の1つめの章（AIエージェントの評価） | 出す前の評価。ゴールデン QA セット、自作の根拠チェック、質問を流して採点するスクリプトと結果 |
| `04-online-evaluation/` | 第2部の1つめの章（AIエージェントの評価） | 本番環境での評価。オンライン評価の設定と結果 |
| `03-guardrails/` | 第2部の2つめの章（ガードレール） | Guardrail の設定、攻撃用の質問、止めた割合と止めすぎを数えるスクリプトと結果。本番で止めすぎに気づく話（オンライン評価の Refusal）もこの章で扱う |
| `shared/` | ― | 共通の設定、セットアップと片付けをまとめたスクリプト |

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

### `01-quality-app/`（題材のアプリ）

| パス | 内容 |
|---|---|
| `help/` | 勤怠システムの使い方マニュアル 15 枚（Markdown） |
| `app/helpdesk/main.py` | エージェント本体 |
| `app/helpdesk/search.py` | マニュアルを検索するツール |
| `app/helpdesk/resources.py` | KB と Guardrail の ID を名前から引き当てる |
| `agentcore/` | AgentCore CLI のプロジェクト設定と CDK。実行ロールに KB と Guardrail の権限を足してある（`cdk/lib/cdk-stack.ts`） |
| `create_kb.py` | S3 にマニュアルを置き、Managed KB を作る |

### `02-evaluation/`（出す前の評価）

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

### `04-online-evaluation/`（本番環境での評価）

| パス | 内容 |
|---|---|
| `create_online_eval.py` | オンライン評価を設定する |
| `live.jsonl` | 本番の会話に見立てた質問 5 問 |
| `results/` | 実測の結果 |

### `shared/` と、環境構築のためのファイル

| パス | 内容 |
|---|---|
| `shared/setup_all.py` | 題材のアプリを動かすところまでをまとめて準備する |
| `shared/teardown.py` | サンプルで作った AWS のリソースをまとめて消す |
| `shared/common.py` | 各章のスクリプトが共通で使う設定 |
| `shared/cleanup.py` | 各章のスクリプトで作ったリソースを消す（`teardown.py` から呼ぶ） |
| `.devcontainer/` | 開発コンテナの設定。`local-aws/` は手元の AWS 認証情報を渡す版 |
| `setup.sh`、`setup.ps1` | 手元で動かすときに、必要なツールがそろっているかを確かめる |

## 動かし方

手順は、macOS（Apple シリコン）の手元と、開発コンテナ（Linux）の中で確かめました（2026-09-28）。GitHub Codespaces と Windows では確かめていません。

### 準備するもの

| もの | 中身 |
|---|---|
| AWS アカウント | 東京リージョン（ap-northeast-1）で、Amazon Bedrock（Anthropic のモデル、Knowledge Bases、Guardrails）、Amazon Bedrock AgentCore、IAM、S3、CloudFormation、CloudWatch を使える権限。サンプルは IAM ロールも作るので、管理者に近い権限を想定しています |
| 実行する環境 | 次の三つのどれか一つ。① Docker と VS Code（Dev Containers 拡張）、② GitHub Codespaces、③ 手元に uv・Node.js 20 以上・AgentCore CLI 0.30.0・AWS CLI v2 を入れる |

### 1. 環境を用意する

どの方法でも、必要なツールが入り、Python の環境（`uv sync`）まで自動で整います。

**① VS Code の開発コンテナ（手元の AWS 認証情報をそのまま使う）**

リポジトリを VS Code で開き、コマンドパレットから「Dev Containers: Reopen in Container」を選びます。設定を聞かれたら「agentcore-quality（手元の AWS 認証情報を使う）」を選びます。手元の `~/.aws`（Windows は `%USERPROFILE%\.aws`）がコンテナに渡されるので、手元で `aws sts get-caller-identity` が通っていれば、そのまま使えます。

**② GitHub Codespaces（コンテナの中で AWS にログインする）**

GitHub のリポジトリの画面で「Code」→「Codespaces」から作ります。手元のファイルは渡せないので、コンテナの中で AWS にログインします。IAM Identity Center を使う場合は次のとおりです。

```sh
aws configure sso
aws sso login --use-device-code
```

IAM ユーザーでコンソールにサインインしている場合は、`aws login --remote` でも構いません。どちらも、表示されたコードをブラウザで入力して承認します。VS Code の開発コンテナで「agentcore-quality（コンテナ内で AWS にログインする）」を選んだ場合も、同じ手順です。

**③ 手元で動かす**

足りないツールがあれば、入れ方を表示します。そろっていれば `uv sync` まで行います。

```sh
# macOS / Linux
./setup.sh
```

```powershell
# Windows（PowerShell）
.\setup.ps1
```

AWS のプロファイルを使う場合は、環境変数で指定しておきます（macOS / Linux は `export AWS_PROFILE=<プロファイル名>`、Windows の PowerShell は `$env:AWS_PROFILE = "<プロファイル名>"`）。

### 2. 題材のアプリを動かす（セットアップ）

```sh
uv run python shared/setup_all.py
```

次の順に進みます。途中で失敗しても、もう一度流せば続きから進みます（作成済みのリソースは作り直しません）。

1. S3 にマニュアルを置き、Managed KB を作る（`01-quality-app/create_kb.py`）
2. Guardrail を作る（`03-guardrails/create_guardrail.py`）
3. デプロイ先（アカウント ID とリージョン）を `01-quality-app/agentcore/aws-targets.json` に書き出す。アカウント ID は認証情報から自動で取ります
4. エージェントを AgentCore Runtime にデプロイする（`agentcore deploy`）
5. 1 問だけ聞いて、動作を確かめる（`agentcore invoke`）

作ったリソースの ID は `.state.json` に書き出されます（git の管理外です）。デプロイ時に、CloudWatch の Transaction Search が有効になります（評価に必須です）。

### 3. 出す前の評価（02-evaluation）

```sh
uv run python 02-evaluation/create_evaluator.py
uv run python 02-evaluation/run_questions.py --label base
uv run python 02-evaluation/score.py --label base --passes 3
```

答えのトレースが CloudWatch に届くまで数分かかります。`run_questions.py` のあと 5 分ほど待ってから `score.py` を実行してください。結果は `02-evaluation/results/` に書き出されます。

### 4. 本番環境での評価（04-online-evaluation）

```sh
uv run python 04-online-evaluation/create_online_eval.py
uv run python 02-evaluation/run_questions.py --label live --questions 04-online-evaluation/live.jsonl --results-dir 04-online-evaluation/results
```

採点結果は CloudWatch Logs の `/aws/bedrock-agentcore/evaluations/results/<設定 ID>` に書き込まれます。会話が終わってから結果が出るまで 15 分ほどかかります。サンプルでは動きを確かめやすいよう、全セッションを採点します（本番では割合を下げてください）。

### 5. ガードレール（03-guardrails）

```sh
uv run python 02-evaluation/run_questions.py --label guard --guardrail --results-dir 03-guardrails/results
uv run python 02-evaluation/run_questions.py --label attacks-guard --guardrail --questions 03-guardrails/attacks.jsonl --results-dir 03-guardrails/results
uv run python 03-guardrails/count_guard.py --attacks attacks-guard --normal guard
uv run python 02-evaluation/score.py --label guard --passes 1 --results-dir 03-guardrails/results
```

Guardrail の設定（`03-guardrails/create_guardrail.py`）を変えたときは、`uv run python 03-guardrails/create_guardrail.py --update` で新しいバージョンとして公開します。

## 片付け

```sh
uv run python shared/teardown.py
```

評価器、オンライン評価、Guardrail、KB、S3 バケット、IAM ロールを消してから、`agentcore remove all` と `agentcore deploy` で Runtime とその実行ロールを含む CloudFormation スタックを消します。

次のものは残ります。不要なら手動で消してください。

- CloudWatch Logs のロググループ（`/aws/bedrock-agentcore/` 配下。エージェントのログと、オンライン評価の結果）
- CloudWatch の Transaction Search の設定（アカウントとリージョンごとの設定です。サンプルのために有効にした場合は、CloudWatch の設定画面から戻せます）
- CDK の準備用スタック（CDKToolkit）。デプロイのときに作られた場合は残ります

## 注意

- AWS アカウント ID、ARN、API キーはこのリポジトリに含めていません。KB と Guardrail の ID は、エージェントが実行時に名前から引き当てます
- サンプルを動かすと AWS の利用料金がかかります。試したあとはリソースを削除してください
- Guardrails で日本語を扱うため、Standard ティアを使っています。Standard ティアはクロスリージョン推論が必須で、東京からは `apac.guardrail.v1:0` を使います。Guardrail の判定はアジア太平洋の他のリージョンで処理されることがあります
- AgentCore Evaluations の組み込み評価器の判定も、アジア太平洋の他のリージョンで処理されることがあります

## ライセンス

準備中です。
