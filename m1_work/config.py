#!/usr/bin/env python3
"""M1 统一配置。

所有路径都由本文件位置推导，因此在任意工作目录下运行结果一致。
数据集根目录可用环境变量 DATASET_ROOT 覆盖（换机器、换挂载点时无需改代码）。
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)

DEFAULT_DATASET_ROOT = os.path.join(
    PROJECT_ROOT,
    "datasets",
    "Video Dataset for Safe and Unsafe Behaviours",
    "Safe and Unsafe Behaviours Dataset",
)
DATASET_ROOT = os.path.abspath(os.environ.get("DATASET_ROOT") or DEFAULT_DATASET_ROOT)

OUT_DIR = os.path.join(HERE, "out")
FRAME_DIR = os.path.join(OUT_DIR, "frames")
CLIP_DIR = os.path.join(OUT_DIR, "clips")
MAPPING_DIR = os.path.join(OUT_DIR, "mappings")
REVIEW_DIR = os.path.join(OUT_DIR, "review")

INVENTORY_JSON = os.path.join(OUT_DIR, "video_inventory.json")
INVENTORY_CSV = os.path.join(OUT_DIR, "video_inventory.csv")
EVENTS_JSON = os.path.join(OUT_DIR, "events.json")
CLIP_MAP_CSV = os.path.join(MAPPING_DIR, "clip_map.csv")
SAMPLES_CSV = os.path.join(HERE, "samples.csv")

SPLITS = ("test", "train")
URI_SCHEME = "saferaw"
SCHEMA_VERSION = "1.1"

# 单帧抽取允许的最大偏差（秒）。超过则标记为 clamped。
FRAME_TOLERANCE = 0.1


def ensure_dirs():
    for d in (OUT_DIR, FRAME_DIR, CLIP_DIR, MAPPING_DIR, REVIEW_DIR):
        os.makedirs(d, exist_ok=True)


def rel_to_project(abs_path):
    """绝对路径 -> 相对项目根的正斜杠路径，便于跨机器复跑。"""
    rel = os.path.relpath(os.path.abspath(abs_path), PROJECT_ROOT)
    return rel.replace(os.sep, "/")
