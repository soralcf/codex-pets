#!/usr/bin/env python3
"""Extract complete generated poses, never equal-width slots, then register rows."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def center_of_shoes(image: Image.Image) -> float:
    a = np.asarray(image)[:, :, 3]
    y, _ = np.nonzero(a > 128)
    _, x = np.nonzero(a[max(0, y.max() - 20):y.max() + 1] > 128)
    return float(x.mean())


def face_x(image: Image.Image) -> float:
    data = np.asarray(image)
    r, g, b = data[:, :, :3].astype(float).transpose(2, 0, 1)
    # Socks and navy clothing can also be greenish: restrict to the head.
    yy, _ = np.indices(r.shape)
    mask = (g > r * 1.3) & (g > b * 1.08) & (g > 90) & (data[:, :, 3] > 128) & (yy < image.height * .4)
    _, x = np.nonzero(mask)
    if len(x) < 5:
        raise ValueError("Cannot identify green-eye registration landmark")
    return float(x.mean())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--skill-dir", type=Path, required=True)
    p.add_argument("--states", default="idle,running-right,running-left,jumping,failed")
    args = p.parse_args()
    extract = load_script(args.skill_dir / "scripts/extract_strip_frames.py", "pet_extract")
    despill = load_script(args.skill_dir / "scripts/despill_chroma_edges.py", "pet_despill")
    states = args.states.split(",")
    counts = {"idle": 6, "running-right": 8, "running-left": 8, "jumping": 5, "failed": 8}
    report = {"method": "complete-pose-components/shared-row-scale", "chroma_key": "#FF00FF", "rows": {}}
    contact = Image.new("RGB", (1536, 240 * len(states)), "#20242b")
    draw = ImageDraw.Draw(contact)
    for index, state in enumerate(states):
        path = args.run_dir / "decoded" / f"{state}.png"
        source = Image.open(path).convert("RGBA")
        keyed = extract.remove_chroma_background(source, (255, 0, 255), 96)
        components = extract.connected_components(keyed)
        largest = max(c["area"] for c in components)
        main = sorted([c for c in components if c["area"] > largest * .12], key=lambda c: c["center_x"])
        if len(main) != counts[state]:
            raise ValueError(f"{state}: expected {counts[state]} whole poses, got {len(main)}; refusing slot fallback")
        groups = [[c] for c in main]
        for c in components:
            if any(c is seed for seed in main) or c["area"] < max(12, largest * .0006):
                continue
            nearest = min(range(len(main)), key=lambda i: abs(main[i]["center_x"] - c["center_x"]))
            groups[nearest].append(c)
        boxes = [extract.component_bounds(group) for group in groups]
        poses = [extract.component_group_image(keyed, group, padding=0) for group in groups]
        heights = [pose.height for pose in poses]
        # One shared scale preserves skull size and genuine crouch/knee flexion.
        scale = 194 / max(heights)
        if state.startswith("running-"):
            scale = 192 / max(heights)
        if state == "jumping":
            scale = 194 / max(heights[1], heights[3])
        anchors = [face_x(pose) if state.startswith("running-") else center_of_shoes(pose) for pose in poses]
        target_x = 126 if state == "running-right" else 66 if state == "running-left" else 98
        scale = min(scale, *(min((target_x - 6) / a, (186 - target_x) / (pose.width - a)) for pose, a in zip(poses, anchors)))
        out = args.run_dir / "frames" / state
        out.mkdir(parents=True, exist_ok=True)
        row_report = {"source": str(path), "pose_bounds": boxes, "scale": scale, "frames": []}
        draw.text((5, index * 240 + 5), state, fill="white")
        for col, (pose, anchor) in enumerate(zip(poses, anchors)):
            resized = pose.resize((round(pose.width * scale), round(pose.height * scale)), Image.Resampling.LANCZOS)
            left = round(target_x - anchor * scale)
            top = 201 - resized.height
            if state == "jumping" and col == 2:
                top = 5
            if state.startswith("running-"):
                # Register the crown; preserve the leg's airborne/contact phases.
                top = 8 + [1, 0, 1, 2, 1, 0, 1, 2][col]
            if left < 4 or top < 4 or left + resized.width > 188 or top + resized.height > 204:
                raise ValueError(f"{state}/{col}: pose would clip after registration")
            cell = Image.new("RGBA", (192, 208))
            cell.alpha_composite(resized, (left, top))
            # Resampling keyed RGB can create a few new near-key pixels. Remove
            # them before the single final edge-color extension, including
            # enclosed hair gaps which are not on the external silhouette.
            cell = extract.remove_chroma_background(cell, (255, 0, 255), 96)
            cell, color_report = despill.decontaminate_image(cell, chroma_key=(255, 0, 255))
            data = np.array(cell)
            data[data[:, :, 3] == 0, :3] = 0
            cell = Image.fromarray(data)
            cell.save(out / f"{col:02}.png")
            contact.paste(cell, (col * 192, index * 240 + 25), cell)
            row_report["frames"].append({"column": col, "left": left, "top": top,
                                          "size": resized.size, "despill": color_report})
        report["rows"][state] = row_report
    qa = args.run_dir / "qa"
    (qa / "row-registration.json").write_text(json.dumps(report, indent=2) + "\n")
    contact.save(qa / "registered-new-rows.png")
    print(json.dumps({"rows": states, "contact": str(qa / "registered-new-rows.png")}))


if __name__ == "__main__":
    main()
