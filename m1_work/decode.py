#!/usr/bin/env python3
"""解码后端。

- 帧与元数据：统一走 OpenCV。实测 1080p 顺序解码约 250 fps，
  而逐点 seek 单帧约 43 ms（慢 10 倍），因此抽帧一律「顺序解码一次 + 按帧号截取」。
- 片段导出：优先 ffmpeg 流拷贝（不重编码）；无 ffmpeg 时降级 OpenCV 重编码，
  并在返回值里标明 backend / codec，避免「看起来一样其实重编码过」。
"""
import json
import os
import shutil
import subprocess

VIDEO_EXTS = (".mp4", ".avi", ".mkv", ".mov")


def have_ffmpeg():
    return shutil.which("ffmpeg") is not None


def have_ffprobe():
    return shutil.which("ffprobe") is not None


def _parse_fraction(s):
    """'25/1' -> 25.0"""
    try:
        if "/" in str(s):
            a, b = str(s).split("/")[:2]
            return float(a) / float(b) if float(b) else 0.0
        return float(s)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0.0


def _empty_record(error):
    return {
        "decodable": False,
        "width": None, "height": None, "fps": None, "effective_fps": None,
        "duration": None, "nb_frames": None, "has_audio": False, "codec": None,
        "metadata_source": None, "degraded": False, "error": error,
    }


def _probe_ffprobe(path):
    cmd = ["ffprobe", "-v", "error", "-print_format", "json",
           "-show_streams", "-show_format", path]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    try:
        info = json.loads(r.stdout.decode("utf-8", "replace"))
    except ValueError:
        return None

    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    if v is None:
        return _empty_record("no video stream")

    # avg_frame_rate 才是有效帧率；r_frame_rate 常是标称值（如 25，实际 24.11）
    fps = _parse_fraction(v.get("avg_frame_rate")) or _parse_fraction(v.get("r_frame_rate"))
    dur = v.get("duration") or info.get("format", {}).get("duration")
    dur = float(dur) if dur else None
    nb = v.get("nb_frames")
    nb = int(nb) if str(nb).isdigit() else None
    if nb is None and fps and dur:
        nb = int(round(dur * fps))

    rec = _empty_record(None)
    rec.update({
        "decodable": bool(dur),
        "width": v.get("width"),
        "height": v.get("height"),
        "fps": round(fps, 3) if fps else None,
        "duration": round(dur, 4) if dur else None,
        "nb_frames": nb,
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        "codec": v.get("codec_name"),
        "metadata_source": "ffprobe",
        "degraded": False,
    })
    rec["effective_fps"] = _effective_fps(rec)
    return rec


def _probe_cv2(path):
    try:
        import cv2
    except ImportError:
        return _empty_record("cv2 not installed")

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        cap.release()
        return _empty_record("cannot open video")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        nb = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        rec = _empty_record(None)
        rec.update({
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or None,
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None,
            "fps": round(fps, 3) if fps else None,
            "nb_frames": nb or None,
            "duration": round(nb / fps, 4) if fps and nb else None,
            "metadata_source": "cv2",
            "degraded": True,
        })
        ok, _ = cap.read()
        rec["decodable"] = bool(ok) and rec["duration"] is not None
        if not ok:
            rec["error"] = "first frame read failed"
    finally:
        cap.release()
    rec["effective_fps"] = _effective_fps(rec)
    return rec


def _effective_fps(rec):
    """时间换算用的帧率：优先 nb_frames / duration，避免标称帧率误差。"""
    if rec.get("nb_frames") and rec.get("duration"):
        return round(rec["nb_frames"] / rec["duration"], 4)
    return rec.get("fps")


def probe(path):
    """提取视频元数据。ffprobe 可用则优先，失败自动降级 cv2。"""
    if have_ffprobe():
        rec = _probe_ffprobe(path)
        if rec and rec["decodable"]:
            return rec
    return _probe_cv2(path)


def grab_frames(path, times, effective_fps=None, tolerance=None):
    """顺序解码一次，取出各目标时间最接近的帧。

    返回与 times 等长的列表，元素为
    {time, actual_time, frame, status}，status ∈ {ok, clamped, extract_failed}。
    """
    import cv2

    try:
        from . import config
    except ImportError:  # 以脚本方式直接运行时
        import config

    tolerance = config.FRAME_TOLERANCE if tolerance is None else tolerance
    times = [float(t) for t in times]
    results = [None] * len(times)
    if not times:
        return results

    order = sorted(range(len(times)), key=lambda i: times[i])
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        cap.release()
        return [{"time": t, "actual_time": None, "frame": None,
                 "status": "extract_failed"} for t in times]

    fps = effective_fps or cap.get(cv2.CAP_PROP_FPS) or 25.0
    idx = 0
    last_frame = None
    last_actual = None
    next_k = 0
    try:
        while next_k < len(order):
            ok, frame = cap.read()
            if not ok:
                break
            last_frame, last_actual = frame, idx / fps
            while next_k < len(order) and idx >= round(times[order[next_k]] * fps):
                i = order[next_k]
                results[i] = {"time": times[i], "actual_time": round(last_actual, 4),
                              "frame": frame, "status": "ok"}
                next_k += 1
            idx += 1
    finally:
        cap.release()

    # 目标时间超出可解码范围：用最后可用帧兜底，并如实标记 actual_time
    for i in range(len(times)):
        if results[i] is None:
            if last_frame is None:
                results[i] = {"time": times[i], "actual_time": None,
                              "frame": None, "status": "extract_failed"}
            else:
                results[i] = {"time": times[i], "actual_time": round(last_actual, 4),
                              "frame": last_frame, "status": "clamped"}
        else:
            actual = results[i]["actual_time"]
            if abs(actual - times[i]) > tolerance + 1.0 / fps:
                results[i]["status"] = "clamped"
    return results


def extract_clip(path, start, end, out_path, effective_fps=None):
    """导出原片 [start, end] 片段。

    返回 {ok, backend, codec, offset_from_original, duration, error}。
    offset_from_original 恒等于 start：片段第 0 秒对应原片第 start 秒。
    """
    start = float(start)
    end = float(end)
    dur = max(0.0, end - start)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    if have_ffmpeg():
        # 重编码而非流拷贝：-c copy 只能从关键帧起切，短片段会偏移近 1 秒。
        cmd = ["ffmpeg", "-nostdin", "-v", "error",
               "-ss", "{:.3f}".format(start), "-i", path,
               "-t", "{:.3f}".format(dur),
               "-map", "0:v:0", "-map", "0:a?",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
               "-c:a", "copy",
               "-avoid_negative_ts", "make_zero", out_path, "-y"]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=300)
            if r.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return {"ok": True, "backend": "ffmpeg", "codec": "h264",
                        "offset_from_original": round(start, 3),
                        "duration": round(dur, 3), "error": None}
            err = r.stderr.decode("utf-8", "replace")[-300:]
        except (OSError, subprocess.TimeoutExpired) as e:
            err = str(e)
    else:
        err = "ffmpeg not available"

    ok, detail = _clip_cv2(path, start, end, out_path, effective_fps)
    return {"ok": ok, "backend": "cv2", "codec": "mp4v",
            "offset_from_original": round(start, 3), "duration": round(dur, 3),
            "error": None if ok else "{}; ffmpeg: {}".format(detail, err)}


def _clip_cv2(path, start, end, out_path, effective_fps):
    """OpenCV 逐帧重编码导出片段，按帧号精确裁剪。

    ffmpeg 的 -c copy 只能从关键帧起切，短片段会偏移近 1 秒；这里按帧号
    写入 [start_frame, end_frame)，保证片段时长 = 区间时长（±1 帧）。
    """
    import cv2

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        cap.release()
        return False, "cannot open video"
    try:
        fps = effective_fps or cap.get(cv2.CAP_PROP_FPS) or 25.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not w or not h:
            return False, "invalid frame size"

        start_f = int(round(start * fps))
        end_f = int(round(end * fps))
        if end_f <= start_f:
            return False, "empty frame range"

        # 提前 1 秒定位，再用帧号精确筛选（POS_MSEC 定位本身不精确）
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, start - 1.0) * 1000.0)
        writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"),
                                 fps, (w, h))
        if not writer.isOpened():
            writer.release()
            return False, "VideoWriter open failed"
        written = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                if idx < start_f:
                    continue
                if idx >= end_f:
                    break
                writer.write(frame)
                written += 1
        finally:
            writer.release()
        if written == 0:
            return False, "no frame written"
        return True, "{} frames".format(written)
    finally:
        cap.release()
