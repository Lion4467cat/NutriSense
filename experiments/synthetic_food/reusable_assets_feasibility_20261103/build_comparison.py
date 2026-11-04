"""Build a contact sheet from TRAIN-only appearance references and both renderers."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
PILOT = ROOT / "datasets/processed/synthetic_food_appearance_pilot_20261103"
ASSET = ROOT / "datasets/processed/reusable_assets_feasibility_20261103/metafood3d"
OUT = ROOT / "datasets/processed/reusable_assets_feasibility_20261103/comparison.png"

rows = {}
for line in (PILOT / "manifest.jsonl").read_text().splitlines():
    rec = json.loads(line)
    if rec.get("scene_kind") != "isolated_dish":
        continue
    ann = rec["annotations"][0]
    name = ann["class_name"]
    if name in {"steamed-rice", "chicken-dum-biryani", "Bottle-gourd-curry", "phulka", "salad"}:
        rows[name] = rec

order = ["steamed-rice", "chicken-dum-biryani", "Bottle-gourd-curry", "phulka", "salad"]
labels = {
    "steamed-rice": ("Steamed rice", "Rice scan; exact WED variety unverified"),
    "chicken-dum-biryani": ("Chicken dum biryani", "Fried-rice scan proxy; identity mismatch"),
    "Bottle-gourd-curry": ("Bottle-gourd curry", "Beef-stew scan proxy; identity mismatch"),
    "phulka": ("Phulka", "Tortilla scan proxy; identity mismatch"),
    "salad": ("Salad", "Coleslaw scan proxy; identity mismatch"),
}
thumb_w, thumb_h = 300, 230
gap, header, label_h = 16, 40, 45
canvas = Image.new("RGB", (3 * thumb_w + 4 * gap, 5 * (thumb_h + label_h + gap) + header + gap), "#f4f1e8")
d = ImageDraw.Draw(canvas)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
except OSError:
    font = small = ImageFont.load_default()
for col, title in enumerate(["WED TRAIN reference", "Existing renderer", "MetaFood3D proxy in Blender"]):
    d.text((gap + col * (thumb_w + gap), 8), title, fill="#17251e", font=font)

for i, name in enumerate(order):
    rec = rows[name]
    sid = rec["sample_id"]
    reference = PILOT / "references" / f"class_{rec['annotations'][0]['class_id']:02d}" / "wed_train_crop.png"
    renderer = PILOT / rec["rgb_path"]
    asset = ASSET / f"{name}.png"
    images = [Image.open(p).convert("RGB") for p in (reference, renderer, asset)]
    y = header + gap + i * (thumb_h + label_h + gap)
    title, proxy = labels[name]
    d.text((gap, y), title, fill="#17251e", font=font)
    for col, im in enumerate(images):
        im.thumbnail((thumb_w, thumb_h))
        x = gap + col * (thumb_w + gap)
        tile = Image.new("RGB", (thumb_w, thumb_h), "white")
        tile.paste(im, ((thumb_w - im.width)//2, (thumb_h - im.height)//2))
        canvas.paste(tile, (x, y + 25))
        caption = ["Eligible TRAIN crop", "Procedural geometry + class surface", proxy][col]
        d.text((x, y + 25 + thumb_h + 4), caption, fill="#48584f", font=small)

OUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUT)
print(OUT)
