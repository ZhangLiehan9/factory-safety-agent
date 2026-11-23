#!/usr/bin/env python3
"""M1 抽帧与时间定位。

核心约束：所有时间戳都基于原片时间；派生片段靠 offset_from_original 反查原片。

用法:
    python m1_work/extract.py --asset-id VID-SAFE-0_te21 --start 1.0 --end 8.5
    python m1_work/extract.py --asset-id VID-SAFE-0_te21 --start 1.0 --end 8.5 --clip-out m1_work/out/clips/a.mp4
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m1_work import config, decode, paths  # noqa: E402


def load_inventory(path=None):
    path = path or config.INVENTORY_JSON
    with open(path, encoding="utf-8") as f:
        inv = json.load(f)
    return {v["asset_id"]: v for v in inv["videos"]}


def asset_video_path(asset):
    """asset 记录 -> 本机绝对路径。优先用 URI 解析，避免硬编码路径失效。"""
    uri = asset.get("video_uri")
    if uri:
        r = paths.resolve_uri(uri)
        if r["ok"]:
            return r["abs_path"]
    return asset.get("path")


def keyframe_name(t):
    return "kf_{:08.3f}.jpg".format(round(float(t), 3)).replace(".", "_", 1)


def extract_keyframes(asset, times, out_dir=None):
    """按原片时间抽关键帧，返回带原片时间与取证状态的记录。

    顺序解码一次取出全部目标帧（比逐点 seek 快一个数量级）。
    status: ok | clamped（超出可解码末尾，用末帧代替）| out_of_range | extract_failed
    """
    import cv2

    out_dir = out_dir or os.path.join(config.FRAME_DIR, asset["asset_id"])
    os.makedirs(out_dir, exist_ok=True)

    times = [round(float(t), 3) for t in times]
    duration = asset.get("duration") or 0.0
    results = []
    pending = []
    for i, t in enumerate(times):
        if duration and t > duration + config.FRAME_TOLERANCE:
            results.append({"time": t, "actual_time": None, "path": None,
                            "status": "out_of_range"})
        else:
            pending.append((t, i))

    if pending:
        grabbed = decode.grab_frames(asset_video_path(asset),
                                     [t for t, _ in pending],
                                     asset.get("effective_fps"))
        for (t, _), g in zip(pending, grabbed):
            rec = {"time": t, "actual_time": g["actual_time"], "path": None,
                   "status": g["status"]}
            if g["frame"] is None:
                rec["status"] = "extract_failed"
            else:
                out_path = os.path.join(out_dir, keyframe_name(t))
                if cv2.imwrite(out_path, g["frame"]):
                    rec["path"] = config.rel_to_project(out_path)
                else:
                    rec["status"] = "extract_failed"
            results.append(rec)

    results.sort(key=lambda r: r["time"])
    for r in results:
        if r["status"] == "ok" and not r["path"]:
            r["status"] = "extract_failed"
    return results


def build_evidence(asset, start, end, keyframe_times=None):
    """构造一条可回放的证据引用（含原片↔片段映射）。"""
    start = round(float(start), 3)
    end = round(float(end), 3)
    if keyframe_times is None:
        keyframe_times = [start, (start + end) / 2.0, end]

    video_path = asset_video_path(asset)
    return {
        "asset_id": asset["asset_id"],
        "source_id": asset["source_id"],
        "original_sample_id": asset["original_sample_id"],
        "split": asset.get("split"),
        "video_uri": asset.get("video_uri") or paths.to_uri(video_path),
        "video_path": config.rel_to_project(video_path),
        "start_time": start,
        "end_time": end,
        "duration": round(end - start, 3),
        "time_base": "original_video",
        "offset_from_original": start,
        "keyframes": extract_keyframes(asset, keyframe_times),
    }


def clip_duration(clip_path):
    """读取导出片段的实际时长，用于核对偏移是否被正确裁剪。"""
    import cv2

    cap = cv2.VideoCapture(clip_path)
    try:
        if not cap.isOpened():
            return None
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        nb = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return round(nb / fps, 3) if fps and nb else None
    finally:
        cap.release()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset-id", required=True)
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--keyframes", help="逗号分隔的原片时间，如 2.0,4.0,6.0")
    ap.add_argument("--clip-out", help="可选：导出片段路径")
    args = ap.parse_args(argv)

    inv = load_inventory()
    if args.asset_id not in inv:
        print("未知 asset_id: {}（共 {} 条）".format(args.asset_id, len(inv)))
        return 2

    asset = inv[args.asset_id]
    if not asset["decodable"]:
        print("视频不可解码: {}".format(asset_video_path(asset)))
        return 2

    start = args.start if args.start is not None else 0.0
    end = args.end if args.end is not None else asset["duration"]
    kf = [float(x) for x in args.keyframes.split(",")] if args.keyframes else None

    ev = build_evidence(asset, start, end, kf)

    if args.clip_out:
        r = decode.extract_clip(asset_video_path(asset), start, end,
                                args.clip_out, asset.get("effective_fps"))
        ev["clip_path"] = config.rel_to_project(args.clip_out) if r["ok"] else None
        ev["clip_status"] = "ok" if r["ok"] else "failed"
        ev["clip_backend"] = r["backend"]
        ev["clip_codec"] = r["codec"]
        ev["clip_error"] = r["error"]
        ev["clip_offset_from_original"] = r["offset_from_original"]
        ev["clip_duration_actual"] = clip_duration(args.clip_out) if r["ok"] else None

    print(json.dumps(ev, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
