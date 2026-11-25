// ============================================================================
// 成员 C · Neo4j 图谱验证查询（逐条执行，截图可作为验收证据）
// 预期：查询2 同时返回原片、工单/历史事件/整改、SOP 版本；
//       查询4 历史事件=v1.0、当前事件=v2.0；查询5 动态匹配结果与查询4一致。
// ============================================================================

// 查询1：图谱规模（确认 8 类节点都已导入）
MATCH (n) RETURN labels(n) AS 节点类型, count(*) AS 数量 ORDER BY 数量 DESC;

// 查询2【队长验收核心】：给定 event_id 同时查原片 + 业务记录
MATCH (e:Event {event_id:'EVT-0_te21-001'})
OPTIONAL MATCH (e)-[:OCCURRED_ON]->(d:Device)
OPTIONAL MATCH (e)-[:HAS_WORK_ORDER]->(w:WorkOrder)
OPTIONAL MATCH (e)-[:HAS_GAP]->(g:EvidenceGap)
OPTIONAL MATCH (e)-[:RELATED_HISTORY]->(h:HistoricalEvent)
OPTIONAL MATCH (h)-[:HAS_RECTIFICATION]->(r:Rectification)
OPTIONAL MATCH (e)-[:GOVERNED_BY]->(s:SOP)
RETURN e.event_id, e.video_file, e.time_range, d.camera_id, d.area_id,
       w.work_order_id, g.gap_type, h.event_id AS 历史事件, r.action AS 整改措施,
       s.version AS SOP版本, s.clause AS 条款;

// 查询3【多跳路径】：事件→设备→历史事件→整改记录（M4 按设备检索历史的依据）
MATCH p=(e:Event {event_id:'EVT-0_te21-001'})-[:OCCURRED_ON]->(d:Device)
       -[:HAS_HISTORY]->(h:HistoricalEvent)-[:HAS_RECTIFICATION]->(r:Rectification)
RETURN p;

// 查询4：事件/历史事件 → 适用 SOP 版本 → 条款（预建关系）
MATCH (n)-[:GOVERNED_BY]->(s:SOP)
WHERE n:Event OR n:HistoricalEvent
RETURN labels(n) AS 类型, n.event_id, n.occurred_at AS 事发时间,
       s.version AS 版本, s.effective_from AS 生效, s.clause AS 条款
ORDER BY n.occurred_at;

// 查询5【按事发时间动态命中】：不依赖预建关系，用生效期算一遍，应与查询4一致
MATCH (n) WHERE n:Event OR n:HistoricalEvent
MATCH (s:SOP)
WHERE n.occurred_at >= s.effective_from
  AND (s.effective_to IS NULL OR n.occurred_at < s.effective_to)
RETURN n.event_id, n.occurred_at AS 事发时间, s.version AS 计算版本, s.clause AS 条款
ORDER BY n.occurred_at;

// 查询6：两种缺证分开查（业务缺证 1 条 + 画面缺证 2 条）
MATCH (e:Event)-[:HAS_GAP]->(g:EvidenceGap)
RETURN e.event_id, e.role, g.gap_type, g.reason ORDER BY g.gap_type, e.event_id;

// 查询7【同视角可比】：V4 的正例与两个反例应挂同一台模拟机位 CAM-A01
MATCH (e:Event)-[:OCCURRED_ON]->(d:Device)
WHERE d.view_group='V4'
RETURN e.event_id, e.role, e.video_file, e.time_range, d.camera_id ORDER BY e.event_id;

// 查询8：模拟关系统计（确认所有业务关系都标记为 simulated）
MATCH ()-[r]->()
RETURN type(r) AS 关系类型, count(r) AS 数量,
       sum(CASE WHEN r.nature='simulated' THEN 1 ELSE 0 END) AS 模拟关系数
ORDER BY 关系类型;
