import { useState } from "react";
import type { ItemBlock } from "../types/contract.gen";

type Box = { index: number; x: number; y: number; width: number; height: number };

function validBoxes(items: ItemBlock[], width: number, height: number): Box[] {
  return items.flatMap((item, index) => {
    const bounds = item.bbox;
    if (!bounds || bounds.length !== 4 || !bounds.every(Number.isFinite)) return [];
    const [x0, y0, x1, y1] = bounds;
    const x = Math.max(0, Math.min(width, x0));
    const y = Math.max(0, Math.min(height, y0));
    const right = Math.max(0, Math.min(width, x1));
    const bottom = Math.max(0, Math.min(height, y1));
    return right > x && bottom > y
      ? [{ index, x, y, width: right - x, height: bottom - y }]
      : [];
  });
}

/** A photo-first view of returned region bounds. Bounds are not pixel masks. */
export default function MealRegionFigure({
  photo,
  items = [],
  demo = false,
  className = "",
}: {
  photo: string;
  items?: ItemBlock[];
  demo?: boolean;
  className?: string;
}) {
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const boxes = !demo && dimensions.width > 0 && dimensions.height > 0
    ? validBoxes(items, dimensions.width, dimensions.height)
    : [];

  return (
    <figure className={`result-photo meal-region-figure ${className}`.trim()}>
      <div className="meal-photo-frame">
        <img
          src={photo}
          alt="Analyzed meal"
          onLoad={(event) => setDimensions({
            width: event.currentTarget.naturalWidth,
            height: event.currentTarget.naturalHeight,
          })}
        />
        {boxes.length > 0 && (
          <>
            <svg
              className="meal-region-svg"
              viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
              preserveAspectRatio="none"
              role="img"
              aria-label={`${boxes.length} returned food region bounds, shown as rectangles`}
            >
              {boxes.map((box) => (
                <rect
                  key={box.index}
                  x={box.x}
                  y={box.y}
                  width={box.width}
                  height={box.height}
                  rx={Math.max(8, dimensions.width * 0.009)}
                  className="meal-region-box"
                />
              ))}
            </svg>
            <ol className="meal-region-markers" aria-hidden="true">
              {boxes.map((box) => (
                <li
                  key={box.index}
                  style={{ left: `${(box.x / dimensions.width) * 100}%`, top: `${(box.y / dimensions.height) * 100}%` }}
                >
                  {box.index + 1}
                </li>
              ))}
            </ol>
          </>
        )}
      </div>
      <figcaption>
        {boxes.length > 0
          ? "Returned region bounds · rectangles do not represent pixel masks"
          : "Captured meal"}
      </figcaption>
    </figure>
  );
}
