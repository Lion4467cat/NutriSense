"""Guard the DEV diagnostic metrics and plate-cluster bootstrap."""
from tools import eval_weight_diagnostics as diag


def test_point_metrics_include_mae_bias_rmse_and_relative_error():
    rows = [
        {"pred": 12.0, "gt": 10.0},
        {"pred": 7.0, "gt": 10.0},
    ]
    out = diag._metrics(rows)
    assert out["mae_g"] == 2.5
    assert out["median_absolute_error_g"] == 2.5
    assert out["rmse_g"] == 2.55
    assert out["mean_bias_g"] == -0.5
    assert out["mape_pct"] == 25.0


def test_plate_total_averages_repeated_views_before_summing_dishes():
    rows = [
        {"plate": "p1", "dish": "rice", "pred": 90.0, "gt": 100.0},
        {"plate": "p1", "dish": "rice", "pred": 110.0, "gt": 100.0},
        {"plate": "p1", "dish": "dal", "pred": 40.0, "gt": 50.0},
        {"plate": "p2", "dish": "rice", "pred": 80.0, "gt": 100.0},
    ]
    out = diag._plate_totals(rows)
    assert out[0]["predicted_total_g"] == 140.0
    assert out[0]["ground_truth_total_g"] == 150.0
    assert out[0]["n_views"] == 3


def test_grouped_bootstrap_is_plate_clustered_and_reproducible():
    rows = [
        {"plate": "p1", "dish": "rice", "pred": 90.0, "gt": 100.0},
        {"plate": "p1", "dish": "dal", "pred": 45.0, "gt": 50.0},
        {"plate": "p2", "dish": "rice", "pred": 80.0, "gt": 100.0},
    ]
    plates = diag._plate_totals(rows)
    first = diag._add_grouped_intervals(rows, plates)
    second = diag._add_grouped_intervals(rows, plates)
    assert first == second
    assert set(first) == {"item_mae_g", "item_bias_g",
                          "plate_total_mae_g", "plate_total_bias_g"}
    assert all(len(interval) == 2 for interval in first.values())


def test_wed_target_must_be_constant_over_views():
    rows = [
        {"plate": "p1", "dish": "rice", "pred": 90.0, "gt": 100.0},
        {"plate": "p1", "dish": "rice", "pred": 95.0, "gt": 101.0},
    ]
    try:
        diag._plate_totals(rows)
    except ValueError as exc:
        assert "target changes across views" in str(exc)
    else:
        raise AssertionError("inconsistent per-view target was accepted")
