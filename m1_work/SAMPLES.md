# M1 样例清单

生成时间：2026-11-23
数据来源：`datasets/Video Dataset for Safe and Unsafe Behaviours/Safe and Unsafe Behaviours Dataset`
（Safe and Unsafe Behaviours，Mendeley `xjmtb22pff`，官方划分 test 保持不用于训练）

## 一、首批样例（6 个事件，区间为人工复核）

| event_id | 原样本 | 划分 | 角色 | 区间(s) | 事件类型 | 证据状态 | 选样依据 |
|---|---|---|---|---|---|---|---|
| EVT-0_te21-001 | 0_te21 | test | 正例 | 1.00–8.50 | walkway_violation | insufficient | 人员沿绿色安全通道区域行走 |
| EVT-0_te23-001 | 0_te23 | test | 正例 | 0.50–7.00 | walkway_violation | insufficient | 人员沿通道标线区域行走，远端进入画面 |
| EVT-4_te5-001 | 4_te5 | test | 相似反例 | 3.80–9.80 | walkway_normal | insufficient | 同机位人员沿车间通道地面正常通行 |
| EVT-4_te6-001 | 4_te6 | test | 相似反例 | 0.50–6.50 | walkway_normal | insufficient | 同机位人员正常通行，未进入通道标线 |
| EVT-0_te29-001 | 0_te29 | test | 缺证 | 0.00–6.50 | walkway_violation | insufficient | 目标过远过小，无法判读是否进入通道区域 |
| EVT-0_te16-001 | 0_te16 | test | 缺证 | 0.00–8.90 | walkway_violation | insufficient | 区间内未见可判读的人员目标 |

区间来源写入 `events.json` 的 `range_source=manual_review`，对应
[samples.csv](./samples.csv)；关键帧时间取 `起点 / 中点 / 终点`。

> **这些区间尚未经人签字**（`review_status=pending`）。复核方式：看
> `out/review/<asset_id>.jpg`（区间内 6 帧联系表），确认后执行
> `python m1_work/review.py --confirm <asset_id> --by <复核人>`。

> 正例与相似反例使用**同一机位、同一时段**的不同行为，用于验证后续检测能否区分
> 「走在安全通道上」与「沿通道地面正常通行」。

## 二、全量清单概况

| 类别目录 | 语义 | 标签 | train | test | 合计 |
|---|---|---|---|---|---|
| `0_safe_walkway_violation` | 通道越界 | unsafe | 178 | 32 | 210 |
| `1_unauthorized_intervention` | 未授权干预 | unsafe | 97 | 11 | 108 |
| `2_opened_panel cover` | 面板开启 | unsafe | 129 | 13 | 142 |
| `3_carrying_overload_with_forklift` | 叉车超载搬运 | unsafe | 48 | 8 | 56 |
| `4_safe_walkway` | 通道正常通行 | safe | 50 | 25 | 75 |
| `5_authorized_intervention` | 授权干预 | safe | 23 | 15 | 38 |
| `6_closed_panel_cover` | 面板关闭 | safe | 19 | 13 | 32 |
| `7_safe_carrying` | 安全搬运 | safe | 22 | 8 | 30 |
| **合计** | | | **566** | **125** | **691** |

统一规格：1920×1080，H.264，9.31 GB，**全部无音轨**。逐条元数据见
`out/video_inventory.csv`（含有效帧率、时长、帧数、解码后端）。

## 三、主事件

**主事件锁定 `walkway_violation`（通道越界）。** 理由：

1. 正反例成对齐全（`0_*` vs `4_*`），test 划分有 32 : 25；
2. 画面中有明显的绿色通道区域与黄色标线，可人工划定判定区域；
3. 行为可判读，不需要依赖设备台账即可核对画面。

### 通道区域从哪里来（重要）

**数据集没有提供任何空间标注。** 实测 691 个文件全部是 mp4，非视频文件 0 个：
没有多边形、没有检测框、没有区域坐标、没有相机参数、没有文字描述。
唯一的标签就是 8 个目录名，粒度是「整段片段」，只能回答
「这一段属于安全/不安全通道行为」，**不能回答「画面里哪块是安全通道」**。

因此通道区域必须由我们自己定义，并且这个定义要独立冻结、可追溯：

| 事项 | 现状 | 结论 |
|---|---|---|
| 区域来源 | 数据集无 | 需人工在画面中划线（D3 起） |
| 可辅证方法 | — | 绿色漆面可用颜色阈值稳定分割（约占画面 4.0%，边界清晰） |
| 是否通用 | — | **不通用**，必须按机位（视角）分别定义 |

### 机位（视角）分组

对 test 下 `0_safe_walkway_violation` + `4_safe_walkway` 共 57 段做背景中值帧聚类
（160×90 灰度，平均绝对差 < 8 归为同一视角）：

| 视角 | 段数 | 包含 clip |
|---|---|---|
| V1 | 25 | 0_te1、0_te2…0_te6、0_te12–14、0_te18–20、0_te25–28、4_te10–18 |
| V2 | 13 | 0_te22、0_te23、4_te1–3、4_te7–9、4_te21–25 |
| V3 | 8 | 0_te15–17、0_te24、0_te29–32 |
| V4 | 4 | 0_te21、4_te5、4_te6、4_te20 |
| V5 | 3 | 0_te7–9 |
| V6 | 2 | 0_te10、0_te11 |

其余为单一视角片段。**同一视角内正反例才可比**：`0_te21` ↔ `4_te5/4_te6`（V4）、
`0_te23` ↔ `4_te9`（V2，背景差 0.00）。跨视角比较只能说明「都像通道」，
不能作为误报依据。

> 注意：`4_te9` 与 `0_te23` 同视角，且两者在 1.5/3/4.5/6 s 的画面几乎一致，
> 人员在远处过小，肉眼难以分辨行为差异。这一对必须靠 VLM 核验或放大后人工确认，
> 不能凭联系表直接判为反例。

**当前决定：M1 阶段不划 zone、不判越界。** M1 只做「事件能回放」，区域定义与越界
判定推迟到 D3，与检测模型一并接入；在此之前所有事件的 `evidence_status` 保持
`insufficient`，不输出「是否越界」的结论。

## 四、缺口说明

| 缺口 | 影响 | 应对 |
|---|---|---|
| `camera_id` / `area_id` 未定 | 事件卡字段为 UNKNOWN | 待数据图谱侧给编码规则后填充 |
| 全部无音轨 | 语音交互无素材 | 中文现场对话必须受控自采 |
| 无区域多边形标注 | 无法自动判定越界 | D3 起人工划定通道区域（`zones/`） |
| 缺证样例为「目标不可判读」 | 未覆盖遮挡/光照异常 | D8 从长片截取遮挡区间或用受控录制补充 |
| 单段最长约 15 s | 无法验证长时连续检索 | 历史检索另用拼接回放序列，并标注为模拟 |
| 6 条样例均未签字 | 不能作为冻结评测集 | 复核人看 `out/review/*.jpg` 后 `review.py --confirm` |

## 五、待团队确认

1. `camera_id` / `area_id` 编码规则（阻塞 M2 事件卡字段）。
2. 评测口径：召回率以「视频段」还是「事件」为单位计数。
3. 缺证样例的验收标准：`evidence_status=insufficient` 时允许输出的信息边界。
4. 6 条样例的区间与角色（见 `samples.csv` 的 `review_status` 列），需复核人签字。
