---
name: d2-inspection
description: 用户给出 D2 事件 ID 并请求巡检研判时，按事件证据、事发时 SOP 和业务记录生成事件卡。
---

# D2 巡检研判

1. 调用 get_event_evidence，传入用户提供的 event_id。无事件或工具出错时报告状态并结束。
2. 从结果读取 event_type、area_id、occurred_at，原样调用 lookup_applicable_rule。无规则或规则冲突时列为待核验并结束业务补查。
3. required_evidence 包含 work_order 时，传入事件的 device_id、area_id、occurred_at 调用 get_work_order。
4. 仅当 required_evidence 包含 permit 且取得 work_order_id 时，传入该 ID、事件的 area_id、occurred_at 调用 get_permit。许可 not_found 时写“许可待核验”。工单未找到时，指出无法补查许可的原因。
5. 输出事件卡，含事件 ID、画面可见事实、原片 URI 及毫秒区间、SOP 版本和条款位置、工单或许可记录 ID、待核验项。注明业务关联和记录为模拟。按原样保留可见事实和越界候选状态。
6. 工具错误或来源冲突时保留已取得证据并标注实际状态。完成所需查询后直接输出事件卡。
