from tools.eval_class_bias_calibration import cross_fitted


def _rows() -> list[dict]:
    rows = []
    for index, residual in enumerate((10.0, 20.0, 30.0, 40.0, 50.0, 60.0)):
        rows.append({"plate": f"p{index}", "dish": "rice",
                     "pred": 100.0 + residual, "gt": 100.0})
    return rows


def test_cross_fitted_correction_uses_other_plates_only() -> None:
    rows = _rows()
    corrected, procedure = cross_fitted(rows)
    by_plate = {row["plate"]: row for row in corrected}
    assert by_plate["p0"]["correction_g"] == 40.0
    assert by_plate["p5"]["correction_g"] == 30.0
    assert procedure["minimum_other_plate_support"] == 5
    changed = _rows()
    changed[0] = {**changed[0], "pred": 10_000.0}
    corrected_after, _ = cross_fitted(changed)
    # p0's own held-out residual cannot affect the p0 correction.
    assert corrected_after[0]["correction_g"] == by_plate["p0"]["correction_g"]


def test_insufficient_other_plate_support_falls_back_to_zero() -> None:
    rows = _rows()[:4]
    corrected, _ = cross_fitted(rows)
    assert all(row["correction_g"] == 0.0 for row in corrected)
