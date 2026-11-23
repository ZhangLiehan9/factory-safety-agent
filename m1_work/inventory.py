#!/usr/bin/env python3
"""M1 视频清单：解码检查 + 元数据提取。

用法:
    python m1_work/inventory.py                     # 全量（test + train）
    python m1_work/inventory.py --splits test       # 仅评测划分
    python m1_work/inventory.py --limit 20          # 冒烟测试
    python m1_work/inventory.py --sha256            # 附带 SHA-256（慢）
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m1_work import config, decode, paths  # noqa: E402

# 目录名 -> (原始标签, 统一事件类型)
LABEL_MAP = {
    "0_safe_walkway_violation": ("unsafe", "walkway_violation"),
    "4_safe_walkway": ("safe", "walkway_normal"),
    "2_opened_panel cover": ("unsafe", "panel_opened"),
    "6_closed_panel_cover": ("safe", "panel_closed"),
    "1_unauthorized_intervention": ("unsafe", "unauthorized_intervention"),
    "5_authorized_intervention": ("safe", "authorized_intervention"),
    "3_carrying_overload_with_forklift": ("unsafe", "carrying_overload"),
    "7_safe_carrying": ("safe", "safe_carrying"),
}

CSV_FIELDS = [
    "asset_id", "source_id", "original_sample_id", "split", "label_dir",
    "label", "event_type", "video_uri", "width", "height", "fps",
    "effective_fps", "duration", "nb_frames", "has_audio", "size_bytes",
    "decodable", "metadata_source", "degraded", "error",
]


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def iter_videos(root, splits):
    """按 <root>/<split>/<label_dir>/*.mp4 遍历，顺序稳定。"""
    for split in splits:
        split_dir = os.path.join(root, split)
        if not os.path.isdir(split_dir):
            continue
        for label_dir in sorted(os.listdir(split_dir)):
            d = os.path.join(split_dir, label_dir)
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if os.path.splitext(fn)[1].lower() in decode.VIDEO_EXTS:
                    yield split, label_dir, os.path.join(d, fn)


def build_inventory(root, splits, do_sha256=False, limit=None):
    videos = []
    for split, label_dir, path in iter_videos(root, splits):
        if limit and len(videos) >= limit:
            break

        sample_id = os.path.splitext(os.path.basename(path))[0]
        label, event_type = LABEL_MAP.get(label_dir, ("unknown", "unknown"))

        rec = {
            "asset_id": "VID-SAFE-{}".format(sample_id),
            "source_id": "SAFE",
            "original_sample_id": sample_id,
            "split": split,
            "path": path,
            "label_dir": label_dir,
            "label": label,
            "event_type": event_type,
            "video_uri": paths.to_uri(path, root),
            "size_bytes": os.path.getsize(path),
        }
        rec.update(decode.probe(path))
        if do_sha256:
            rec["sha256"] = sha256_file(path)
        videos.append(rec)

        print("[{}][{}] {} ({}x{} @{:.2f}fps, {}s, audio={}, {})".format(
            "OK" if rec["decodable"] else "FAIL",
            split, os.path.basename(path), rec["width"], rec["height"],
            rec["effective_fps"] or 0.0, rec["duration"],
            rec["has_audio"], rec["metadata_source"]))

    return {
        "schema_version": config.SCHEMA_VERSION,
        "source_id": "SAFE",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": root,
        "splits": list(splits),
        "total": len(videos),
        "decodable": sum(1 for v in videos if v["decodable"]),
        "degraded": sum(1 for v in videos if v["degraded"]),
        "videos": videos,
    }


def write_outputs(inv):
    os.makedirs(os.path.dirname(config.INVENTORY_JSON), exist_ok=True)
    with open(config.INVENTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, indent=2)
    with open(config.INVENTORY_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for v in inv["videos"]:
            w.writerow(v)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=config.DATASET_ROOT)
    ap.add_argument("--splits", default=",".join(config.SPLITS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sha256", action="store_true", help="同时计算 SHA-256（较慢）")
    args = ap.parse_args(argv)

    ok, msg = paths.check_root(args.root)
    if not ok:
        print("错误: {}".format(msg))
        return 2

    splits = [s.strip() for s in args.splits.split(",") if s.strip()]
    print("数据集根目录: {}".format(args.root))
    print("划分: {}  元数据后端: {}".format(
        ", ".join(splits), "ffprobe" if decode.have_ffprobe() else "cv2（降级）"))

    inv = build_inventory(args.root, splits, args.sha256, args.limit)
    write_outputs(inv)

    print("\n共 {} 个视频，可解码 {} 个，降级 {} 个".format(
        inv["total"], inv["decodable"], inv["degraded"]))
    print("清单已写入: {} / {}".format(config.INVENTORY_JSON, config.INVENTORY_CSV))
    return 0 if inv["decodable"] == inv["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
