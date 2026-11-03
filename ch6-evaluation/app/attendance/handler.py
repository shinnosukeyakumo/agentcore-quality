"""勤怠の記録を返す Lambda。Gateway のツールとして呼ばれる。

記録は架空のもの。本物のシステムの代わりに、社員番号と月で引く。
"""

import json

RECORDS = {
    ("E0001", "2026-10"): {
        "出勤日数": 20,
        "残業時間": "12時間30分",
        "有給休暇の残り": "8日",
        "打刻漏れ": ["2026-10-14 退勤"],
    },
    ("E0001", "2026-09"): {
        "出勤日数": 19,
        "残業時間": "8時間",
        "有給休暇の残り": "9日",
        "打刻漏れ": [],
    },
    ("E0002", "2026-10"): {
        "出勤日数": 18,
        "残業時間": "30時間",
        "有給休暇の残り": "3日",
        "打刻漏れ": [],
    },
}


def handler(event, context):
    # ツールの引数は event の直下に入る
    employee_id = event.get("employee_id", "")
    month = event.get("month", "")
    record = RECORDS.get((employee_id, month))
    if record is None:
        return {"error": f"{employee_id} の {month} の記録はありません"}
    return {"employee_id": employee_id, "month": month, **record}


if __name__ == "__main__":
    print(
        json.dumps(
            handler({"employee_id": "E0001", "month": "2026-10"}, None),
            ensure_ascii=False,
        )
    )
