# Nexent 联调交接

## D1 平台验证

服务器 Nexent 已验证文本推理、d1_ping 调用、d1-mcp-smoke 同轮读取与调用和 Agent 导出。文本验收输出 D1-TEXT-OK 42。MCP 用 D1-001 调用 d1_ping 并返回 D1-MCP-OK。视觉附件复测尚待补。

## D2 巡检复跑

1. 进入 d2 目录，用普通用户运行 python3 server.py --bind <Nexent 后端可达的监听地址> --port 18082。传参前将占位地址换为实际值。服务使用 Python 标准库。
2. 在 Nexent 注册 workshop-safety-d2，地址填 http://<部署地址>:18082/mcp。绑定 get_event_evidence、lookup_applicable_rule、get_work_order、get_permit。
3. 将 d2-inspection 目录打包为 ZIP，上传后给独立的 D2 智能体绑定该技能。主模型沿用项目租户中的车间安全-总控推理。
4. 分别要求智能体读取 d2-inspection 并对下列事件执行巡检研判，展开工具调用详情核对返回。

| 用例 | 预期 |
| --- | --- |
| D2-OLD-001 | SOP v1，工单 WO-D2-OLD，跳过许可查询 |
| D2-NEW-001 | SOP v2，工单 WO-D2-NEW，许可 PERMIT-D2-NEW 有效 |
| D2-MISSING-001 | SOP v2，工单 WO-D2-MISSING，许可返回 not_found，事件卡标为待核验 |

原片证据来自 B 的 VID-SAFE-0_te23，区间 500–7000 ms。业务记录、区域和事发时间由本包提供模拟数据。此目录提供可重新启动的测试服务，团队共享平台现有实例的部署参数由维护人提供。

D2 Agent 导出已核对技能和四个工具绑定。新版有许可分支已有 Nexent 通过证据。归档还需补存旧版独立最终回复及缺许可分支的原始工具返回。
