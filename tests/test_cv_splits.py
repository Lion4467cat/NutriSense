from tools.train_weight_head import split_grouped_cv_fold


def _rows(n_plates: int = 30):
    return [
        {"date_key": f"date_{i:02d}", "set": "setA", "view": view}
        for i in range(n_plates) for view in range(2)
    ]


def test_outer_folds_exclude_fixed_dev_and_keep_each_plate_whole():
    rows = _rows()
    outer_seen = []
    excluded_sets = []
    for fold in range(5):
        fit, held, excluded = split_grouped_cv_fold(rows, 5, fold)
        fit_groups = {f"{r['date_key']}_{r['set']}" for r in fit}
        held_groups = {f"{r['date_key']}_{r['set']}" for r in held}
        assert fit_groups.isdisjoint(held_groups)
        assert not (fit_groups | held_groups) & excluded
        assert len(held) == 2 * len(held_groups)
        outer_seen.extend(held_groups)
        excluded_sets.append(excluded)
    assert all(value == excluded_sets[0] for value in excluded_sets)
    assert len(outer_seen) == len(set(outer_seen))
    assert len(outer_seen) + len(excluded_sets[0]) == 30


def test_grouped_cv_rejects_invalid_fold_index():
    try:
        split_grouped_cv_fold(_rows(), 5, 5)
    except ValueError as exc:
        assert "fold count/index" in str(exc)
    else:
        raise AssertionError("invalid fold index accepted")
