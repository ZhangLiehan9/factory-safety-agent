import os

import pytest

from m1_work import config, decode

SAMPLE = os.path.join(config.DATASET_ROOT, "test", "0_safe_walkway_violation",
                      "0_te21.mp4")

needs_video = pytest.mark.skipif(
    not os.path.isfile(SAMPLE), reason="缺少数据集样例 0_te21.mp4")


@needs_video
def test_probe_reports_decodable_and_effective_fps():
    rec = decode.probe(SAMPLE)
    assert rec["decodable"] is True
    assert rec["width"] == 1920 and rec["height"] == 1080
    assert rec["duration"] == pytest.approx(10.45, abs=0.1)
    # 有效帧率必须与 帧数/时长 一致，不能沿用标称帧率
    assert rec["effective_fps"] == pytest.approx(
        rec["nb_frames"] / rec["duration"], abs=1e-3)


@needs_video
def test_grab_frames_hits_requested_times():
    rec = decode.probe(SAMPLE)
    times = [1.0, 5.0, 9.0]
    got = decode.grab_frames(SAMPLE, times, rec["effective_fps"])
    assert [g["status"] for g in got] == ["ok"] * 3
    for g, t in zip(got, times):
        assert abs(g["actual_time"] - t) <= 1.0 / rec["effective_fps"] + 1e-6


@needs_video
def test_grab_frames_near_end_still_returns_a_frame():
    rec = decode.probe(SAMPLE)
    got = decode.grab_frames(SAMPLE, [rec["duration"] - 0.05], rec["effective_fps"])
    assert got[0]["frame"] is not None
    assert got[0]["status"] in ("ok", "clamped")


@needs_video
def test_extract_clip_is_frame_accurate(tmp_path):
    import cv2

    rec = decode.probe(SAMPLE)
    out = tmp_path / "clip.mp4"
    start, end = 2.0, 6.0
    r = decode.extract_clip(SAMPLE, start, end, str(out), rec["effective_fps"])
    assert r["ok"] is True
    assert r["offset_from_original"] == pytest.approx(start, abs=1e-3)

    cap = cv2.VideoCapture(str(out))
    fps = cap.get(cv2.CAP_PROP_FPS)
    actual = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
    cap.release()
    assert actual == pytest.approx(end - start,
                                   abs=1.5 / rec["effective_fps"] + 0.05)
