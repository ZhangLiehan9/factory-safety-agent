#!/usr/bin/env python3
"""按 event_id 回放原片证据。

这是 M1「能定位」的验收入口：给定事件 ID，输出原片路径、区间、关键帧，
并导出该区间的派生片段（保留与原片的偏移关系）。

用法:
    python m1_work/play.py --list
    python m1_work/play.py --event-id EVT-0_te21-001
    python m1_work/play.py --event-id EVT-0_te21-001 --open
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m1_work import config, decode, paths  # noqa: E402
from m1_work.extract import clip_duration, load_inventory  # noqa: E402


def load_events(path=None):
    path = path or config.EVENTS_JSON
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_event(events, event_id):
    for e in events["events"]:
        if e["event_id"] == event_id:
            return e
    return None


def export_clip(event, asset, out_path=None):
    resolved = paths.resolve_uri(event["video_uri"])
    if not resolved["ok"]:
        return {"ok": False, "error": resolved["error"], "detail": resolved["detail"]}

    out_path = out_path or os.path.join(
        config.CLIP_DIR, "{}.mp4".format(event["event_id"]))
    r = decode.extract_clip(resolved["abs_path"], event["start_time"],
                            event["end_time"], out_path,
                            (asset or {}).get("effective_fps"))
    r["clip_path"] = config.rel_to_project(out_path) if r["ok"] else None
    if r["ok"]:
        actual = clip_duration(out_path)
        expected = event["end_time"] - event["start_time"]
        r["clip_duration_actual"] = actual
        r["expected_duration"] = round(expected, 3)
        r["duration_error"] = round(abs((actual or 0) - expected), 3)
    return r


def summarize(event, asset):
    resolved = paths.resolve_uri(event["video_uri"])
    kf_ok = [k for k in event.get("keyframes", []) if k.get("status") == "ok"]
    return {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "sample_role": event.get("sample_role"),
        "evidence_status": event["evidence_status"],
        "insufficient_reason": event.get("insufficient_reason"),
        "time_base": event.get("time_base"),
        "original_video": {
            "uri": event["video_uri"],
            "resolved": resolved["ok"],
            "abs_path": resolved["abs_path"],
            "error": resolved["error"],
            "duration": (asset or {}).get("duration"),
            "splits": event.get("split"),
        },
        "replay": {
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "offset_from_original": event.get("offset_from_original", event["start_time"]),
            "clip_uri": "{}#t={:.3f},{:.3f}".format(
                event["video_uri"], event["start_time"], event["end_time"]),
        },
        "keyframes_ok": len(kf_ok),
        "keyframes_total": len(event.get("keyframes", [])),
        "keyframes": event.get("keyframes", []),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--event-id")
    ap.add_argument("--list", action="store_true", help="列出全部事件 ID")
    ap.add_argument("--open", action="store_true", help="导出片段后用系统播放器打开")
    ap.add_argument("--no-clip", action="store_true", help="只打印定位信息，不导出片段")
    args = ap.parse_args(argv)

    if not os.path.isfile(config.EVENTS_JSON):
        print("缺少事件文件，请先运行 events.py: {}".format(config.EVENTS_JSON))
        return 2
    events = load_events()

    if args.list or not args.event_id:
        for e in events["events"]:
            print("{}  [{}] {:>7.2f}-{:>7.2f}s  {}  {}".format(
                e["event_id"], e.get("sample_role", "-"), e["start_time"],
                e["end_time"], e["event_type"], e["evidence_status"]))
        if not args.event_id:
            print("\n用 --event-id 指定要回放的事件")
        return 0

    event = find_event(events, args.event_id)
    if event is None:
        print("未找到事件: {}（用 --list 查看可用 ID）".format(args.event_id))
        return 2

    inv = {}
    if os.path.isfile(config.INVENTORY_JSON):
        inv = load_inventory()
    asset = inv.get(event["asset_id"])

    out = summarize(event, asset)
    if not args.no_clip:
        out["clip"] = export_clip(event, asset)
    print(json.dumps(out, ensure_ascii=False, indent=2))

    if args.open and out.get("clip", {}).get("ok"):
        target = os.path.join(config.PROJECT_ROOT, out["clip"]["clip_path"])
        try:
            os.startfile(target)  # noqa: S606  Windows 默认播放器
        except AttributeError:
            print("当前系统不支持自动打开，请手动播放: {}".format(target))

    clip_ok = out.get("clip", {}).get("ok", True)
    return 0 if out["original_video"]["resolved"] and clip_ok else 1


if __name__ == "__main__":
    sys.exit(main())
