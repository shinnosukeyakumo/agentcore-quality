// 勤怠の記録は、質問している本人（サンプルでは E0001）の分だけ照会できる。
// 他の社員番号での呼び出しは、どの policy にも当たらず既定で拒否される。
// {gateway_arn} は、create_policy.py がデプロイ済みの Gateway の ARN に置き換える。
permit (
  principal is AgentCore::IamEntity,
  action == AgentCore::Action::"attendance___get_attendance",
  resource == AgentCore::Gateway::"{gateway_arn}"
) when {
  context.input.employee_id == "E0001"
};
