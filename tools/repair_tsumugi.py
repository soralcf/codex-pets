#!/usr/bin/env python3
"""Deterministic registration and edge cleanup for the Tsumugi repair.

Requires Pillow and numpy. This processes existing/generated artwork; it does
not draw poses. The original atlas must be supplied explicitly and is never
overwritten. See the character README for source provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WIDTH, HEIGHT = 192, 208
STATES = ["idle", "running-right", "running-left", "waving", "jumping",
          "failed", "waiting", "running", "review", "look-a", "look-b"]
COUNTS = [7, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8]


def crop_cell(atlas: Image.Image, row: int, col: int) -> Image.Image:
    return atlas.crop((col * WIDTH, row * HEIGHT, (col + 1) * WIDTH, (row + 1) * HEIGHT))


def shoe_center(cell: Image.Image) -> float:
    alpha = np.asarray(cell)[:, :, 3]
    ys, _ = np.nonzero(alpha > 128)
    bottom = int(ys.max())
    _, xs = np.nonzero(alpha[max(0, bottom - 9):bottom + 1] > 128)
    return float(xs.mean())


def clean_white_hair_edge(cell: Image.Image) -> tuple[Image.Image, int]:
    """Replace white matte RGB only at a thin, conservatively masked hair edge.

    Alpha, interior highlights, face and central uniform pixels are untouched.
    Unlike a second chroma-despill pass, this targets low-saturation pale matte
    adjacent to warm hair and never selects saturated pink clip/hair details.
    """
    data = np.array(cell)
    rgb = data[:, :, :3].astype(float)
    alpha = data[:, :, 3]
    visible = Image.fromarray(np.uint8(alpha > 16) * 255)
    boundary = (alpha > 0) & (np.asarray(visible.filter(ImageFilter.MinFilter(3))) == 0)
    yy, xx = np.indices(alpha.shape)
    hair_zone = (yy < 156) & ((yy < 38) | (xx < 62) | (xx > 133))
    red, green, blue = rgb.transpose(2, 0, 1)
    pale = (red > 210) & (green > 205) & (blue > 185) & (red - blue < 55) & (green - blue < 45)
    warm = (alpha > 240) & (red > green + 4) & (green > blue + 12) & (red - blue > 30)
    changed = 0
    for y, x in zip(*np.nonzero(boundary & hair_zone & pale)):
        y0, y1 = max(0, y - 3), min(HEIGHT, y + 4)
        x0, x1 = max(0, x - 3), min(WIDTH, x + 4)
        wy, wx = np.nonzero(warm[y0:y1, x0:x1])
        if not len(wx):
            continue
        wy, wx = wy + y0, wx + x0
        dist = (wy - y) ** 2 + (wx - x) ** 2
        if dist.min() > 10:
            continue
        near = dist <= min(dist.min() + 2, 10)
        reference = np.median(rgb[wy[near], wx[near]], axis=0)
        data[y, x, :3] = np.rint(reference * .85 + rgb[y, x] * .15).astype(np.uint8)
        changed += 1
    data[alpha == 0, :3] = 0
    assert np.array_equal(data[:, :, 3], alpha)
    return Image.fromarray(data), changed


def retain_and_register(source: Image.Image, replaced_rows: tuple = ()) -> tuple[Image.Image, dict]:
    result = source.copy()
    target = shoe_center(crop_cell(source, 0, 6))
    report = {"foot_anchor_x": target, "registration": [], "white_matte": {}}
    for row, count in enumerate(COUNTS):
        if row in (1, 2, 4) or row in replaced_rows:
            continue
        for col in range(count):
            original = crop_cell(source, row, col)
            cell, changed = clean_white_hair_edge(original)
            report["white_matte"][f"r{row}c{col}"] = changed
            if row in (0, 5, 8) and not (row == 0 and col == 6):
                before = shoe_center(cell)
                dx = round(target - before)
                moved = Image.new("RGBA", cell.size)
                moved.alpha_composite(cell, (dx, 0))
                if np.asarray(moved)[:, :, 3].sum() != np.asarray(cell)[:, :, 3].sum():
                    raise ValueError(f"Translation clipped r{row}c{col}")
                cell = moved
                report["registration"].append({"row": row, "frame": col, "dx": dx,
                                                "before_x": before, "after_x": shoe_center(cell)})
            result.paste(cell, (col * WIDTH, row * HEIGHT))
    return result, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--replacement-frames", type=Path)
    args = parser.parse_args()
    original = Image.open(args.source).convert("RGBA")
    if original.size != (1536, 2288):
        raise ValueError("Expected a 1536×2288 v2 atlas")
    replaced_rows = (0, 1, 2, 4, 5) if args.replacement_frames else ()
    atlas, report = retain_and_register(original, replaced_rows)
    report["source_sha256"] = hashlib.sha256(args.source.read_bytes()).hexdigest()
    report["replaced_rows"] = []
    if args.replacement_frames:
        for row in replaced_rows:
            state = STATES[row]
            for col in range(6 if row == 0 else COUNTS[row]):
                path = args.replacement_frames / state / f"{col:02}.png"
                cell = Image.open(path).convert("RGBA")
                if cell.size != (WIDTH, HEIGHT):
                    raise ValueError(f"Invalid final frame size: {path}")
                atlas.paste(cell, (col * WIDTH, row * HEIGHT))
            report["replaced_rows"].append(state)
        # The neutral look pose remains the existing approved image, with the
        # same RGB-only white-edge repair applied to the retained direction set.
        neutral, changed = clean_white_hair_edge(crop_cell(original, 0, 6))
        atlas.paste(neutral, (6 * WIDTH, 0))
        report["white_matte"]["r0c6"] = changed
    data = np.array(atlas)
    data[data[:, :, 3] == 0, :3] = 0
    atlas = Image.fromarray(data)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atlas.save(args.output_dir / "spritesheet.png")
    atlas.save(args.output_dir / "spritesheet.webp", lossless=True, exact=True)
    report["output_sha256"] = hashlib.sha256((args.output_dir / "spritesheet.webp").read_bytes()).hexdigest()
    (args.output_dir / "repair-report.json").write_text(json.dumps(report, indent=2) + "\n")
    # Full-size dark-background comparison of retained rows, with identical crops.
    comparison = Image.new("RGB", (WIDTH * 8, 240 * 6), "#20242b")
    draw = ImageDraw.Draw(comparison)
    for pair, row in enumerate((0, 5, 8)):
        for variant, image in enumerate((original, atlas)):
            y = (pair * 2 + variant) * 240
            draw.text((8, y + 5), f"{STATES[row]} / {'after' if variant else 'before'}", fill="white")
            for col in range(COUNTS[row]):
                cell = crop_cell(image, row, col)
                comparison.paste(cell, (col * WIDTH, y + 25), cell)
    comparison.save(args.output_dir / "registration-comparison.png")
    print(json.dumps({"output": str(args.output_dir), "white_edge_pixels": sum(report["white_matte"].values()),
                      "registered_frames": len(report["registration"])}))


if __name__ == "__main__":
    main()
