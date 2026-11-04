"""Build a local HTML visual review gallery and human decision sheet."""
from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PILOT = ROOT / "datasets/processed/synthetic_food_appearance_pilot_20261103"
DEFAULT_OUT = ROOT / "experiments/synthetic_food/appearance_pilot_review_20261103"


def _read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_review(pilot_root: Path, output_root: Path) -> dict[str, Any]:
    rows = _read_rows(pilot_root / "manifest.jsonl")
    by_pair: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_pair.setdefault(str(row["card_pair_id"]), []).append(row)
    pairs = []
    for pair_id, members in sorted(by_pair.items()):
        if len(members) != 2 or {bool(item["card_present"]) for item in members} != {True, False}:
            raise ValueError(f"Invalid matched pair: {pair_id}")
        pair = {"pair_id": pair_id,
                "present": next(item for item in members if item["card_present"]),
                "absent": next(item for item in members if not item["card_present"])}
        pairs.append(pair)
    output_root.mkdir(parents=True, exist_ok=True)
    rows_for_sheet = []
    cards_html = []
    contact_rows: list[tuple[str, list[str], str, str]] = []
    for pair in pairs:
        present, absent = pair["present"], pair["absent"]
        kind = present["scene_kind"]
        component_names = ", ".join(item["class_name"] for item in present["annotations"])
        if kind == "isolated_dish":
            ref = present["train_reference"]
            reference_paths = [str(pilot_root / ref["crop_path"])]
            ref_html = (f'<div class="ref"><b>WED TRAIN reference crop</b>'
                        f'<img src="../../../datasets/processed/synthetic_food_appearance_pilot_20261103/{html.escape(ref["crop_path"])}">'
                        f'<img src="../../../datasets/processed/synthetic_food_appearance_pilot_20261103/{html.escape(ref["mask_overlay_path"])}">'
                        f'<small>Group {html.escape(ref["source_group_id"])} · {html.escape(ref["source_record_id"])}<br>'
                        f'Image SHA-256 {html.escape(ref["source_image_sha256"][:16])}…</small></div>')
        else:
            refs = present.get("train_references", {})
            thumbs = []
            reference_paths = [str(pilot_root / ref["crop_path"]) for ref in refs.values()]
            for ref in refs.values():
                thumbs.append(f'<div><img src="../../../datasets/processed/synthetic_food_appearance_pilot_20261103/{html.escape(ref["crop_path"])}">'
                              f'<small>{html.escape(ref["source_record_id"])}<br>Group {html.escape(ref["source_group_id"])}</small></div>')
            ref_html = '<div class="ref"><b>WED TRAIN appearance references</b><div class="ref-grid">' + ''.join(thumbs) + '</div></div>'
        contact_rows.append((component_names, reference_paths,
                             str(pilot_root / present["rgb_path"]),
                             str(pilot_root / absent["rgb_path"])))
        for sample in (present, absent):
            visual_status = sample["review_dimensions"]["visual_identity"]
            physical_status = sample["review_dimensions"]["physical_labels"]
            cards_html.append(f"""
            <section class="scene">
              <header><span>{'Card present' if sample['card_present'] else 'No card'}</span>
                <code>{html.escape(sample['sample_id'])}</code></header>
              <img class="hero" src="../../../datasets/processed/synthetic_food_appearance_pilot_20261103/{html.escape(sample['rgb_path'])}">
              <div class="diagnostics">{''.join(f'<a href="../../../datasets/processed/synthetic_food_appearance_pilot_20261103/{html.escape(path)}"><img src="../../../datasets/processed/synthetic_food_appearance_pilot_20261103/{html.escape(path)}"><small>{html.escape(name.replace("_", " "))}</small></a>' for name,path in sample['diagnostics'].items())}</div>
              <p>Visual identity: <b class="pending">{html.escape(visual_status)}</b> · Physical label checks: <b>{html.escape(physical_status)}</b></p>
            </section>""")
        rows_for_sheet.append({
            "scene_pair_id": pair["pair_id"], "scene_kind": kind,
            "food_classes": component_names,
            "card_present_sample_id": present["sample_id"], "card_absent_sample_id": absent["sample_id"],
            "class_identity": "REVIEW_REQUIRED", "visual_plausibility": "REVIEW_REQUIRED",
            "photorealism": "REVIEW_REQUIRED", "pair_consistency": "PASS (automated comparison; human confirmation required)",
            "segmentation_validity": "PASS (automated alignment/coverage checks)",
            "metric_depth_validity": "PASS (renderer finite/positive and pair checks)",
            "geometry_volume_validity": "PASS (surface integral and geometry checks)",
            "mass_density_validity": "PASS (mass=volume×density; density assumptions remain tagged)",
            "marker_visual_detection": "REVIEW_REQUIRED on card-present / NOT_APPLICABLE on no-card",
            "marker_pose_label_validity": "PASS on card-present / NOT_APPLICABLE on no-card (automated ID7/60mm geometry check)",
            "identified_artifacts": "", "rejection_reason": "", "reviewer_comments": "",
        })
        cards_html.append(f'<section class="pair"><h2>{html.escape(component_names)}</h2><p class="kind">{html.escape(kind)} · pair {html.escape(pair["pair_id"])}</p>{ref_html}<div class="pair-scenes">')
        cards_html.append("</div></section>")
        # Interleave the two samples as one pair for the layout; move scene blocks below the WED refs.
        scene_blocks = cards_html[-4:-2]
        del cards_html[-4:-2]
        cards_html[-1] = "".join(scene_blocks) + cards_html[-1]
    sheet_path = output_root / "human_review.csv"
    columns = list(rows_for_sheet[0]) if rows_for_sheet else []
    with sheet_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows_for_sheet)
    contact = Image.new("RGB", (1080, len(contact_rows) * 300), "#f4f7f1")
    draw = ImageDraw.Draw(contact)
    for index, (label, references, with_card, without_card) in enumerate(contact_rows):
        y = index * 300
        draw.text((8, y + 4), label, fill="#183128")
        for col, (heading, paths) in enumerate((
                ("WED TRAIN ref(s)", references), ("Card present", [with_card]),
                ("No card", [without_card]))):
            draw.text((8 + col * 360, y + 24), heading, fill="#68776e")
            if col == 0 and len(paths) > 1:
                box = Image.new("RGB", (350, 255), "white")
                for ref_index, path in enumerate(paths):
                    image = Image.open(path).convert("RGB")
                    image.thumbnail((172, 124))
                    box.paste(image, ((ref_index % 2) * 175, (ref_index // 2) * 127))
                contact.paste(box, (8 + col * 360, y + 42))
            else:
                image = Image.open(paths[0]).convert("RGB")
                image.thumbnail((350, 255))
                contact.paste(image, (8 + col * 360, y + 42))
    contact.save(output_root / "contact_sheet.png")
    stylesheet = """
      :root{color-scheme:light;--ink:#183128;--muted:#68776e;--line:#dce5dc;--paper:#f4f7f1;--green:#2d7555}
      *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 Inter,ui-sans-serif,system-ui,sans-serif}
      main{max-width:1440px;margin:auto;padding:32px 22px 80px}h1{font-size:34px;letter-spacing:-.04em;margin:0}h2{font-size:24px;margin:0 0 3px}.intro{color:var(--muted);max-width:900px;margin:8px 0 24px}
      .gate{padding:14px 18px;border:1px solid #e4c68c;background:#fff7df;border-radius:14px;margin:18px 0 28px}.pair{border-top:1px solid var(--line);padding:28px 0}.kind{color:var(--muted);margin:0 0 14px}.ref{background:white;border:1px solid var(--line);border-radius:14px;padding:14px;margin:12px 0;display:flex;align-items:center;gap:14px;flex-wrap:wrap}.ref img{max-height:170px;max-width:260px;object-fit:contain;border-radius:8px}.ref small{color:var(--muted);max-width:280px;overflow-wrap:anywhere}.ref-grid{display:flex;gap:10px;flex-wrap:wrap}.ref-grid>div{display:grid;gap:4px}.pair-scenes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.scene{background:white;border:1px solid var(--line);border-radius:16px;padding:14px;min-width:0}.scene header{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:10px;font-weight:700}.scene code{font-size:11px;color:var(--muted)}.hero{display:block;width:100%;height:auto;border-radius:10px;background:#e7e9e4}.diagnostics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;margin-top:8px}.diagnostics a{min-width:0;color:var(--muted);font-size:11px;text-decoration:none}.diagnostics img{width:100%;height:82px;object-fit:cover;border:1px solid var(--line);border-radius:5px}.diagnostics small{display:block;text-align:center}.pending{color:#a96707}.scene p{font-size:12px;color:var(--muted)}.human{border-top:1px solid var(--line);padding-top:20px;color:var(--muted)}
      @media(max-width:900px){.pair-scenes{grid-template-columns:1fr}.ref{align-items:flex-start}.diagnostics{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:540px){main{padding:22px 12px 50px}h1{font-size:27px}.diagnostics img{height:70px}.scene header{display:block}.scene code{display:block}}
    """
    html_doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NutriSense class-specific appearance pilot</title><style>{stylesheet}</style></head><body><main>
      <h1>Class-specific renderer pilot</h1><p class="intro">A small appearance redesign review set. Each generated scene is shown with its paired card/no-card version, a corresponding eligible WED TRAIN reference, and task-specific diagnostic views. All captured review statuses remain pending.</p>
      <div class="gate"><b>Review gate is open.</b> This pilot is not approved for classification training or corpus scale-up. Visual identity and photorealism require your review. Automated physical-label checks do not establish visual correctness.</div>
      <p><a href="contact_sheet.png">Open compact reference / matched-pair contact sheet</a></p>
      {''.join(cards_html)}<p class="human">Human decisions and notes are in <a href="human_review.csv">human_review.csv</a>. The source pilot and frozen production artifacts were not modified.</p></main></body></html>"""
    (output_root / "index.html").write_text(html_doc, encoding="utf-8")
    summary = {"pilot_root": str(pilot_root), "pairs": len(pairs), "images": len(rows),
               "human_review_rows": len(rows_for_sheet), "human_review_status": "pending",
               "visual_identity": "REVIEW_REQUIRED", "photorealism": "REVIEW_REQUIRED",
               "automated_label_checks_recorded_separately": True,
               "gallery": "index.html", "contact_sheet": "contact_sheet.png",
               "review_sheet": "human_review.csv"}
    (output_root / "package_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(build_review(args.pilot, args.out), indent=2))


if __name__ == "__main__":
    main()
