#!/usr/bin/env python3
"""Render matched before/after previews at the desktop player's actual timing."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

STATES = ["idle", "running-right", "running-left", "waving", "jumping", "failed", "waiting", "running", "review"]
DURATIONS = [[280, 110, 110, 140, 140, 320], [120] * 7 + [220], [120] * 7 + [220],
             [140] * 3 + [280], [140] * 4 + [280], [140] * 7 + [240],
             [150] * 5 + [260], [120] * 5 + [220], [150] * 5 + [280]]


def cell(image, row, col):
    return image.crop((col * 192, row * 208, (col + 1) * 192, (row + 1) * 208))


def frame(old, new, row, col):
    result = Image.new("RGB", (408, 252), "#252a33")
    draw = ImageDraw.Draw(result)
    draw.text((6, 7), f"BEFORE / {STATES[row]} / {col + 1}", fill="white")
    draw.text((216, 7), f"AFTER / {STATES[row]} / {col + 1}", fill="white")
    for image, x in ((old, 6), (new, 210)):
        sprite = cell(image, row, col)
        result.paste(sprite, (x, 30), sprite)
        draw.line((x, 233, x + 192, 233), fill="#555a65")
    return result


def foot_x(sprite):
    a = np.asarray(sprite)[:, :, 3]
    y, _ = np.nonzero(a > 128)
    _, x = np.nonzero(a[max(0, y.max() - 9):y.max() + 1] > 128)
    return float(x.mean())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--before", type=Path, required=True)
    p.add_argument("--after", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--require-run-symmetry", action="store_true")
    args = p.parse_args()
    old = Image.open(args.before).convert("RGBA")
    new = Image.open(args.after).convert("RGBA")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"playback": "non-idle rows repeat three times, then idle at 6x frame durations", "rows": {}}
    for row, state in enumerate(STATES):
        count = len(DURATIONS[row])
        frames = [frame(old, new, row, col) for col in range(count)]
        durations = [d * 6 for d in DURATIONS[row]] if row == 0 else DURATIONS[row]
        frames[0].save(args.output_dir / f"{state}-comparison.webp", save_all=True,
                       append_images=frames[1:], duration=durations, loop=0, lossless=True)
        # Explicitly exercise both loop closure and transition back to idle.
        if row in (1, 2, 4, 5):
            sequence = frames * 3 + [frame(old, new, 0, col) for col in range(6)]
            timing = DURATIONS[row] * 3 + [d * 6 for d in DURATIONS[0]]
            sequence[0].save(args.output_dir / f"{state}-app-playback.webp", save_all=True,
                             append_images=sequence[1:], duration=timing, loop=0, lossless=True)
        if row in (0, 5, 8):
            bx = [foot_x(cell(old, row, col)) for col in range(count)]
            ax = [foot_x(cell(new, row, col)) for col in range(count)]
            report["rows"][state] = {"before_foot_x": bx, "after_foot_x": ax,
                                      "before_range_px": max(bx) - min(bx), "after_range_px": max(ax) - min(ax),
                                      "before_loop_snap_px": abs(bx[-1] - bx[0]), "after_loop_snap_px": abs(ax[-1] - ax[0])}
    for row in (9, 10):
        a = np.asarray(old)[row * 208:(row + 1) * 208]
        b = np.asarray(new)[row * 208:(row + 1) * 208]
        same_alpha = bool(np.array_equal(a[:, :, 3], b[:, :, 3]))
        if not same_alpha:
            raise ValueError(f"Preserved look row {row} changed shape/registration")
    report["look_geometry_and_alpha_unchanged"] = True
    symmetry = []
    paired_frames = []
    contact = Image.new("RGB", (8 * 192, 2 * 240), "#252a33")
    draw = ImageDraw.Draw(contact)
    for col in range(8):
        left = cell(new, 2, col)
        right = cell(new, 1, col)
        expected = left.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        different = int(np.any(np.asarray(right) != np.asarray(expected), axis=2).sum())
        lb, rb = left.getbbox(), right.getbbox()
        symmetry.append({"frame": col, "different_rgba_pixels": different,
                         "left_bounds": lb, "right_bounds": rb,
                         "height_difference_px": (rb[3] - rb[1]) - (lb[3] - lb[1])})
        pair = Image.new("RGB", (408, 252), "#252a33")
        pd = ImageDraw.Draw(pair)
        for row, (sprite, label, x) in enumerate(((left, "LEFT", 6), (right, "RIGHT", 210))):
            pd.text((x, 7), f"{label} / {col + 1}", fill="white")
            pair.paste(sprite, (x, 30), sprite)
            draw.text((col * 192 + 5, row * 240 + 5), f"{label} / {col + 1}", fill="white")
            contact.paste(sprite, (col * 192, row * 240 + 25), sprite)
        paired_frames.append(pair)
    symmetric = all(f["different_rgba_pixels"] == 0 for f in symmetry)
    report["directional_symmetry"] = {"ok": symmetric, "canonical_state": "running-left",
                                       "frame_order_preserved": True, "frames": symmetry}
    if args.require_run_symmetry and not symmetric:
        raise ValueError("Directional running rows are not exact per-frame mirrors")
    contact.save(args.output_dir / "running-symmetry.png")
    paired_frames[0].save(args.output_dir / "running-symmetry.webp", save_all=True,
                          append_images=paired_frames[1:], duration=DURATIONS[1], loop=0, lossless=True)
    (args.output_dir / "motion-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: {s: round(v, 2) for s, v in data.items() if s.endswith("_px")} for k, data in report["rows"].items()}))


if __name__ == "__main__":
    main()
