"""Check captured analysis results against the earlier raw ArUco evaluation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def records(path: Path) -> dict[str, dict]:
    out = {}
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row.get("event") == "image_result" and row.get("mode") == "default":
            out[row["image"]] = row
    return out


def sha(value: object) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode()).hexdigest()


def main() -> None:
    old = records(ROOT / "aruco_raw.jsonl")
    new = records(ROOT / "aruco_mask_capture.jsonl")
    different = [p for p in sorted(set(old) & set(new))
                 if old[p]["result"] != new[p]["result"]]
    print(f"baseline_default_images={len(old)} capture_default_images={len(new)} "
          f"same_paths={set(old) == set(new)}")
    print(f"identical_result_objects={len(set(old) & set(new)) - len(different)} "
          f"different_result_objects={len(different)}")
    for path in different:
        before = old[path]["result"]
        after = new[path]["result"]
        bitems = before.get("items") or []
        aitems = after.get("items") or []
        print(f"difference={path}")
        print(f"  old_item_count={len(bitems)} new_item_count={len(aitems)} "
              f"old_total={(before.get('portion') or {}).get('grams')} "
              f"new_total={(after.get('portion') or {}).get('grams')}")
        print(f"  old_skipped_reasons={[x.get('reason') for x in bitems if x.get('reason')]} "
              f"new_skipped_reasons={[x.get('reason') for x in aitems if x.get('reason')]}")
    p = min(old)
    print(f"chosen_flag_off_replay_image={Path(p).name}")
    print(f"earlier_result_sha256={sha(old[p]['result'])}")
    replay_lines = (ROOT / "aruco_flag_off_replay.jsonl").read_text().splitlines()
    replay = next(json.loads(line) for line in replay_lines
                  if json.loads(line).get("event") == "image_result")
    print(f"flag_off_result_sha256={sha(replay['result'])}")
    print(f"earlier_equals_flag_off={old[p]['result'] == replay['result']}")
    print(f"mask_capture_equals_earlier={old[p]['result'] == new[p]['result']}")
    print(f"replay_cuda_device={json.loads(replay_lines[0]).get('cuda_device')}")


if __name__ == "__main__":
    main()
