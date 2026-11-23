#!/usr/bin/env python3
"""M1 一键跑通：清单 -> 候选事件 -> 回放验证 -> 验收报告。

用法:
    python m1_work/run_m1.py                 # 全量清单（test + train）
    python m1_work/run_m1.py --splits test   # 只跑评测划分
    python m1_work/run_m1.py --limit 20      # 冒烟测试
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m1_work import config, paths  # noqa: E402
import inventory  # noqa: E402
import events as events_mod  # noqa: E402
import play  # noqa: E402

CLIP_MAP_FIELDS = [
    "clip_id", "clip_path", "event_id", "asset_id", "video_uri",
    "start_time", "end_time", "offset_from_original", "duration",
    "clip_duration_actual", "duration_error", "codec", "backend", "created_at",
]


def step_inventory(root, splits, limit):
    ok, msg = paths.check_root(root)
    if not ok:
        print("错误: {}".format(msg))
        return 2
    print("\n[1/3] 视频清单")
    inv = inventory.build_inventory(root, splits, do_sha256=False, limit=limit)
    inventory.write_outputs(inv)
    print("  -> {} 个视频，可解码 {}，降级 {}".format(
        inv["total"], inv["decodable"], inv["degraded"]))
    return 0


def step_events():
    print("\n[2/3] 候选事件")
    inv = events_mod.load_inventory()
    samples = events_mod.load_samples()
    if samples is None:
        print("  错误: 缺少 {}".format(config.SAMPLES_CSV))
        return 2
    events, problems = events_mod.build_from_samples(inv, samples)
    events_mod.write_events(events, {
        "mode": "samples",
        "samples_source": config.rel_to_project(config.SAMPLES_CSV),
    })
    for asset_id, err in problems:
        print("  ! {} {}".format(asset_id, err))
    print("  -> {} 个事件".format(len(events)))
    return 0 if not problems else 1


def step_verify():
    """导出每个事件的片段并校验偏移，同时生成原片↔片段映射表。"""
    print("\n[3/3] 回放验证")
    payload = play.load_events()
    inv = play.load_inventory()
    rows, bad = [], []
    for e in payload["events"]:
        asset = inv.get(e["asset_id"])
        summary = play.summarize(e, asset)
        clip = play.export_clip(e, asset)
        summary["clip"] = clip
        if not summary["original_video"]["resolved"]:
            bad.append((e["event_id"], "原片 URI 无法解析"))
        if not clip.get("ok"):
            bad.append((e["event_id"], "片段导出失败: {}".format(clip.get("error"))))
        else:
            if clip["duration_error"] > 0.5:
                bad.append((e["event_id"], "片段时长偏差 {:.3f}s".format(clip["duration_error"])))
            rows.append({
                "clip_id": "CLIP-{}-001".format(e["original_sample_id"]),
                "clip_path": clip["clip_path"],
                "event_id": e["event_id"],
                "asset_id": e["asset_id"],
                "video_uri": e["video_uri"],
                "start_time": e["start_time"],
                "end_time": e["end_time"],
                "offset_from_original": e["offset_from_original"],
                "duration": round(e["end_time"] - e["start_time"], 3),
                "clip_duration_actual": clip.get("clip_duration_actual"),
                "duration_error": clip.get("duration_error"),
                "codec": clip.get("codec"),
                "backend": clip.get("backend"),
                "created_at": payload.get("generated_at"),
            })
        print("  {} 原片={} 片段={} 偏移={:.3f}s 时长误差={}s".format(
            e["event_id"], summary["original_video"]["resolved"], clip.get("ok"),
            e["offset_from_original"], clip.get("duration_error")))

    os.makedirs(config.MAPPING_DIR, exist_ok=True)
    with open(config.CLIP_MAP_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CLIP_MAP_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("  -> 映射表: {}".format(config.CLIP_MAP_CSV))
    return (0 if not bad else 1), bad


def report(require_review=False):
    with open(config.INVENTORY_JSON, encoding="utf-8") as f:
        inv = json.load(f)
    with open(config.EVENTS_JSON, encoding="utf-8") as f:
        evs = json.load(f)
    inv_by_id = {v["asset_id"]: v for v in inv["videos"]}

    checks = []

    # 0 事件存在
    checks.append(("候选事件", evs["total"] > 0,
                   "{} 个".format(evs["total"])))

    # 1 解码
    checks.append(("视频解码", inv["decodable"] == inv["total"],
                   "{}/{}".format(inv["decodable"], inv["total"])))

    # 2 URI 可解析
    bad_uri = [e["event_id"] for e in evs["events"]
               if not paths.resolve_uri(e["video_uri"])["ok"]]
    checks.append(("原片可定位", not bad_uri,
                   "全部可解析" if not bad_uri else "{} 条失败".format(len(bad_uri))))

    # 3 区间合法且非退化
    bad_range = []
    for e in evs["events"]:
        asset = inv_by_id.get(e["asset_id"], {})
        dur = asset.get("duration") or 0
        if e["end_time"] <= e["start_time"]:
            bad_range.append((e["event_id"], "区间非法"))
        elif dur and e["end_time"] > dur + config.FRAME_TOLERANCE:
            bad_range.append((e["event_id"], "超出原片时长"))
    checks.append(("时间区间合法", not bad_range,
                   "校验 {} 条".format(len(evs["events"])) if not bad_range
                   else "{} 条异常".format(len(bad_range))))

    # 4 关键帧
    kf_total = kf_ok = 0
    missing = []
    for e in evs["events"]:
        for k in e.get("keyframes", []):
            kf_total += 1
            if k.get("status") == "ok" and k.get("path") and \
                    os.path.isfile(os.path.join(config.PROJECT_ROOT, k["path"])):
                kf_ok += 1
            else:
                missing.append((e["event_id"], k.get("time"), k.get("status")))
    checks.append(("关键帧可用", not missing, "{}/{}".format(kf_ok, kf_total)))

    # 5 片段回放（映射表由 step_verify 生成）
    clips = 0
    if os.path.isfile(config.CLIP_MAP_CSV):
        with open(config.CLIP_MAP_CSV, encoding="utf-8-sig", newline="") as f:
            clips = sum(1 for _ in csv.DictReader(f))
    checks.append(("可回放原片段", clips == len(evs["events"]),
                   "{}/{}".format(clips, len(evs["events"]))))

    # 6 人工复核（M1 冻结前必须全部确认）
    pending = [e["event_id"] for e in evs["events"]
               if (e.get("annotation_review") or {}).get("status") != "confirmed"]
    checks.append(("人工复核签字", not require_review or not pending,
                   "全部已确认" if not pending
                   else "待确认 {} 条{}".format(
                       len(pending), "" if not require_review else "（--require-review）")))

    # 样例覆盖
    roles = {}
    for e in evs["events"]:
        roles[e.get("sample_role", "unknown")] = roles.get(e.get("sample_role", "unknown"), 0) + 1


    print("\n" + "=" * 64)
    print("M1 验收报告")
    print("=" * 64)
    print("数据集根目录  : {}".format(inv["root"]))
    print("划分          : {}".format(", ".join(inv["splits"])))
    print("元数据后端    : {}（降级 {} 条）".format(
        inv["videos"][0]["metadata_source"] if inv["videos"] else "-", inv["degraded"]))
    print("无音轨视频    : {}/{}".format(
        sum(1 for v in inv["videos"] if not v["has_audio"]), inv["total"]))
    print("-" * 64)
    for name, ok, detail in checks:
        print("{:<14}: {:<6} {}".format(name, "通过" if ok else "失败", detail))
    print("-" * 64)
    print("样例覆盖      : {}".format(
        ", ".join("{} {}".format(k, v) for k, v in sorted(roles.items()))))
    print("人工复核      : {}".format(
        "全部已确认" if not pending else "待确认 {} 条（见 samples.csv）".format(len(pending))))
    for e in evs["events"]:
        review = (e.get("annotation_review") or {}).get("status", "pending")
        print("  {:<20} [{}] {:>6.2f}-{:>6.2f}s  {:>10}  复核={}".format(
            e["event_id"], e.get("sample_role", "-"), e["start_time"],
            e["end_time"], e["insufficient_reason"], review))
    for item in bad_range + [("uri", x) for x in bad_uri]:
        print("  ! {}".format(item))
    for item in missing[:5]:
        print("  ! 关键帧 {} {} {}".format(*item))

    ok = all(c[1] for c in checks)
    print("\nM1 结论       : {}".format("通过" if ok else "存在待修复项"))
    print("=" * 64)
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=config.DATASET_ROOT)
    ap.add_argument("--splits", default=",".join(config.SPLITS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--require-review", action="store_true",
                    help="要求全部样例已人工复核签字，否则视为不通过")
    args = ap.parse_args(argv)

    config.ensure_dirs()
    splits = [s.strip() for s in args.splits.split(",") if s.strip()]

    rc = step_inventory(args.root, splits, args.limit)
    if rc != 0:
        return rc
    rc |= step_events()
    verify_rc, bad = step_verify()
    rc |= verify_rc
    rc |= report(require_review=args.require_review)
    return rc


if __name__ == "__main__":
    sys.exit(main())
