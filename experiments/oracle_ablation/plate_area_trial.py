"""Read-only CV trial for fitting plate references from the ArUco photos."""
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT.parent / "Aruco_7ID_60mm_with_food"


def main() -> None:
    files = sorted(p for p in DATA.glob("Dish */*")
                   if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    print("method=grayscale Hough gradient circles on 600px-wide full-frame resize")
    print("params=medianBlur(7), dp=1.2, minDist=120, param1=100, param2=28, radius=80..260")
    print("warning=circles are candidates only; not accepted as plate fits")
    for path in files:
        image = cv2.imread(str(path))
        h, w = image.shape[:2]
        small = cv2.resize(image, (600, round(600 * h / w)))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        circles = cv2.HoughCircles(
            cv2.medianBlur(gray, 7), cv2.HOUGH_GRADIENT, dp=1.2,
            minDist=120, param1=100, param2=28, minRadius=80, maxRadius=260)
        values = [] if circles is None else [
            [round(float(v), 1) for v in circle]
            for circle in circles[0][:12]]
        print(f"{path.parent.name}|{path.name}|shape={h}x{w}|candidate_count="
              f"{0 if circles is None else len(circles[0])}|top_candidates={values}")


if __name__ == "__main__":
    main()
