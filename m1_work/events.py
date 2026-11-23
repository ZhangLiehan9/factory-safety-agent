#!/usr/bin/env python3
"""M1 候选事件生成。

M1 阶段的事件是「人工标注区间 + 数据集标签」构成的壳子，用于冻结接口契约：
区间来自 samples.csv（人工复核），事件类型来自目录标签，两者分开记录。
接入检测模型后只需替换区间来源，输出结构不变。

用法:
    python m1_work/events.py                 # 按 samples.csv 生成首批样例事件
    python m1_work/events.py --all           # 全量目录式事件（整段区间，不抽帧）
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m1_work import config  # noqa: E402
from m1_work.extract import build_evidence, load_inventory  # noqa: E402

# sample_role -> 缺证原因（M1 尚未接入检测与 VLM，证据状态一律 insufficient）
INSUFFICIENT_REASON = {
    "positive": "detector_not_connected",
    "similar_negative": "detector_not_connected",
    "insufficient": "target_not_judgeable",
    "unknown": "not_reviewed",
}

EVENT_TYPE_BY_ROLE = {
    "positive": "walkway_violation",
    "similar_negative": "walkway_normal",
    "insufficient": "walkway_violation",
}


def load_samples(path=None):
    path = path or config.SAMPLES_CSV
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("asset_id")]


def detect_events(asset, start, end, keyframe_times=None):
    """从单个视频 + 一个已确定区间产出候选事件。"""
    if not asset["decodable"]:
        return []

    evidence = build_evidence(asset, start, end, keyframe_times)
    return [{
        "event_id": "EVT-{}-001".format(asset["original_sample_id"]),
        "schema_version": config.SCHEMA_VERSION,
        "source_id": asset["source_id"],
        "asset_id": asset["asset_id"],
        "original_sample_id": asset["original_sample_id"],
        "split": asset.get("split"),
        "video_uri": evidence["video_uri"],
        "start_time": evidence["start_time"],
        "end_time": evidence["end_time"],
        "time_base": "original_video",
        "offset_from_original": evidence["offset_from_original"],
        "camera_id": "CAM-UNKNOWN",
        "area_id": "AREA-UNKNOWN",
        "event_type": asset["event_type"],
        "observations": [],
        "facts": [],
        "inferences": [],
        "evidence_status": "insufficient",
        "confidence": None,
        "keyframes": evidence["keyframes"],
        "label_source": "dataset_label",
        "is_simulated": False,
        "detector": "manual_annotation",
    }]


def event_from_sample(asset, row):
    start = float(row["start_time"])
    end = float(row["end_time"])
    role = (row.get("sample_role") or "unknown").strip()
    note = (row.get("note") or "").strip()

    duration = asset.get("duration") or 0.0
    if end <= start:
        return None, "区间非法 ({}-{})".format(start, end)
    if end > duration + config.FRAME_TOLERANCE:
        return None, "区间超出原片时长 {:.2f}s".format(duration)

    events = detect_events(asset, start, end)
    if not events:
        return None, "视频不可解码"

    ev = events[0]
    ev["event_type"] = EVENT_TYPE_BY_ROLE.get(role, asset["event_type"])
    ev["sample_role"] = role
    ev["range_source"] = "manual_review"
    ev["evidence_status"] = "insufficient"
    ev["insufficient_reason"] = INSUFFICIENT_REASON.get(role, "not_reviewed")
    ev["observations"] = [note] if note else []
    ev["annotation_review"] = {
        "status": (row.get("review_status") or "pending").strip(),
        "reviewed_by": (row.get("reviewed_by") or "").strip() or None,
        "reviewed_at": (row.get("reviewed_at") or "").strip() or None,
        "note": (row.get("review_note") or "").strip() or None,
    }
    return ev, None


def build_from_samples(inv, samples):
    events, problems = [], []
    for row in samples:
        asset_id = row["asset_id"].strip()
        asset = inv.get(asset_id)
        if asset is None:
            problems.append((asset_id, "清单中不存在"))
            continue
        ev, err = event_from_sample(asset, row)
        if ev is None:
            problems.append((asset_id, err))
        else:
            events.append(ev)
    return events, problems


def build_catalog(inv):
    """全量目录式事件：整段区间、不抽帧，只用于把资产登记进事件索引。"""
    events = []
    for asset_id in sorted(inv):
        asset = inv[asset_id]
        if not asset["decodable"] or asset["event_type"] == "unknown":
            continue
        events.append({
            "event_id": "EVT-{}-001".format(asset["original_sample_id"]),
            "schema_version": config.SCHEMA_VERSION,
            "source_id": asset["source_id"],
            "asset_id": asset["asset_id"],
            "original_sample_id": asset["original_sample_id"],
            "split": asset.get("split"),
            "video_uri": asset["video_uri"],
            "start_time": 0.0,
            "end_time": asset["duration"],
            "time_base": "original_video",
            "offset_from_original": 0.0,
            "camera_id": "CAM-UNKNOWN",
            "area_id": "AREA-UNKNOWN",
            "event_type": asset["event_type"],
            "observations": [],
            "facts": [],
            "inferences": [],
            "evidence_status": "insufficient",
            "insufficient_reason": "range_not_localized",
            "confidence": None,
            "keyframes": [],
            "label_source": "dataset_label",
            "is_simulated": False,
            "detector": "catalog",
            "sample_role": "catalog",
            "range_source": "whole_video",
        })
    return events


def write_events(events, extra=None, out_path=None):
    out_path = out_path or config.EVENTS_JSON
    payload = {
        "schema_version": config.SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "time_base": "original_video",
        "total": len(events),
        "events": events,
    }
    if extra:
        payload.update(extra)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default=config.SAMPLES_CSV)
    ap.add_argument("--all", action="store_true", help="全量目录式事件（整段区间）")
    ap.add_argument("--out", default=config.EVENTS_JSON)
    args = ap.parse_args(argv)

    if not os.path.isfile(config.INVENTORY_JSON):
        print("缺少清单，请先运行 inventory.py: {}".format(config.INVENTORY_JSON))
        return 2

    inv = load_inventory()

    if args.all:
        events = build_catalog(inv)
        write_events(events, {"mode": "catalog", "samples_source": None}, args.out)
        print("目录式事件: {} 个（整段区间，未抽帧）".format(len(events)))
        print("已写入: {}".format(args.out))
        return 0

    samples = load_samples(args.samples)
    if samples is None:
        print("缺少样例清单: {}".format(args.samples))
        print("M1 需要人工复核的正例/反例/缺证样例，请先提供该文件")
        return 2

    events, problems = build_from_samples(inv, samples)
    write_events(events, {"mode": "samples",
                          "samples_source": config.rel_to_project(args.samples)},
                 args.out)

    for e in events:
        ok = sum(1 for k in e["keyframes"] if k["status"] == "ok")
        print("{} [{}] {:.3f}-{:.3f}s  关键帧 {}/{}".format(
            e["event_id"], e["sample_role"], e["start_time"], e["end_time"],
            ok, len(e["keyframes"])))
    for asset_id, err in problems:
        print("! {} {}".format(asset_id, err))

    print("\n共 {} 个候选事件，已写入 {}".format(len(events), args.out))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
