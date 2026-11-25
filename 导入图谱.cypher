// ============================================================================
// 成员 C · Neo4j 最小图谱导入脚本（自动生成，改表后重跑 生成Cypher.py）
// 数据来源：来源清单.csv / 设备台账.xlsx / 工单记录.xlsx / 整改记录.xlsx
// 对齐口径：event_id=B 格式；time_range=B samples.csv 事件子区间；
//           camera_id 按 B 的 V1-V6 背景聚类分配；area 统一 AREA-A（通道场景）
// 运行方式：Neo4j Browser 全选执行，或 cypher-shell -f 导入图谱.cypher
// 幂等性：全部 MERGE + 约束 IF NOT EXISTS，可重复运行
// ⚠️ 模拟声明：设备/工单/整改/历史事件/版本命中均为课程设计模拟档案；
//    公开视频片段与模拟业务档案之间只允许称"模拟关联"，不得称真实对应。
// ============================================================================

// 0. 清空库（默认注释。）仅在专用测试库需要重来时取消注释，会删掉整库所有节点和关系！
// MATCH (n) DETACH DELETE n;

// ---------- 1. 唯一性约束（Neo4j 5.x 语法；4.x 改为 ON ... ASSERT ... IS UNIQUE） ----------
CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (n:Event) REQUIRE n.event_id IS UNIQUE;
CREATE CONSTRAINT device_id_unique IF NOT EXISTS FOR (n:Device) REQUIRE n.device_id IS UNIQUE;
CREATE CONSTRAINT area_id_unique IF NOT EXISTS FOR (n:Area) REQUIRE n.area_id IS UNIQUE;
CREATE CONSTRAINT wo_id_unique IF NOT EXISTS FOR (n:WorkOrder) REQUIRE n.work_order_id IS UNIQUE;
CREATE CONSTRAINT gap_id_unique IF NOT EXISTS FOR (n:EvidenceGap) REQUIRE n.gap_id IS UNIQUE;
CREATE CONSTRAINT hist_id_unique IF NOT EXISTS FOR (n:HistoricalEvent) REQUIRE n.event_id IS UNIQUE;
CREATE CONSTRAINT rect_id_unique IF NOT EXISTS FOR (n:Rectification) REQUIRE n.rect_id IS UNIQUE;
CREATE CONSTRAINT sop_ver_unique IF NOT EXISTS FOR (n:SOP) REQUIRE n.version IS UNIQUE;

// ---------- 2. 区域节点（V1-V6 均为通道场景，area 统一 AREA-A；面板类 AREA-B 为备选） ----------
MERGE (a:Area {area_id:'AREA-A'})
SET a.name='通道 A', a.is_simulated=true, a.note='模拟档案；区域划分非真实工厂数据';
MERGE (a:Area {area_id:'AREA-B'})
SET a.name='配电柜 B', a.is_simulated=true, a.note='模拟档案；区域划分非真实工厂数据';

// ---------- 3. SOP 版本节点（生效时间用于"按事发时间命中当时条款"） ----------
MERGE (s:SOP {version:'v1.0'})
SET s.effective_from='2025-01-01', s.effective_to='2026-01-01',
    s.clause='人员越过划定的安全通道边界即触发告警。', s.source_file='SOP_v1.0.docx', s.is_simulated=true;
MERGE (s:SOP {version:'v2.0'})
SET s.effective_from='2026-01-01', s.effective_to=null,
    s.clause='人员越过划定的安全通道边界且持续超过 5 秒才触发告警；短暂越界不触发。', s.source_file='SOP_v2.0.docx', s.is_simulated=true;

// ---------- 4. 设备节点（camera_id 按 B 视角聚类；DEV-A02 已删"出口/补拍"臆造语义） ----------
MERGE (d:Device {device_id:'DEV-A01'})
SET d.area_id='AREA-A', d.camera_id='CAM-A01',
    d.name='通道 A（B 聚类 V4 视角）', d.view_group='V4',
    d.model='固定监控摄像机', d.status='在线',
    d.is_simulated=true, d.note='模拟档案；V4 视角，含 0_te21 正例与 4_te5/4_te6 反例，同视角可比';
MATCH (d:Device {device_id:'DEV-A01'}), (a:Area {area_id:'AREA-A'})
MERGE (d)-[:LOCATED_IN {nature:'simulated'}]->(a);
MERGE (d:Device {device_id:'DEV-B01'})
SET d.area_id='AREA-B', d.camera_id='CAM-B01',
    d.name='配电柜 B', d.view_group='未聚类',
    d.model='固定监控摄像机', d.status='在线',
    d.is_simulated=true, d.note='模拟档案；面板类备选链（2_te12/6_te12），未参与 B 的 V 聚类';
MATCH (d:Device {device_id:'DEV-B01'}), (a:Area {area_id:'AREA-B'})
MERGE (d)-[:LOCATED_IN {nature:'simulated'}]->(a);
MERGE (d:Device {device_id:'DEV-A02'})
SET d.area_id='AREA-A', d.camera_id='CAM-A02',
    d.name='通道 A（B 聚类 V2 视角）', d.view_group='V2',
    d.model='固定监控摄像机', d.status='在线',
    d.is_simulated=true, d.note='模拟档案；V2 视角，含 0_te23；同视角反例 4_te9（B 提示人员过小不可直接判读）';
MATCH (d:Device {device_id:'DEV-A02'}), (a:Area {area_id:'AREA-A'})
MERGE (d)-[:LOCATED_IN {nature:'simulated'}]->(a);
MERGE (d:Device {device_id:'DEV-A03'})
SET d.area_id='AREA-A', d.camera_id='CAM-A03',
    d.name='通道 A（B 聚类 V3 视角）', d.view_group='V3',
    d.model='固定监控摄像机', d.status='在线',
    d.is_simulated=true, d.note='模拟档案；V3 视角，含画面缺证样例 0_te29/0_te16';
MATCH (d:Device {device_id:'DEV-A03'}), (a:Area {area_id:'AREA-A'})
MERGE (d)-[:LOCATED_IN {nature:'simulated'}]->(a);

// ---------- 5. 事件节点（含 video_file / time_range，满足"给定 ID 可查原片"） ----------
MERGE (e:Event {event_id:'EVT-0_te21-001'})
SET e.old_id='EVT-001', e.sample_id='0_te21', e.label_dir='0_safe_walkway_violation',
    e.video_file='0_te21.mp4', e.video_uri='saferaw://test/0_safe_walkway_violation/0_te21.mp4',
    e.time_range='1.0-8.5', e.start_time=1.0, e.end_time=8.5,
    e.time_source='B samples.csv 事件子区间（review_status=pending）',
    e.role='正例', e.view_group='V4', e.device_id='DEV-A01',
    e.occurred_at='2026-03-10', e.evidence_status='pending_review',
    e.work_order_status='present', e.is_simulated=false,
    e.note='主事件正例，配完整工单；与模拟业务档案为模拟关联';
MATCH (e:Event {event_id:'EVT-0_te21-001'}), (d:Device {device_id:'DEV-A01'})
MERGE (e)-[r:OCCURRED_ON]->(d)
SET r.nature='simulated', r.note='模拟关联：按 B 视角聚类分配机位，非真实物理设备对应';
MERGE (e:Event {event_id:'EVT-0_te23-001'})
SET e.old_id='EVT-002', e.sample_id='0_te23', e.label_dir='0_safe_walkway_violation',
    e.video_file='0_te23.mp4', e.video_uri='saferaw://test/0_safe_walkway_violation/0_te23.mp4',
    e.time_range='0.5-7.0', e.start_time=0.5, e.end_time=7.0,
    e.time_source='B samples.csv 事件子区间（review_status=pending）',
    e.role='正例', e.view_group='V2', e.device_id='DEV-A02',
    e.occurred_at='2026-03-10', e.evidence_status='business_gap',
    e.work_order_status='missing_business', e.is_simulated=false,
    e.note='正例；另用于业务缺证演示（故意无工单）；与模拟业务档案为模拟关联';
MATCH (e:Event {event_id:'EVT-0_te23-001'}), (d:Device {device_id:'DEV-A02'})
MERGE (e)-[r:OCCURRED_ON]->(d)
SET r.nature='simulated', r.note='模拟关联：按 B 视角聚类分配机位，非真实物理设备对应';
MERGE (e:Event {event_id:'EVT-4_te5-001'})
SET e.old_id='EVT-003', e.sample_id='4_te5', e.label_dir='4_safe_walkway',
    e.video_file='4_te5.mp4', e.video_uri='saferaw://test/4_safe_walkway/4_te5.mp4',
    e.time_range='3.8-9.8', e.start_time=3.8, e.end_time=9.8,
    e.time_source='B samples.csv 事件子区间（review_status=pending）',
    e.role='相似反例', e.view_group='V4', e.device_id='DEV-A01',
    e.occurred_at='2026-03-10', e.evidence_status='pending_review',
    e.work_order_status='present', e.is_simulated=false,
    e.note='同 V4 视角反例，验证误报排除；与模拟业务档案为模拟关联';
MATCH (e:Event {event_id:'EVT-4_te5-001'}), (d:Device {device_id:'DEV-A01'})
MERGE (e)-[r:OCCURRED_ON]->(d)
SET r.nature='simulated', r.note='模拟关联：按 B 视角聚类分配机位，非真实物理设备对应';
MERGE (e:Event {event_id:'EVT-4_te6-001'})
SET e.old_id='EVT-004', e.sample_id='4_te6', e.label_dir='4_safe_walkway',
    e.video_file='4_te6.mp4', e.video_uri='saferaw://test/4_safe_walkway/4_te6.mp4',
    e.time_range='0.5-6.5', e.start_time=0.5, e.end_time=6.5,
    e.time_source='B samples.csv 事件子区间（review_status=pending）',
    e.role='相似反例', e.view_group='V4', e.device_id='DEV-A01',
    e.occurred_at='2026-03-10', e.evidence_status='pending_review',
    e.work_order_status='present', e.is_simulated=false,
    e.note='同 V4 视角反例，验证误报排除；与模拟业务档案为模拟关联';
MATCH (e:Event {event_id:'EVT-4_te6-001'}), (d:Device {device_id:'DEV-A01'})
MERGE (e)-[r:OCCURRED_ON]->(d)
SET r.nature='simulated', r.note='模拟关联：按 B 视角聚类分配机位，非真实物理设备对应';
MERGE (e:Event {event_id:'EVT-0_te29-001'})
SET e.old_id='EVT-005', e.sample_id='0_te29', e.label_dir='0_safe_walkway_violation',
    e.video_file='0_te29.mp4', e.video_uri='saferaw://test/0_safe_walkway_violation/0_te29.mp4',
    e.time_range='0.0-6.5', e.start_time=0.0, e.end_time=6.5,
    e.time_source='B samples.csv 事件子区间（review_status=pending）',
    e.role='缺证（画面）', e.view_group='V3', e.device_id='DEV-A03',
    e.occurred_at='2026-03-10', e.evidence_status='insufficient',
    e.work_order_status='not_applicable_visual_gap', e.is_simulated=false,
    e.note='B 定义的缺证样例：目标过远过小，无法判读是否越界；与模拟业务档案为模拟关联';
MATCH (e:Event {event_id:'EVT-0_te29-001'}), (d:Device {device_id:'DEV-A03'})
MERGE (e)-[r:OCCURRED_ON]->(d)
SET r.nature='simulated', r.note='模拟关联：按 B 视角聚类分配机位，非真实物理设备对应';
MERGE (e:Event {event_id:'EVT-0_te16-001'})
SET e.old_id='EVT-006', e.sample_id='0_te16', e.label_dir='0_safe_walkway_violation',
    e.video_file='0_te16.mp4', e.video_uri='saferaw://test/0_safe_walkway_violation/0_te16.mp4',
    e.time_range='0.0-8.9', e.start_time=0.0, e.end_time=8.9,
    e.time_source='B samples.csv 事件子区间（review_status=pending）',
    e.role='缺证（画面）', e.view_group='V3', e.device_id='DEV-A03',
    e.occurred_at='2026-03-10', e.evidence_status='insufficient',
    e.work_order_status='not_applicable_visual_gap', e.is_simulated=false,
    e.note='B 定义的缺证样例：区间内无可判读人员目标；与模拟业务档案为模拟关联';
MATCH (e:Event {event_id:'EVT-0_te16-001'}), (d:Device {device_id:'DEV-A03'})
MERGE (e)-[r:OCCURRED_ON]->(d)
SET r.nature='simulated', r.note='模拟关联：按 B 视角聚类分配机位，非真实物理设备对应';

// ---------- 6. 工单节点（仅 3 条有授权工单；0_te23 业务缺证、0_te29/0_te16 画面缺证均无工单） ----------
MERGE (w:WorkOrder {work_order_id:'WO-20260310-01'})
SET w.event_id='EVT-0_te21-001', w.device_id='DEV-A01',
    w.authorized_by='张安全员', w.authorized_window='2026-03-10 08:00-10:00',
    w.work_type='通道巡检', w.is_simulated=true,
    w.note='模拟档案；有授权，核对齐备（V4）';
MATCH (e:Event {event_id:'EVT-0_te21-001'}), (w:WorkOrder {work_order_id:'WO-20260310-01'})
MERGE (e)-[:HAS_WORK_ORDER {nature:'simulated'}]->(w);
MERGE (w:WorkOrder {work_order_id:'WO-20260310-03'})
SET w.event_id='EVT-4_te5-001', w.device_id='DEV-A01',
    w.authorized_by='张安全员', w.authorized_window='2026-03-10 08:00-10:00',
    w.work_type='通道巡检', w.is_simulated=true,
    w.note='模拟档案；正常通行反例（V4）';
MATCH (e:Event {event_id:'EVT-4_te5-001'}), (w:WorkOrder {work_order_id:'WO-20260310-03'})
MERGE (e)-[:HAS_WORK_ORDER {nature:'simulated'}]->(w);
MERGE (w:WorkOrder {work_order_id:'WO-20260310-04'})
SET w.event_id='EVT-4_te6-001', w.device_id='DEV-A01',
    w.authorized_by='张安全员', w.authorized_window='2026-03-10 08:00-10:00',
    w.work_type='通道巡检', w.is_simulated=true,
    w.note='模拟档案；正常通行反例（V4）';
MATCH (e:Event {event_id:'EVT-4_te6-001'}), (w:WorkOrder {work_order_id:'WO-20260310-04'})
MERGE (e)-[:HAS_WORK_ORDER {nature:'simulated'}]->(w);

// ---------- 7. 缺证节点（业务缺证 vs 画面缺证，两种维度不可混为一条） ----------
MERGE (g:EvidenceGap {gap_id:'GAP-BIZ-0_te23'})
SET g.event_id='EVT-0_te23-001', g.gap_type='business', g.reason='missing_authorization_work_order', g.is_simulated=true,
    g.note='模拟档案；缺证判断用于验证补证前后结论变化';
MATCH (e:Event {event_id:'EVT-0_te23-001'}), (g:EvidenceGap {gap_id:'GAP-BIZ-0_te23'})
MERGE (e)-[:HAS_GAP {nature:'simulated'}]->(g);
MERGE (g:EvidenceGap {gap_id:'GAP-VIS-0_te29'})
SET g.event_id='EVT-0_te29-001', g.gap_type='visual', g.reason='target_not_judgeable', g.is_simulated=true,
    g.note='模拟档案；缺证判断用于验证补证前后结论变化';
MATCH (e:Event {event_id:'EVT-0_te29-001'}), (g:EvidenceGap {gap_id:'GAP-VIS-0_te29'})
MERGE (e)-[:HAS_GAP {nature:'simulated'}]->(g);
MERGE (g:EvidenceGap {gap_id:'GAP-VIS-0_te16'})
SET g.event_id='EVT-0_te16-001', g.gap_type='visual', g.reason='no_judgeable_person', g.is_simulated=true,
    g.note='模拟档案；缺证判断用于验证补证前后结论变化';
MATCH (e:Event {event_id:'EVT-0_te16-001'}), (g:EvidenceGap {gap_id:'GAP-VIS-0_te16'})
MERGE (e)-[:HAS_GAP {nature:'simulated'}]->(g);

// ---------- 8. 历史事件与整改节点（历史链 EVT-H01/H02/H03，事发 2025-06-10 命中 SOP v1.0） ----------
MERGE (h:HistoricalEvent {event_id:'EVT-H01'})
SET h.device_id='DEV-A01', h.occurred_at='2025-06-10',
    h.video_file='0_te21.mp4',
    h.time_range='1.0-8.5',
    h.is_simulated=true, h.note='模拟档案；事发 2025-06-10，按事发时间命中当时版本（V4）';
MERGE (rect:Rectification {rect_id:'RECT-EVT-H01'})
SET rect.event_id='EVT-0_te21-001', rect.history_event_id='EVT-H01',
    rect.action='加设通道地面标识并安排班前会宣贯', rect.sop_version='SOP_v1.0',
    rect.is_simulated=true, rect.note='模拟档案；事发 2025-06-10，按事发时间命中当时版本（V4）';
MATCH (e:Event {event_id:'EVT-0_te21-001'}), (h:HistoricalEvent {event_id:'EVT-H01'})
MERGE (e)-[rel:RELATED_HISTORY]->(h)
SET rel.relation_type='similar_case', rel.nature='simulated',
    rel.note='模拟关联：相似历史案例，非真实同一事件';
MATCH (d:Device {device_id:'DEV-A01'}), (h:HistoricalEvent {event_id:'EVT-H01'})
MERGE (d)-[:HAS_HISTORY {nature:'simulated'}]->(h);
MATCH (h:HistoricalEvent {event_id:'EVT-H01'}), (rect:Rectification {rect_id:'RECT-EVT-H01'})
MERGE (h)-[:HAS_RECTIFICATION {nature:'simulated'}]->(rect);
MERGE (h:HistoricalEvent {event_id:'EVT-H02'})
SET h.device_id='DEV-A02', h.occurred_at='2025-06-10',
    h.video_file='0_te23.mp4',
    h.time_range='0.5-7.0',
    h.is_simulated=true, h.note='模拟档案；历史事件用于演示补证后的判断变化（V2）';
MERGE (rect:Rectification {rect_id:'RECT-EVT-H02'})
SET rect.event_id='EVT-0_te23-001', rect.history_event_id='EVT-H02',
    rect.action='补录越界作业授权并复核当班巡检路线', rect.sop_version='SOP_v1.0',
    rect.is_simulated=true, rect.note='模拟档案；历史事件用于演示补证后的判断变化（V2）';
MATCH (e:Event {event_id:'EVT-0_te23-001'}), (h:HistoricalEvent {event_id:'EVT-H02'})
MERGE (e)-[rel:RELATED_HISTORY]->(h)
SET rel.relation_type='similar_case', rel.nature='simulated',
    rel.note='模拟关联：相似历史案例，非真实同一事件';
MATCH (d:Device {device_id:'DEV-A02'}), (h:HistoricalEvent {event_id:'EVT-H02'})
MERGE (d)-[:HAS_HISTORY {nature:'simulated'}]->(h);
MATCH (h:HistoricalEvent {event_id:'EVT-H02'}), (rect:Rectification {rect_id:'RECT-EVT-H02'})
MERGE (h)-[:HAS_RECTIFICATION {nature:'simulated'}]->(rect);
MERGE (h:HistoricalEvent {event_id:'EVT-H03'})
SET h.device_id='DEV-A01', h.occurred_at='2025-06-10',
    h.video_file='4_te5.mp4',
    h.time_range='3.8-9.8',
    h.is_simulated=true, h.note='模拟档案；反例侧历史事件，用于误报排除链验证（V4）';
MERGE (rect:Rectification {rect_id:'RECT-EVT-H03'})
SET rect.event_id='EVT-4_te5-001', rect.history_event_id='EVT-H03',
    rect.action='复核通道标线可视性并调整巡检路线', rect.sop_version='SOP_v1.0',
    rect.is_simulated=true, rect.note='模拟档案；反例侧历史事件，用于误报排除链验证（V4）';
MATCH (e:Event {event_id:'EVT-4_te5-001'}), (h:HistoricalEvent {event_id:'EVT-H03'})
MERGE (e)-[rel:RELATED_HISTORY]->(h)
SET rel.relation_type='similar_case', rel.nature='simulated',
    rel.note='模拟关联：相似历史案例，非真实同一事件';
MATCH (d:Device {device_id:'DEV-A01'}), (h:HistoricalEvent {event_id:'EVT-H03'})
MERGE (d)-[:HAS_HISTORY {nature:'simulated'}]->(h);
MATCH (h:HistoricalEvent {event_id:'EVT-H03'}), (rect:Rectification {rect_id:'RECT-EVT-H03'})
MERGE (h)-[:HAS_RECTIFICATION {nature:'simulated'}]->(rect);

// ---------- 9. 版本命中（历史事件 2025-06-10→v1.0；当前事件 2026-03-10→v2.0） ----------
MATCH (h:HistoricalEvent), (s:SOP {version:'v1.0'})
MERGE (h)-[g:GOVERNED_BY]->(s)
SET g.basis='事发时间 2025-06-10 命中 v1.0 生效期', g.nature='simulated';
MATCH (e:Event), (s:SOP {version:'v2.0'})
MERGE (e)-[g:GOVERNED_BY]->(s)
SET g.basis='事发时间 2026-03-10 命中 v2.0 生效期', g.nature='simulated';

// 导入完成。接着运行 验证查询.cypher 核对两条验收路径。
