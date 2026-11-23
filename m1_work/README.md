# M1 视频最小链路

目标：**给定视频 → 产出固定 `event_id` 的候选事件 → 关键帧与时间区间 → 能跳回原片回放。**

M1 不包含检测模型、VLM、语音与历史检索，全部用 CPU 完成。

## 快速开始

```powershell
cd D:\factory-safety-agent
$env:PYTHONIOENCODING='utf-8'      # 避免中文输出乱码

python m1_work\run_m1.py           # 全量 691 段：清单 → 事件 → 回放验证 → 验收报告
python m1_work\run_m1.py --splits test   # 只跑评测划分（125 段）
python m1_work\run_m1.py --limit 20      # 冒烟测试
python m1_work\run_m1.py --require-review  # 冻结验收：人工复核未签字则判不通过
```

单独使用各步骤：

```powershell
python m1_work\inventory.py --splits test         # 视频清单
python m1_work\events.py                          # 按 samples.csv 生成候选事件
python m1_work\play.py --list                     # 列出事件
python m1_work\play.py --event-id EVT-0_te29-001  # 按 ID 回放原片区间
python m1_work\extract.py --asset-id VID-SAFE-0_te21 --start 1.0 --end 8.5 --clip-out m1_work\out\clips\x.mp4
python m1_work\review.py                          # 生成复核联系表 + 待复核清单
python m1_work\review.py --confirm VID-SAFE-0_te21 --by 张三   # 写入复核记录
python -m pytest tests -q                         # 单元测试
```

## 需要人工确认的部分

M1 里有三件事**必须由人做**，代码只能辅助，不能替代：

| 事项 | 为什么必须人工 | 怎么做 | 卡住什么 |
|---|---|---|---|
| **样例区间与角色签字** | 区间是「哪一段算事件」的判断，模型给不出可信答案；签了才能当评测基准 | 看 `out/review/<asset_id>.jpg`（区间内 6 帧联系表），确认后执行 `review.py --confirm` | M1 冻结（`--require-review` 不通过）；M5 评测口径 |
| **主事件确认** | 决定整条链路做成什么事件，换成本极高 | 团队确认 `walkway_violation`（通道越界） | 全部后续工作 |
| **`camera_id` / `area_id` 编码规则** | 需要与数据图谱侧台账一致，否则事件卡无法关联设备 | C 侧给编码规则，代码里替换 `CAM-UNKNOWN` | M2 事件卡字段、M4 历史检索 |

另外两项属于 D3 之后、非 M1 范围，但同样只能人工：

- **通道区域多边形标注**：在画面里划出限制区，供越界判定用（`zones/*.json`）。
- **中文现场语音采集**：本数据集 691 段全部无音轨，两轮追问必须自录音频。

### 复核流程

```powershell
python m1_work\review.py                            # 1. 生成 6 张联系表
# 2. 打开 m1_work/out/review/*.jpg 逐张看片
python m1_work\review.py --confirm VID-SAFE-0_te21 --by 张三
python m1_work\review.py --reject  VID-SAFE-0_te16 --by 张三 --note "区间内实际有人"
python m1_work\run_m1.py --require-review           # 3. 冻结验收
```

复核结论写回 [samples.csv](./samples.csv) 的 `review_status / reviewed_by / reviewed_at /
review_note` 四列，并作为 `annotation_review` 字段进入 `events.json`，因此可追溯、可复核，
也不会因为重跑而丢失。

换机器时只需指定数据集根目录，代码不用改：

```powershell
$env:DATASET_ROOT = 'D:\data\Safe and Unsafe Behaviours Dataset'
```

## 目录

```
m1_work/
├── config.py          # 唯一配置源：数据集根、输出目录、schema 版本
├── paths.py           # saferaw:// URI <-> 本地绝对路径
├── decode.py          # 解码后端：元数据/抽帧(cv2)、片段导出(ffmpeg 或 cv2)
├── inventory.py       # 视频清单：解码检查 + 元数据
├── extract.py         # 抽帧与时间定位
├── events.py          # 候选事件生成
├── play.py            # 按 event_id 回放原片证据
├── review.py          # 人工复核：生成联系表 + 写回签字记录
├── run_m1.py          # 一键跑通 + 验收报告
├── samples.csv        # 人工标注的正例/反例/缺证样例（区间 + 复核签字）
└── out/
    ├── video_inventory.json / .csv
    ├── events.json
    ├── mappings/clip_map.csv    # 原片 ↔ 派生片段映射
    ├── review/<asset_id>.jpg    # 复核联系表（人工看片用）
    ├── frames/<asset_id>/       # 关键帧（可重新生成，不入库）
    └── clips/                   # 派生片段（可重新生成，不入库）
```

## 输出契约

### 视频清单 `video_inventory.json`

```json
{
  "schema_version": "1.1",
  "root": "...Safe and Unsafe Behaviours Dataset",
  "total": 691, "decodable": 691, "degraded": 691,
  "videos": [{
    "asset_id": "VID-SAFE-0_te21",
    "split": "test",
    "label_dir": "0_safe_walkway_violation",
    "label": "unsafe",
    "event_type": "walkway_violation",
    "video_uri": "saferaw://test/0_safe_walkway_violation/0_te21.mp4",
    "width": 1920, "height": 1080,
    "fps": 24.112, "effective_fps": 24.112,
    "duration": 10.4512, "nb_frames": 252,
    "has_audio": false, "decodable": true,
    "metadata_source": "cv2", "degraded": true
  }]
}
```

### 候选事件 `events.json`

```json
{
  "event_id": "EVT-0_te29-001",
  "schema_version": "1.1",
  "asset_id": "VID-SAFE-0_te29",
  "split": "test",
  "video_uri": "saferaw://test/0_safe_walkway_violation/0_te29.mp4",
  "start_time": 0.0,
  "end_time": 6.5,
  "time_base": "original_video",
  "offset_from_original": 0.0,
  "camera_id": "CAM-UNKNOWN",
  "area_id": "AREA-UNKNOWN",
  "event_type": "walkway_violation",
  "observations": ["目标过远过小，无法判读是否进入通道区域"],
  "facts": [],
  "inferences": [],
  "evidence_status": "insufficient",
  "insufficient_reason": "target_not_judgeable",
  "confidence": null,
  "keyframes": [
    {"time": 3.25, "actual_time": 3.2622,
     "path": "m1_work/out/frames/VID-SAFE-0_te29/kf_0003_250.jpg", "status": "ok"}
  ],
  "label_source": "dataset_label",
  "detector": "manual_annotation",
  "sample_role": "insufficient",
  "range_source": "manual_review",
  "annotation_review": {
    "status": "pending",
    "reviewed_by": null,
    "reviewed_at": null,
    "note": null
  },
  "is_simulated": false
}
```

关键字段约定：

| 字段 | 约定 |
|---|---|
| `event_id` | `EVT-<原始样本ID>-<序号>`，重跑不漂移 |
| `video_uri` | `saferaw://<split>/<label_dir>/<file>`，与机器无关；目录名空格编码为 `%20` |
| `time_base` | 恒为 `original_video`，所有时间都是原片时间 |
| `offset_from_original` | 派生片段第 0 秒对应的原片时间，等于 `start_time` |
| `keyframes[].status` | `ok` / `clamped`（超出可解码末尾，用末帧代替）/ `out_of_range` / `extract_failed` |
| `facts` / `inferences` | 画面可见事实与模型推断分字段，M1 均为空 |
| `evidence_status` | M1 统一为 `insufficient`，因为尚未做过检测与核验；原因写入 `insufficient_reason` |
| `label_source` | `dataset_label`：事件类型来自目录标签，不是模型判断 |
| `annotation_review` | 复核签字记录；`status=confirmed` 才可确认区间有效 |

### 原片↔片段映射 `mappings/clip_map.csv`

`clip_id, clip_path, event_id, asset_id, video_uri, start_time, end_time,
offset_from_original, duration, clip_duration_actual, duration_error, codec, backend, created_at`

`duration_error` 是片段实际时长与区间时长的差，用于证明切片没有错位。

## 解码后端

| 操作 | 实现 | 说明 |
|---|---|---|
| 元数据 | `ffprobe`（若已安装）→ 否则 `cv2.VideoCapture` | 未装 ffprobe 时 `metadata_source=cv2`、`degraded=true` |
| 抽帧 | `cv2` 顺序解码一次 | 实测随机 seek 43.5 ms/帧 vs 顺序解码 3.9 ms/帧，所以按帧号截取 |
| 片段导出 | `ffmpeg`（libx264 重编码）→ 否则 `cv2`（mp4v） | 不用 `-c copy`：只能从关键帧起切，短片段会偏移近 1 秒 |

**帧率口径**：`effective_fps = nb_frames / duration`。本数据集容器标称帧率（如 25）
与实际不符（如 24.11），用标称帧率换算时间会在 10 秒片子累积约 0.4 秒误差。

## M1 验收对照（本机实测）

| 检查项 | 标准 | 实测 |
|---|---|---|
| 候选事件 | 正例/反例/缺证各 ≥1 | 6 个：正例 2、反例 2、缺证 2 |
| 视频解码 | 候选视频全部可解码 | 691/691 |
| 原片可定位 | `video_uri` 全部可解析 | 6/6 |
| 时间定位 | 区间合法且不超出原片时长 | 6/6 |
| 关键帧 | 全部生成 | 18/18 |
| 可回放原片段 | 每个事件都能导出片段 | 6/6，时长误差 ≤ 0.022 s（< 1 帧） |
| 人工复核签字 | 6 条样例均需复核人确认 | **待确认 6 条**（`--require-review` 会判不通过） |

验收报告由 `python m1_work/run_m1.py` 直接输出，退出码 0 表示技术链路通过；
加 `--require-review` 则要求人工复核也已签字，这是 M1 冻结的正式口径。

## 已知限制

- **区间由 AI 提出、尚未经人签字**：`samples.csv` 里的 6 条区间是按逐帧看片给出的建议值，
  `review_status` 全部为 `pending`。必须由复核人看 `out/review/*.jpg` 后 `--confirm`，
  才能作为评测基准；未签字前 `detector=manual_annotation` 只代表「有人工来源」，不代表
  「已验证」。
- **未接入检测模型**：区间来自人工标注，`event_type` 仍来自目录标签
  （`label_source=dataset_label`）。这是 M1 的占位，D3 后替换。
- **未安装 ffprobe**：`has_audio` 由 cv2 探测，恒为 false。本数据集确认全部无音轨，
  但对新数据不可靠；装有 ffprobe 的机器会自动恢复准确判断。
- **`camera_id` / `area_id` 为 UNKNOWN**：待与数据图谱侧统一编码规则后填充。
- **末帧边界**：容器标称时长略大于可解码时长，超出范围的关键帧会用末帧代替并标记
  `clamped`，`time` 保持原片时间不变、`actual_time` 记录实际取到的时刻。
- **派生片段为 mp4v 重编码**：无 ffmpeg 时的降级路径，画面质量低于原片，仅用于回放定位。

## 不在 M1 范围

检测模型与区域越界判定、VLM 时序核验、中文语音交互、历史检索、评测指标。
这些从 D3 起逐步接入，接口字段已在上面冻结，替换实现时不需要改结构。

其中**通道区域（zone）定义按计划推迟到 D3**：M1 只负责「事件能回放」，不对
「是否越界」下结论，因此事件字段里不含任何区域判定结果，`evidence_status` 一律
`insufficient`。数据集本身也没有区域标注，zone 必须由我们按机位人工划定后单独冻结
（见 [SAMPLES.md](./SAMPLES.md)「通道区域从哪里来」）。
