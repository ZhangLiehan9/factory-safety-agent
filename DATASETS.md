# 数据集盘点与可用性说明

> 面向：车间安全资产认知智能体项目组全体成员
> 更新：2026-11-19
> 数据位置：`/data2/xsq/ICT_datasets/`
> 校验清单：`subset_manifest.csv`（69 个文件，路径 + 字节数 + SHA-256）
> 全量数据：`archive.zip`（691 个视频，9.31 GB，已通过 CRC + 官方清单双重校验）

---

## 0. 一句话结论

| 数据集 | 与车间安全的相关性 | 能干什么 | 不能干什么 |
|---|---|---|---|
| **SafeUnsafe** | ★★★★★ 强相关 | 视频事件检测主链路 | 无音轨、无区域/设备标注 |
| **InspecSafe** | ★★★★☆ 强相关 | 隐患语义知识库、多模态演示 | 单帧图，无时间维度 |
| **IndEgo** | ★★★☆☆ 中等 | 检修工序上下文、**唯一可用人声音频** | 不是安全隐患数据 |
| **iSafetyBench** | ★☆☆☆☆ 弱相关 | 通用危险动作参考 | 英文通用工地，非车间 |

**核心判断**：只有 **SafeUnsafe** 是「车间场景 + 视频 + 安全/不安全标签」三者齐全的，是事件检测的唯一主数据源。其余三个各有用途，但都不能替代它。

---

## 1. SafeUnsafe —— 主数据源

### 1.0 全量数据（`archive.zip`，已就位）

| 项 | 值 |
|---|---|
| 文件 | `archive.zip`（10.0 GB 压缩包） |
| 内容 | **691 个 mp4，解压后 9.31 GB** |
| 来源 | Mendeley Data `10.17632/xjmtb22pff.1` |
| 完整性 | ✅ `unzip -t` 无错误；✅ 691/691 文件 CRC 通过；✅ 与官方 API 清单逐条比对（文件名 + 字节数）**零差异** |
| 官方划分 | `train/` 566 个 + `test/` 125 个 |
| 解压路径 | `Video Dataset for Safe and Unsafe Behaviours/Safe and Unsafe Behaviours Dataset/{train,test}/<类别>/` |

**8 个类别完整分布**（此前子集只有 0/2/4/6 四类，现已补齐 1/3/5/7）：

| 类别目录 | 语义 | train | test | 合计 | 大小 |
|---|---|---|---|---|---|
| `0_safe_walkway_violation` | 通道越界（**不安全**） | 178 | 32 | 210 | 3.26 GB |
| `1_unauthorized_intervention` | 未授权干预（**不安全**） | 97 | 11 | 108 | 1.76 GB |
| `2_opened_panel cover` | 面板开启（**不安全**） | 129 | 13 | 142 | 1.41 GB |
| `3_carrying_overload_with_forklift` | 叉车超载搬运（**不安全**） | 48 | 8 | 56 | 0.89 GB |
| `4_safe_walkway` | 通道正常通行（安全） | 50 | 25 | 75 | 1.10 GB |
| `5_authorized_intervention` | 授权干预（安全） | 23 | 15 | 38 | 0.52 GB |
| `6_closed_panel_cover` | 面板关闭（安全） | 19 | 13 | 32 | 0.24 GB |
| `7_safe_carrying` | 安全搬运（安全） | 22 | 8 | 30 | 0.12 GB |
| **合计** | | **566** | **125** | **691** | **9.31 GB** |

> **安全/不安全配对关系**（可用于正反例对照）：
> - 通道：`0_safe_walkway_violation`（不安全） ↔ `4_safe_walkway`（安全）
> - 面板：`2_opened_panel cover`（不安全） ↔ `6_closed_panel_cover`（安全）
> - 干预：`1_unauthorized_intervention`（不安全） ↔ `5_authorized_intervention`（安全）
> - 搬运：`3_carrying_overload_with_forklift`（不安全） ↔ `7_safe_carrying`（安全）

### 1.1 子集基本信息（`SafeUnsafe_subset/`，M1 已用）

| 项 | 值 |
|---|---|
| 体积 | 37.9 MB / 12 个文件 |
| 来源 | Mendeley Data `xjmtb22pff` |
| 官方划分 | test（保持官方 test 属性，**不得用于训练**） |
| 许可校验 | 全部通过官方 SHA-256 |
| 目录 | `SafeUnsafe_subset/test/<标签目录>/` |

### 1.2 视频清单（8 段，全部 1920×1080 H.264，**全部无音轨**）

| 文件 | 标签目录 | 语义 | 时长 | 帧数 | 帧率 |
|---|---|---|---|---|---|
| `0_te21.mp4` | `0_safe_walkway_violation` | 通道越界（不安全） | 10.452s | 252 | 25 |
| `0_te23.mp4` | `0_safe_walkway_violation` | 通道越界（不安全） | 10.478s | 241 | 25 |
| `2_te12.mp4` | `2_opened_panel cover` | 面板开启（不安全） | 10.415s | 261 | 25 |
| `2_te13.mp4` | `2_opened_panel cover` | 面板开启（不安全） | 2.998s | 75 | **25.02** |
| `4_te5.mp4` | `4_safe_walkway` | 通道正常（安全） | 10.440s | 262 | 25 |
| `4_te6.mp4` | `4_safe_walkway` | 通道正常（安全） | 10.414s | 260 | 25 |
| `6_te10.mp4` | `6_closed_panel_cover` | 面板关闭（安全） | **1.840s** | 46 | 25 |
| `6_te12.mp4` | `6_closed_panel_cover` | 面板关闭（安全） | 10.437s | 260 | 25 |

### 1.3 标签映射（`m1_work/inventory.py` 的 `LABEL_MAP` 目前只覆盖 4 类）

**已固化（子集用到的 4 类）**：

```
0_safe_walkway_violation  →  (unsafe, walkway_violation)
4_safe_walkway            →  (safe,   walkway_normal)
2_opened_panel cover      →  (unsafe, panel_opened)
6_closed_panel_cover      →  (safe,   panel_closed)
```

**全量数据新增的 4 类（待补入 `LABEL_MAP`）**：

```
1_unauthorized_intervention          →  (unsafe, unauthorized_intervention)
5_authorized_intervention            →  (safe,   authorized_intervention)
3_carrying_overload_with_forklift    →  (unsafe, carrying_overload)
7_safe_carrying                      →  (safe,   safe_carrying)
```

> ⚠️ 使用全量数据前，需先把这 4 条补进 `m1_work/inventory.py` 的 `LABEL_MAP`，否则 `inventory.py` 会跳过这些目录。

### 1.4 使用建议

- **主事件正例**：`0_te21`、`0_te23`（通道越界，建议作为主事件）
- **相似反例**：`4_te5`、`4_te6`（同为通道场景但正常通行，用于验证误报）
- **备选**：`2_te12`、`2_te13`、`6_te10`、`6_te12`（面板开闭）

### 1.5 已知缺陷（务必注意）

| 缺陷 | 影响 | 应对 |
|---|---|---|
| **全部无音轨** | 音频链路无素材 | 语音交互必须自采 |
| `6_te10` 仅 1.84s | 太短，做不了完整事件 | 只作补充，不作主样例 |
| `2_te13` 帧率 25.02（1251/50） | 与其他 25fps 不一致 | 时间换算需按实际帧率 |
| 无 `camera_id` / `area_id` | 事件卡字段为空 | 待与数据图谱侧对齐 |
| 无区域边界标注 | 无法自动判定"越界" | 需人工划定通道多边形 |
| 容器时长 ≠ 可解码时长 | 末帧抽取失败 | 已在 `extract.py` 加回退重试 |

---

## 2. InspecSafe_subset —— 隐患语义知识库

### 2.1 基本信息

| 项 | 值 |
|---|---|
| 体积 | 41.8 MB / 40 个文件 |
| 来源 | HuggingFace `Tetrabot2026/InspecSafe-V1` |
| 场景 | 煤廊、隧道、电力、油化（**工业场景，比 SafeUnsafe 更贴题**） |
| 模态 | 单帧图像 + LabelMe 多边形 + 自然语言隐患描述 + 多模态传感器 |

### 2.2 图像与标注（10 张，**是单帧图不是视频**）

| 文件 | 场景 | 尺寸 | 类型 |
|---|---|---|---|
| `coal_conveyor-Level01-SuspendedRail-002245-001` | 煤廊 | 2688×1520 | 异常 |
| `coal_conveyor-Level02-SuspendedRail-002312-001` | 煤廊 | 1920×1080 | 异常 |
| `coal_conveyor-Level04-SuspendedRail-000026-001` | 煤廊 | 2560×1440 | 正常 |
| `tunnel-Level01-SuspendedRail-002416-001` | 隧道 | 1920×1080 | 异常 |
| `tunnel-Level02-SuspendedRail-002456-001` | 隧道 | 1920×1080 | 异常 |
| `power-Level02-SuspendedRail-002403-001` | 电力 | 1920×1080 | 异常 |
| `oil_chemical-Level01-Wheeled-002355-001` | 油化 | 1920×1080 | 异常 |
| `oil_chemical-Level02-Wheeled-002386-001` | 油化 | 1917×1080 | 异常 |
| `oil_chemical-Level04-Wheeled-000312-001` | 油化 | 1920×1080 | 正常 |
| `oil_chemical-Level04-Wheeled-000312-002` | 油化 | 1920×1080 | 正常 |

### 2.3 标注格式

**LabelMe 多边形 JSON**（`shapes[].label` + `points`），共 26 类标签：

```
Bolt(10)  Person(9)  Pipeline(6)  Radiator(6)  Stent(5)  Idler Roller(4)
Fire Hydrant(3)  Motor(3)  Guardrail(3)  Window(3)  Cigarette(2)
Safety Helmet(2)  Stairs(2)  Belt(2)  Railing(2)  Lamp(2)  Flange(2)
Shutoff Valve(2)  Electrical Box(1)  Open Flame(1)  Plastic Bottle(1)
Equipment Container(1)  Power Box(1)  Mobile Phone(1)  Protective Net(1)  Liquid(1)
```

**自然语言隐患描述 + 安全等级**（`.txt`），例如：

> "In the coal conveying bridge scenario, the potential hazards in the image are personnel smoking and not wearing gloves. Therefore, the safety level is Grade One."

> "In the oil and gas chemical scenario, the cabinet door is abnormally open. Therefore, the safety level is Grade 2."

> "In the coal conveyor bridge scene, a person wearing a safety helmet stands near the railing beside the belt supported by idler rollers and stents, with a lamp overhead, no abnormalities observed."

**这个「场景 + 隐患 + 等级」结构，正好对应事件卡的「观察 + 判定」字段。**

### 2.4 多模态数据（仅 2 个巡检点）

`oil_chemical-Level04-Wheeled-000312` 是唯一多模态齐全的样本：

| 模态 | 文件 | 规格 |
|---|---|---|
| 可见光 | `-visible.mp4` | 1920×1080, 25fps, 13.28s |
| 红外 | `-infrared.mp4` | 1280×1024, 25fps, 13.28s |
| **音频** | `-audio.wav` | pcm_s16le, **8000Hz 双声道**, 15.0s |
| 点云 | `-point_cloud.bag` | ROSBAG V2.0, 1.1MB |
| 传感器 | `-sensor.txt` | JSON，见下 |

**传感器字段**（`env` 数组，带报警阈值）：

| 字段 | 单位 | 阈值 | coal_conveyor 实测 | oil_chemical 实测 |
|---|---|---|---|---|
| temperature | ℃ | 150 | 22.0 | **0.0** |
| humidity | % | 150 | 62.2 | **0.0** |
| smog | — | 150 | 0.0 | 0.0 |
| pm2D5 | ug/m3 | 150 | 4.0 | 0.0 |
| pm1D0 | ug/m3 | 150 | 3.0 | — |
| pm10 | ug/m3 | 150 | 4.0 | — |
| CH4 | %VOL | 150 | 0.0 | — |
| CO | PPM | 16 | 0.0 | **0.0** |
| O2 | %VOL | 19 | 20.2 | **0.0** |
| H2S | PPM | 1 | 0.0 | — |

### 2.5 已知缺陷

| 缺陷 | 影响 |
|---|---|
| **单帧图，无时间维度** | 做不了"事件"（事件需 start/end） |
| 只有 10 张图 | 样本量太小，不能训练 |
| 多模态仅 1 个巡检点齐全 | 不能做多模态泛化验证 |
| `oil_chemical` 传感器值**全为 0** | **不能用于传感器异常检测验证** |
| 无正常样本的完整多模态 | 正常/异常对比受限 |

### 2.6 推荐用途

- **事件卡话术库**：给 `walkway_violation`、`panel_opened` 等事件补充标准化隐患描述和安全等级
- **多模态演示**：用 `oil_chemical-Level04` 展示可见光+红外+音频+点云+传感器的融合能力
- **标签体系参考**：26 类工业部件标签可作为设备台账的命名参考

---

## 3. IndEgo_subset —— 检修工序上下文

### 3.1 基本信息

| 项 | 值 |
|---|---|
| 体积 | 79.9 MB / 7 个文件 |
| 来源 | HuggingFace `FraunhoferIPK/IndEgo` |
| 内容 | 第一人称（ego）工业设备检修视频 |
| 校验 | 全部通过官方 SHA-256 |

### 3.2 视频清单（3 段，**均有 44.1kHz 双声道音频**）

| 文件 | 时长 | 分辨率 | 帧率 | 音频 |
|---|---|---|---|---|
| `User_15_410_0511_1_480.mp4` | 299.0s | 480×480 | 10 | mp3 44.1kHz 双声道 |
| `User_17_410_0511_1_480.mp4` | 277.8s | 480×480 | 10 | mp3 44.1kHz 双声道 |
| `User_17_User_1_407_2910_1_480.mp4` | 300.1s | 480×480 | 10 | mp3 44.1kHz 双声道 |

### 3.3 标注（VIA 格式，工序时间区间）

标注属性 `steps` 有三个取值：`00_inspect` / `01_repair` / `02_test`

| 标注文件 | 对应视频 | 区间数 | 首段区间 |
|---|---|---|---|
| `AS_User_15_410_0511_1.json` | ✅ `User_15_410_0511_1_480.mp4` | 3 | 7.798–29.966s |
| `AS_User_17_410_0511_1.json` | ✅ `User_17_410_0511_1_480.mp4` | 4 | 4.058–57.726s |
| `AS_User_17_User_1_407_2910_1.json` | ✅ `User_17_User_1_407_2910_1_480.mp4` | 3 | 8.105–57.739s |
| `AS_User_14_2325_451.json` | ❌ **无对应视频** | 2 | 14.521–94.743s |

> ⚠️ `AS_User_14_2325_451.json` 对应的 `User_14_2325_451_480.mp4` **不在子集中**，不可配对使用。

### 3.4 音频可用性实测

对前 60 秒做能量分析：

| 文件 | RMS | 帧能量范围 | 静音帧占比 |
|---|---|---|---|
| `User_15_410_0511_1_480` | 76.8 | 4.9 – 297.6 | 57% |
| `User_17_410_0511_1_480` | 110.4 | 4.5 – 919.3 | 60% |
| `User_17_User_1_407_2910_1_480` | 16.0 | 1.6 – 92.0 | 98% |

**结论**：前两段有真实声音内容（能量波动明显），第三段基本静音。**这是整个数据集里唯一可用的长时人声音频素材**（约 10 分钟有效内容）。

### 3.5 推荐用途

- **M4 历史检索**：作为"设备检修记录"的模拟素材
- **音频链路验证**：验证 ASR / 语音交互流程（虽然是英文/德语，但可验证技术链路）
- **工序理解**：`inspect → repair → test` 的时序结构可参考用于事件卡的状态机设计

### 3.6 已知缺陷

| 缺陷 | 影响 |
|---|---|
| 480×480 低分辨率 | 不适合视觉检测 |
| 10fps 低帧率 | 动作识别受限 |
| 是"检修工序"不是"安全隐患" | 不能做安全事件检测 |
| 音频非中文 | 不能直接用于中文语音交互 |
| 1 个标注文件无对应视频 | 需剔除 |

---

## 4. iSafetyBench_subset —— 弱相关参考

### 4.1 基本信息

| 项 | 值 |
|---|---|
| 体积 | 7.8 MB / 10 个文件 |
| 来源 | HuggingFace `raiyaanabdullah/isafety-bench` + GitHub `iSafetyBench/data` |
| 内容 | YouTube 裁剪片段，**英文通用工地场景** |

### 4.2 视频清单（7 段，均有音轨）

| 文件 | 类别 | 时长 | 分辨率 | 帧率 |
|---|---|---|---|---|
| `-0zRCAh9_N4_trim_0.mp4` | hazard | 6.024s | 640×352 | 25.11 |
| `0QHQ2nmdE78_clip0_trim_2.mp4` | hazard | 7.024s | 1280×720 | 30 |
| `-BzGMvclD88_trim_1.mp4` | hazard | 5.024s | 1280×720 | 30 |
| `0jbAwaxJlCU_trim_0.mp4` | normal | 8.024s | 360×640 | 30 |
| `0XutYYk-0Uc_trim_0.mp4` | normal | 5.024s | 1280×720 | 30 |
| `0a-WuC1Xdl4_trim_0.mp4` | normal | 8.024s | 1280×720 | 29.97 |
| `0JyepVxTNTg_trim_0.mp4` | normal | 5.012s | 640×480 | 30 |
| `0E-P6HrYYQI_trim_0.mp4` | normal | 6.024s | 1280×720 | 25 |

### 4.3 标注

格式极简：`{video_name, caption, gt_actions[]}`

- `annotations_hazard.json`：**420 条**
- `annotations_normal.json`：**680 条**

**危险动作类别分布（Top 15）**：

```
escaping from danger                    75
watching incident passively             73
fire incident                           73
rescue effort                           68
falling load                            62
person falling down                     48
operating forklift                      36
extinguishing fire                      34
structural collapse                     27
vehicle losing control                  22
carrying heavy load                     22
intention of theft                      18
operating heavy equipment dangerously   17
misusing lift platform                  17
heavy object slipping                   16
```

### 4.4 关键问题

| 问题 | 说明 |
|---|---|
| **标注数 ≫ 视频数** | 1100 条标注 vs 7 段视频。标注是**全量数据集**的，不是子集的 |
| **场景不匹配** | 屋顶坍塌、火灾、叉车——通用工地，不是车间 |
| **英文** | caption 和动作标签全英文 |
| **分辨率参差** | 360×640 到 1280×720 不等 |

### 4.5 推荐用途

- 仅作**危险动作类别体系参考**（可借鉴其动作分类思路）
- **不建议**用于车间场景的检测或评测

---

## 5. 跨数据集对比

### 5.1 模态覆盖

| 模态 | SafeUnsafe | InspecSafe | IndEgo | iSafetyBench |
|---|---|---|---|---|
| 视频 | ✅ 8 段 | ✅ 2 段（多模态点） | ✅ 3 段 | ✅ 7 段 |
| 图像 | — | ✅ 10 张 | — | — |
| **音频** | ❌ **无** | ✅ 1 段 8kHz | ✅ 3 段 44.1kHz | ✅ 有 |
| 红外 | — | ✅ 2 段 | — | — |
| 点云 | — | ✅ 1 个 bag | — | — |
| 传感器 | — | ✅ 2 份 | — | — |
| 时间区间标注 | ❌ | ❌ | ✅ | ❌ |
| 安全/不安全标签 | ✅ | ✅（等级） | ❌ | ✅ |

### 5.2 场景匹配度

```
SafeUnsafe    ████████████████████  车间（通道/面板）
InspecSafe    ██████████████████    工业（煤廊/隧道/电力/油化）
IndEgo        ████████              工业设备检修
iSafetyBench  ████                  通用工地（英文）
```

---

## 6. 对里程碑的影响

| 里程碑 | 数据是否够用 | 说明 |
|---|---|---|
| **M1 视频链路** | ✅ 够 | 已跑通，8/8 解码，24/24 关键帧 |
| **M2 事件卡/MCP** | ✅ 够 | 8 个候选事件可做 |
| **M3 中文语音交互** | ❌ **不够** | **无中文人声素材，必须自采** |
| **M4 历史检索** | ⚠️ 部分 | 需自造模拟档案（IndEgo 可作检修记录素材） |
| **M5 评测冻结** | ⚠️ 偏小 | 8 段视频做评测集偏小，建议按采集场次划分 |
| **M6 演示** | ✅ 够 | InspecSafe 多模态可增强演示效果 |

---

## 7. 必须遵守的约束

摘自 `下载说明.md`，全体成员需知晓：

1. **这些数据用于初期联调，不代表正式评测集。**
2. **SafeUnsafe 保持官方 test 属性**，不得用于训练后又在同样样本上报告测试成绩。
3. **按原视频或采集场次划分开发与评测**，不能随机划分。
4. **中文现场双轮语音必须受控自采。**
5. **设备台账、工单、整改及两版 SOP 必须独立生成并标明模拟。**
6. **公开片段与模拟档案之间的关系不得称为真实关联。**

---

## 8. 待团队确认事项

| 事项 | 建议 | 负责方 |
|---|---|---|
| 主事件确认 | `walkway_violation` | 音视频组 + 项目负责人 |
| 区域定义 | 在画面中划定通道边界多边形 | 音视频组 |
| 设备映射 | panel 事件需与设备 ID 对齐 | 数据图谱组（C） |
| `camera_id`/`area_id` 填充 | 待 C 侧提供编码规则 | 数据图谱组（C） |
| 中文语音素材采集 | 需尽快启动，M3 阻塞项 | 音视频组 |
| 模拟档案生成规范 | 需明确"模拟"标注方式 | 项目负责人 |

---

## 附：文件索引

| 文件 | 说明 |
|---|---|
| `subset_manifest.csv` | 69 个文件的路径/字节数/SHA-256 |
| `下载说明.md` | 数据来源、下载过程、使用约束（**必读**） |
| `m1_work/README.md` | M1 实现说明与验收对照 |
| `m1_work/SAMPLES.md` | SafeUnsafe 样例清单与用法分类 |
| `m1_work/out/video_inventory.json` | 8 段视频元数据 |
| `m1_work/out/events.json` | 8 个候选事件 |
| `m1_work/out/frames/` | 24 张关键帧 |
