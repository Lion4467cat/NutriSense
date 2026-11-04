"""Validate paired Blender renders and build a human-review gallery/sheet.

Uses only outputs, the already-saved eligible TRAIN reference crops, and local
renderer/MetaFood3D pilot previews. It never opens source WED images.
"""
from __future__ import annotations

import csv
import json
import itertools
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"datasets/processed/synthetic_food_ingredient_blender_pilot_20261104"
OLD=ROOT/"datasets/processed/synthetic_food_appearance_pilot_20261103"
MESH=ROOT/"datasets/processed/reusable_assets_feasibility_20261103/metafood3d"
CLASSES=[("chicken-dum-biryani",12),("Bottle-gourd-curry",1),("salad",32)]


def load_font(size):
    try:return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",size)
    except OSError:return ImageFont.load_default()


def row_pairs(rows):
    pairs={}
    for r in rows:pairs.setdefault(r["pair_id"],[]).append(r)
    return pairs


def verify_pair(pair_id,members):
    out={"pair_id":pair_id,"check_status":{},"errors":[]}
    if len(members)!=2 or {bool(x["card_present"]) for x in members}!={True,False}:
        return {**out,"errors":["expected one card-present and one no-card frame"]}
    present=next(r for r in members if r["card_present"])
    absent=next(r for r in members if not r["card_present"])
    pp=OUT/present["metadata"];ap=OUT/absent["metadata"]
    pm=json.loads(pp.read_text());am=json.loads(ap.read_text())
    pc=cv2.imread(str(OUT/present["rgb"]),cv2.IMREAD_COLOR)
    ac=cv2.imread(str(OUT/absent["rgb"]),cv2.IMREAD_COLOR)
    pmask=cv2.imread(str(OUT/present["mask"]),cv2.IMREAD_UNCHANGED)
    amask=cv2.imread(str(OUT/absent["mask"]),cv2.IMREAD_UNCHANGED)
    pd=np.load(OUT/present["metric_depth"]);ad=np.load(OUT/absent["metric_depth"])
    out["check_status"]["rgb_pair_dimensions"]="PASS" if pc.shape==ac.shape else "FAIL"
    if pc.shape!=ac.shape:out["errors"].append("RGB dimensions differ")
    mask_equal=bool(np.array_equal(pmask,amask))
    out["check_status"]["food_mask_identical"]="PASS" if mask_equal else "FAIL"
    if not mask_equal:out["errors"].append("class masks differ between card pair")
    food=pmask>0
    depth_equal=bool(np.allclose(pd[food],ad[food],rtol=0,atol=1e-7) and np.array_equal(food,amask>0))
    out["check_status"]["food_metric_depth_identical"]="PASS" if depth_equal else "FAIL"
    if not depth_equal:out["errors"].append("food camera-Z depth differs between card pair")
    config_equal=(pm["seed"]==am["seed"] and pm["camera"]==am["camera"]
                  and pm["components"]==am["components"]
                  and pm["total_food_mass_estimate_g"]==am["total_food_mass_estimate_g"])
    out["check_status"]["camera_geometry_seed_identical"]="PASS" if config_equal else "FAIL"
    if not config_equal:out["errors"].append("camera, geometry, mass or seed metadata differ")
    card_pixels=cv2.imread(str(OUT/present["card_mask"]),cv2.IMREAD_UNCHANGED)>0
    polygon=cv2.dilate(card_pixels.astype(np.uint8),np.ones((5,5),np.uint8))>0
    diff=np.max(np.abs(pc.astype(np.int16)-ac.astype(np.int16)),axis=2)>3
    outside=int(np.count_nonzero(diff&~polygon))
    outside_delta=np.max(np.abs(pc.astype(np.int16)-ac.astype(np.int16)),axis=2)[diff&~polygon]
    max_outside=int(outside_delta.max()) if outside_delta.size else 0
    out["rgb_changed_pixels_outside_card_plus_2px"] = outside
    out["max_rgb_delta_outside_card_plus_2px"] = max_outside
    # At 12 Cycles samples, card visibility can shift a few low-level AA/path
    # samples outside the ray-cast footprint. Record them and fail larger ones.
    rgb_pair_ok=outside<=12 and max_outside<=12
    out["check_status"]["rgb_changes_confined_to_card"]=(
        "PASS_WITH_LOW_LEVEL_RENDER_TOLERANCE" if rgb_pair_ok and outside else
        "PASS" if rgb_pair_ok else "FAIL")
    if not rgb_pair_ok:
        out["errors"].append(f"{outside} pixels (max RGB delta {max_outside}) changed outside card + 2px")
    elif outside:
        out.setdefault("warnings",[]).append(
            f"{outside} low-level path-trace pixels (max RGB delta {max_outside}/255) changed outside card + 2px")
    gray=cv2.cvtColor(pc,cv2.COLOR_BGR2GRAY)
    dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector=cv2.aruco.ArucoDetector(dictionary)
    marker_corners,ids,_=detector.detectMarkers(gray)
    ids=[] if ids is None else [int(v) for v in ids.reshape(-1)]
    out["detected_marker_ids"]=ids
    marker_ok=7 in ids and pm["marker"]["marker_side_mm"]==60.0
    out["check_status"]["ID7_60mm_detectable"]="PASS" if marker_ok else "FAIL"
    if not marker_ok:out["errors"].append(f"expected detectable ID 7, got {ids}")
    if marker_ok:
        corners_detected=marker_corners[ids.index(7)][0]
        planted=np.asarray(pm["marker"]["image_corners_px"],dtype=np.float32)
        # Compare corner sets while allowing image orientation changes from the
        # marker's world-to-camera rotation. Pose corners remain saved in Blender
        # world/camera metadata independently of this detector diagnostic.
        reproj=min(float(np.linalg.norm(corners_detected[list(order)]-planted,axis=1).mean())
                   for order in itertools.permutations(range(4)))
        out["marker_corner_mean_error_px"]=reproj
        pose_ok=reproj<=8.0
        out["check_status"]["marker_pose_projection"]="PASS" if pose_ok else "REVIEW_REQUIRED"
        if not pose_ok:out["warnings"]=[f"detected vs projected marker corner-set error {reproj:.2f}px; review printed marker pose"]
    out["check_status"]["human_visual_identity"]="PENDING"
    out["check_status"]["human_realism"]="PENDING"
    out["check_status"]["human_label_validity_review"]="PENDING"
    out["pair_automated_result"]="PASS" if not out["errors"] else "FAIL"
    return out


def make_review_artifacts(rows,pair_results):
    # Visual grid: each row is one portion/scene variation, not an approval score.
    columns=["Eligible WED TRAIN reference","Existing renderer","Complete-food mesh preview","Ingredient recipe — ID7 card","Same scene — no card"]
    thumbs=(256,192);gap=12;header=58;row_h=thumbs[1]+46
    isolated_rows=[r for r in rows if r["scene_kind"]=="isolated" and r["card_present"]]
    sheet=Image.new("RGB",(len(columns)*thumbs[0]+(len(columns)+1)*gap,
                            header+len(isolated_rows)*row_h+gap),"#f4f1e8")
    draw=ImageDraw.Draw(sheet);f=load_font(15);fs=load_font(11)
    for i,title in enumerate(columns):draw.text((gap+i*(thumbs[0]+gap),10),title,fill="#24352c",font=f)
    old_manifest=[json.loads(x) for x in (OLD/"manifest.jsonl").read_text().splitlines()]
    old_by_class={}
    for r in old_manifest:
        if r.get("scene_kind")=="isolated_dish":
            a=r["annotations"][0]
            if a["class_id"] in {1,12,32}:old_by_class.setdefault(a["class_id"],r)
    for ridx,row in enumerate(isolated_rows):
        meta=json.loads((OUT/row["metadata"]).read_text())
        class_component=meta["components"][0]
        class_id=class_component["class_id"]
        class_name=class_component["name"]
        q=row["pair_id"].rsplit("_",1)[-1]
        class_rows=[x for x in rows if x["pair_id"]==row["pair_id"]]
        y=header+ridx*row_h
        draw.text((gap,y-2),f"{class_name} · {q} · estimate {class_component['estimated_mass_g']:.1f} g (density assumption)",fill="#24352c",font=fs)
        ref=OLD/"references"/f"class_{class_id:02d}"/"wed_train_crop.png"
        old=OLD/old_by_class[class_id]["rgb_path"]
        mesh=MESH/f"{class_name}.png"
        if not mesh.exists():mesh=MESH/("Bottle-gourd-curry.png" if class_id==1 else "chicken-dum-biryani.png" if class_id==12 else "salad.png")
        no_card=next((x for x in class_rows if not x["card_present"]),None)
        paths=[ref,old,mesh,OUT/row["rgb"],OUT/no_card["rgb"] if no_card else OUT/row["rgb"]]
        for col,path in enumerate(paths):
            im=Image.open(path).convert("RGB");im.thumbnail(thumbs)
            tile=Image.new("RGB",thumbs,"white");tile.paste(im,((thumbs[0]-im.width)//2,(thumbs[1]-im.height)//2))
            x=gap+col*(thumbs[0]+gap);sheet.paste(tile,(x,y+16))
    sheet.save(OUT/"comparison_contact_sheet.png")

    # Composed gallery with pairs shown side by side.
    comp=[r for r in rows if r["scene_kind"]=="composed" and r["card_present"]]
    cw,ch=448,336;gallery=Image.new("RGB",(2*cw+3*gap,len(comp)*(ch+65)+gap),"#f4f1e8");gd=ImageDraw.Draw(gallery)
    for i,row in enumerate(comp):
        pair=[x for x in rows if x["pair_id"]==row["pair_id"]]
        y=gap+i*(ch+65);gd.text((gap,y),row["pair_id"]+" — same composition, card / no-card",fill="#24352c",font=f)
        for j,r in enumerate(sorted(pair,key=lambda x:not x["card_present"])):
            im=Image.open(OUT/r["rgb"]).convert("RGB");gallery.paste(im,(gap+j*(cw+gap),y+25))
    gallery.save(OUT/"composed_pairs.png")

    review_path=OUT/"human_review.csv"
    fields=["pair_id","scene_kind","class_names","portion_quantiles","card_pair_consistency","class_identity",
            "ingredient_composition","visual_realism","shape_and_portion","texture_and_color","artifacts",
            "mask_validity","metric_depth_validity","geometry_volume_validity","mass_density_provenance",
            "marker_detection_and_pose","reviewer_comments"]
    with review_path.open("w",newline="",encoding="utf-8") as fobj:
        writer=csv.DictWriter(fobj,fieldnames=fields);writer.writeheader()
        for pid,members in sorted(row_pairs(rows).items()):
            first=members[0];meta=json.loads((OUT/first["metadata"]).read_text())
            writer.writerow({"pair_id":pid,"scene_kind":first["scene_kind"],
                "class_names":";".join(c["name"] for c in meta["components"]),
                "portion_quantiles":";".join(f"{c['portion_conditioning_g']:.1f}g" for c in meta["components"]),
                "card_pair_consistency":"PASS / LOW-LEVEL RENDER TOLERANCE" if next((p for p in pair_results if p['pair_id']==pid),{}).get('pair_automated_result')=='PASS' else "FAIL",
                "class_identity":"PENDING","ingredient_composition":"PENDING","visual_realism":"PENDING",
                "shape_and_portion":"PENDING","texture_and_color":"PENDING","artifacts":"PENDING",
                "mask_validity":"PENDING","metric_depth_validity":"PENDING","geometry_volume_validity":"PENDING",
                "mass_density_provenance":"ASSUMPTION REVIEW","marker_detection_and_pose":"PASS/REVIEW based on pair audit",
                "reviewer_comments":""})
    # Copyable browser gallery with all paired images and saved diagnostics.
    items=[]
    for r in rows:
        meta=json.loads((OUT/r["metadata"]).read_text())
        names=", ".join(c["name"]+f" (~{c['estimated_mass_g']:.1f} g estimate)" for c in meta["components"])
        items.append(f'<article><h3>{r["pair_id"]} · {"card" if r["card_present"] else "no card"}</h3><p>{names}</p><img src="{r["rgb"]}"><img src="{r["mask"]}"><details><summary>Geometry / depth provenance</summary><pre>{json.dumps({"camera":meta["camera"],"marker":meta["marker"],"components":meta["components"],"task_status":"pending human review"},indent=2)}</pre></details></article>')
    html="""<!doctype html><meta charset='utf-8'><title>Ingredient Blender Pilot Review</title><style>body{font:16px system-ui;margin:24px;background:#f4f1e8;color:#20332a}h1{max-width:950px}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px}article{background:#fff;border-radius:16px;padding:14px;box-shadow:0 4px 18px #19261d18}img{width:49%;object-fit:contain;background:#eee}pre{max-height:420px;overflow:auto;font-size:11px}summary{cursor:pointer}</style><h1>Ingredient-level Blender pilot — human review pending</h1><p>Visual identity, realism and task-label acceptance are not auto-approved. MetaFood3D previews are noncommercial proxies. All masses use geometry volume × an uncertain class-density prior.</p><section>"""+"".join(items)+"</section>"
    (OUT/"gallery.html").write_text(html,encoding="utf-8")


def main():
    manifest=json.loads((OUT/"manifest.json").read_text())
    rows=manifest["manifest"]
    pair_results=[verify_pair(pid,members) for pid,members in sorted(row_pairs(rows).items())]
    task_errors=[]
    for row in rows:
        meta=json.loads((OUT/row["metadata"]).read_text())
        mask=cv2.imread(str(OUT/row["mask"]),cv2.IMREAD_UNCHANGED)
        depth=np.load(OUT/row["metric_depth"])
        present={int(v) for v in np.unique(mask) if v}
        expected={int(c["class_id"]) for c in meta["components"]}
        if present!=expected:task_errors.append(f"{row['sample_id']}: class mask IDs {present} != expected {expected}")
        if mask.shape!=(336,448):task_errors.append(f"{row['sample_id']}: mask dimensions differ")
        if np.count_nonzero(mask)==0:task_errors.append(f"{row['sample_id']}: empty food mask")
        if not np.isfinite(depth).all() or np.any(depth[mask>0]<=0):task_errors.append(f"{row['sample_id']}: invalid food metric depth")
        total_v=sum(float(c["volume_ml"]) for c in meta["components"])
        total_m=sum(float(c["estimated_mass_g"]) for c in meta["components"])
        if total_v<=0 or abs(total_m-meta["total_food_mass_estimate_g"])>1e-4:task_errors.append(f"{row['sample_id']}: volume/mass bundle inconsistency")
        for c in meta["components"]:
            if abs(c["estimated_mass_g"]-c["volume_ml"]*c["density_g_ml"])>0.02:task_errors.append(f"{row['sample_id']}: {c['name']} estimate != volume × density")
            if c["density_status"].find("assumed_not_measured")<0:task_errors.append(f"{row['sample_id']}: missing assumed density status")
        im=np.load(OUT/row["ingredient_instances"])
        mapped={int(x) for x in meta["ingredient_instance_ids_present"]}
        if {int(v) for v in np.unique(im) if v}!=mapped:task_errors.append(f"{row['sample_id']}: ingredient instance map mismatch")
        if not set(meta["mask_class_ids_present"]).issubset({c["class_id"] for c in meta["components"]}):
            task_errors.append(f"{row['sample_id']}: semantic class IDs unexpected")
    marker_pairs_ok=all(p["check_status"].get("ID7_60mm_detectable")=="PASS"
                        and p["check_status"].get("marker_pose_projection")=="PASS"
                        for p in pair_results)
    validation={"image_count":len(rows),"pair_count":len(pair_results),
        "pair_results":pair_results,"task_geometry_errors":task_errors,
        "automated_result":"PASS" if not task_errors and all(p["pair_automated_result"]=="PASS" for p in pair_results) else "FAIL",
        "automated_task_checks":{
            "semantic_masks":"PASS" if not task_errors else "FAIL",
            "metric_depth":"PASS" if not task_errors else "FAIL",
            "geometry_volume":"PASS" if not task_errors else "FAIL",
            "mass_density":"ASSUMPTION_ONLY; volume × uncertain class prior, not measured ground truth",
            "marker_detection_and_pose":"PASS" if marker_pairs_ok else "FAIL",
            "class_identity":"REVIEW_REQUIRED; recipe label is assigned and not independently inferred",
            "ingredient_composition":"REVIEW_REQUIRED; recipe hypotheses, not WED pixel labels",
            "visual_realism":"REVIEW_REQUIRED; no automatic approval"},
        "human_identity":"PENDING","human_realism":"PENDING","human_label_approval":"PENDING",
        "no_DEV_or_protected_inputs":True,"full_corpus_generated":False,"production_models_trained":False}
    (OUT/"validation.json").write_text(json.dumps(validation,indent=2,sort_keys=True)+"\n")
    make_review_artifacts(rows,pair_results)
    print(json.dumps({"result":validation["automated_result"],"images":len(rows),"pairs":len(pair_results),"errors":task_errors,
                      "pair_failures":[p for p in pair_results if p["pair_automated_result"]!="PASS"]},indent=2))


if __name__=="__main__":main()
