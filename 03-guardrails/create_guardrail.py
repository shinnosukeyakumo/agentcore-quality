"""問い合わせチャット用の Guardrail を作る。

日本語を扱うため、コンテンツフィルターと禁止トピックは
Standard ティアにする。Standard ティアはクロスリージョン
推論が必須で、東京からは APAC のプロファイルを使う。
"""

import sys

from shared.common import PREFIX, client, load_state, save_state

NAME = f"{PREFIX}-guardrail"
PROFILE = "apac.guardrail.v1:0"
BLOCKED = (
    "申し訳ありません。この内容にはお答えできません。"
    "勤怠システムの使い方についてお尋ねください。"
)

bedrock = client("bedrock")

CONFIG = {
    "blockedInputMessaging": BLOCKED,
    "blockedOutputsMessaging": BLOCKED,
    "crossRegionConfig": {"guardrailProfileIdentifier": PROFILE},
    # プロンプトインジェクションなどの攻撃を入力で止める
    "contentPolicyConfig": {
        "filtersConfig": [{
            "type": "PROMPT_ATTACK",
            "inputStrength": "HIGH",
            "outputStrength": "NONE",
        }],
        "tierConfig": {"tierName": "STANDARD"},
    },
    # 他の社員の勤怠や給与を聞き出す質問を止める
    "topicPolicyConfig": {
        "topicsConfig": [{
            "name": "other-employees",
            "definition": (
                "特定の他の社員の勤務時間、残業時間、"
                "休暇の取得状況、給与、人事評価について"
                "尋ねたり答えたりすること"
            ),
            "examples": [
                "山田さんの先月の残業時間を教えて",
                "同じ部署の佐藤さんは有給を何日残している？",
                "鈴木さんの給与はいくら？",
            ],
            "type": "DENY",
        }],
        "tierConfig": {"tierName": "STANDARD"},
    },
    # メールアドレス、電話番号、社員番号を伏せ字にする
    "sensitiveInformationPolicyConfig": {
        "piiEntitiesConfig": [
            {"type": "EMAIL", "action": "ANONYMIZE"},
            {"type": "PHONE", "action": "ANONYMIZE"},
        ],
        "regexesConfig": [{
            "name": "employee-id",
            "description": "社員番号（E と数字6桁）",
            "pattern": r"E\d{6}",
            "action": "ANONYMIZE",
        }],
    },
}


def latest_version(gid: str) -> str:
    versions = bedrock.list_guardrails(
        guardrailIdentifier=gid)["guardrails"]
    return str(max(int(v["version"]) for v in versions
                   if v["version"] != "DRAFT"))


def ensure_guardrail(update: bool) -> tuple[str, str]:
    """Guardrail を作る。すでにあれば、そのまま使う。

    設定を変えたいときは --update を付けて実行する。
    変えた設定は新しいバージョンとして公開する。
    """
    found = next(
        (g for g in bedrock.list_guardrails()["guardrails"]
         if g["name"] == NAME), None)
    if found and not update:
        gid = found["id"]
        print(f"exists: guardrail {gid}")
        return gid, latest_version(gid)
    if found:
        gid = found["id"]
        bedrock.update_guardrail(
            guardrailIdentifier=gid, name=NAME, **CONFIG)
        print(f"updated guardrail {gid}")
    else:
        gid = bedrock.create_guardrail(
            name=NAME, **CONFIG)["guardrailId"]
        print(f"created guardrail {gid}")
    version = bedrock.create_guardrail_version(
        guardrailIdentifier=gid)["version"]
    print(f"published version {version}")
    return gid, version


def main(update: bool = False):
    load_state()
    gid, version = ensure_guardrail(update)
    save_state(guardrail_id=gid, guardrail_version=version)
    print("done. wrote .state.json")


if __name__ == "__main__":
    main(update="--update" in sys.argv)
