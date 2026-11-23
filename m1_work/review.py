#!/usr/bin/env python3
"""人工复核工具：生成复核联系表，并把复核结论写回 samples.csv。

M1 的区间与角色是人工判断的产物，必须有人签字确认后才能冻结。
本工具只做两件事：

1. 为每条样例生成一张按区间均匀采样的联系表（jpg），供人快速看片；
2. 把「确认 / 驳回」结论写回 samples.csv，作为可追溯的复核记录。

用法:
    python m1_work/review.py                          # 生成联系表 + 打印待复核清单
    python m1_work/review.py --confirm VID-SAFE-0_te21 --by 张三
    python m1_work/review.py --reject VID-SAFE-0_te16 --by 张三 --note "区间内实际有人，需重新标"
"""
import argparse
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m1_work import config, decode  # noqa: E402
from m1_work.extract import asset_video_path, load_inventory  # noqa: E402

FIELDS = [
    "asset_id", "split", "label_dir", "sample_role", "start_time", "end_time",
    "note", "review_status", "reviewed_by", "reviewed_at", "review_note",
]
SHEET_SAMPLES = 6


def load_samples():
    with open(config.SAMPLES_CSV, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("asset_id")]
    for r in rows:
        for k in FIELDS:
            r.setdefault(k, "")
        if not r["review_status"]:
            r["review_status"] = "pending"
    return rows


def save_samples(rows):
    with open(config.SAMPLES_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def build_sheet(asset, row, out_path):
    """按区间均匀取 N 帧拼成一张联系表，每格标注原片时间。"""
    import cv2
    import numpy as np

    start = float(row["start_time"])
    end = float(row["end_time"])
    times = [round(start + (end - start) * (k + 0.5) / SHEET_SAMPLES, 3)
             for k in range(SHEET_SAMPLES)]

    grabbed = decode.grab_frames(asset_video_path(asset), times,
                                 asset.get("effective_fps"))
    tiles = []
    for g in grabbed:
        if g["frame"] is None:
            tile = np.zeros((270, 480, 3), np.uint8)
            label = "{:.2f}s 缺帧".format(g["time"])
        else:
            tile = cv2.resize(g["frame"], (480, 270))
            label = "{:.2f}s".format(g["actual_time"] if g["actual_time"] is not None
                                     else g["time"])
        overlay = tile.copy()
        cv2.rectangle(overlay, (0, 0), (480, 34), (0, 0, 0), -1)
        tile = cv2.addWeighted(overlay, 0.55, tile, 0.45, 0)
        cv2.putText(tile, "{}  {}".format(asset["original_sample_id"], label),
                    (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        tiles.append(tile)

    header = np.zeros((40, 480 * 3, 3), np.uint8)
    cv2.putText(header, "{role} | {note} | {start}-{end}s | 复核状态: {status}".format(
        role=row["sample_role"], note=row["note"],
        start=row["start_time"], end=row["end_time"], status=row["review_status"]),
        (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, np.vstack([header,
                                     np.hstack(tiles[0:3]),
                                     np.hstack(tiles[3:6])]))
    return out_path


def confirm(rows, asset_id, by, note="", status="confirmed"):
    hit = [r for r in rows if r["asset_id"] == asset_id]
    if not hit:
        print("未找到样例: {}".format(asset_id))
        return False
    row = hit[0]
    row["review_status"] = status
    row["reviewed_by"] = by
    row["reviewed_at"] = datetime.now().isoformat(timespec="seconds")
    row["review_note"] = note
    save_samples(rows)
    print("{} -> {}（复核人: {}）".format(asset_id, status, by))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset-id", help="只为指定样例生成联系表")
    ap.add_argument("--confirm", help="确认该样例")
    ap.add_argument("--reject", help="驳回该样例")
    ap.add_argument("--by", help="复核人")
    ap.add_argument("--note", default="", help="复核备注")
    args = ap.parse_args(argv)

    if not os.path.isfile(config.SAMPLES_CSV):
        print("缺少样例清单: {}".format(config.SAMPLES_CSV))
        return 2

    rows = load_samples()
    inv = load_inventory()

    if args.confirm or args.reject:
        if not args.by:
            print("必须用 --by 指定复核人（复核记录要可追溯）")
            return 2
        target = args.confirm or args.reject
        status = "confirmed" if args.confirm else "rejected"
        return 0 if confirm(rows, target, args.by, args.note, status) else 1

    print("联系表输出目录: {}".format(config.REVIEW_DIR))
    print("\n{:<20} {:<18} {:>7} {:>7}  {:<14} {:<10} {}".format(
        "asset_id", "sample_role", "start", "end", "review_status", "reviewed_by",
        "note"))
    print("-" * 110)

    pending = 0
    for row in rows:
        asset_id = row["asset_id"]
        if args.asset_id and asset_id != args.asset_id:
            continue
        asset = inv.get(asset_id)
        if asset is None:
            print("{:<20} 清单中不存在".format(asset_id))
            continue
        sheet = build_sheet(asset, row,
                            os.path.join(config.REVIEW_DIR, asset_id + ".jpg"))
        if row["review_status"] != "confirmed":
            pending += 1
        print("{:<20} {:<18} {:>7} {:>7}  {:<14} {:<10} {}".format(
            asset_id, row["sample_role"], row["start_time"], row["end_time"],
            row["review_status"], row["reviewed_by"] or "-", row["note"]))
        print("{:<20} -> {}".format("", config.rel_to_project(sheet)))

    print("\n待复核 {} / {} 条".format(pending, len(rows)))
    if pending:
        print("复核完成后执行，例如:")
        print("  python m1_work/review.py --confirm VID-SAFE-0_te21 --by <复核人>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
