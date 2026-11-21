import numpy as np

from firewitness.score import negatives, splits
from firewitness.score.adapters import caught, live
from firewitness.score.dataset import FIRE, NO_FIRE, UNKNOWN, Dataset


def _sq(x0, y0, x1, y1):
    return {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}


def _caught_rows(n=6):
    rows = []
    for i in range(n):
        lon, lat = -120.0 + 0.5 * i, 38.0
        d = 0.01   # about 1 km
        rows += [
            {"rid": f"FOD{i}", "state": "fire", "geometry": _sq(lon, lat, lon + d / 4, lat + d / 4), "t0": "2020-07-01", "t1": "2020-07-03", "tier": "verified"},
            # clear look, can see burns >= 2,000 m2: verifies cells of 0.05 km (2,500 m2) and larger only
            {"rid": f"FOD{i}", "state": "no_fire", "geometry": _sq(lon + d / 4, lat, lon + d, lat + d / 2), "t0": "2020-06-28", "t1": "2020-07-06", "floor_m2": 2000.0, "tier": "verified"},
            # a second no_fire area seen through a coarse look: floor 90,000 m2 cannot verify a small cell
            {"rid": f"FOD{i}", "state": "no_fire", "geometry": _sq(lon, lat + d / 2, lon + d, lat + d), "t0": "2020-06-28", "t1": "2020-07-06", "floor_m2": 90000.0, "tier": "verified"},
            {"rid": f"FOD{i}", "state": "unknown", "geometry": _sq(lon + d / 4, lat, lon + d / 2, lat + d / 8), "t0": "2020-06-28", "t1": "2020-07-06", "tier": "verified"},
        ]
    return rows


def test_caught_adapter_three_states_and_floor_rule():
    ds = caught.from_rows(_caught_rows(), cell_km=0.05, cell_from_floor=False)
    assert len(ds.scenes) == 6
    s = ds.scenes["FOD0"]
    assert (s.state == FIRE).any() and (s.state == NO_FIRE).any()
    assert "floor_m2" in s.static
    # fire only inside the fire interval, no fire label before it
    assert not (s.state[0] == FIRE).any() and (s.state[3:5] == FIRE).any()
    r = negatives.sample(ds, ds.ids(), k=2, buffer_cells=0)
    t = r["table"]
    neg = t["label"] == 0
    assert neg.any() and r["stats"]["source"]["floor_m2_rule"]
    ids = r["fires"]
    for f, tt, y, x in zip(t["fire"][neg], t["t"][neg], t["y"][neg], t["x"][neg]):
        s = ds.scenes[ids[f]]
        assert s.state[tt, y, x] == NO_FIRE                       # only verified no fire
        assert s.static["floor_m2"][y, x] <= (s.cell_km * 1000) ** 2   # and only where the look could see a burn of cell size
    assert set(r["stats"]["source"]["match_keys_unavailable"]) == {"danger", "landcover"}


def test_negatives_fall_back_to_benchmark_masks_when_no_floor(ds):
    sp = splits.make(ds, "space")
    r = negatives.sample(ds, sp["folds"]["train"], k=2)
    assert r["stats"]["source"]["floor_m2_rule"] is False and r["stats"]["source"]["match_keys_unavailable"] == []


def test_live_adapter_onset_and_pre_ignition_negatives():
    rows = [{"fire_id": "F1", "lat": "36.0", "lon": "-119.9", "acres": "50", "discovery_t": "1688789220"}]
    ds = live.from_rows(rows)
    s = ds.scenes["F1"]
    assert s.meta["record_only"] and "not satellite verified" in s.meta["negatives"]
    fire_days = [int((s.state[t] == FIRE).sum()) for t in range(len(s.dates))]
    assert fire_days[0] == 0 and fire_days[-1] > 0
    assert (s.state[0] == NO_FIRE).any() and (s.state == UNKNOWN).any()


def test_space_time_split_is_blocked_in_space_and_time_and_by_fire(ds):
    sp = splits.make(ds, "space_time")
    f = sp["folds"]
    assert f["train"] and f["val"] and f["test"]
    assert not (set(f["train"]) & set(f["test"]) or set(f["train"]) & set(f["val"]) or set(f["val"]) & set(f["test"]))
    desc = {x: splits.fire_descriptor(ds.scenes[x]) for x in ds.ids()}
    xy = {x: splits._xy_km(desc[x]["lat"], desc[x]["lon"]) for x in ds.ids()}
    blk = lambda x: (int(xy[x][0] // 100), int(xy[x][1] // 100))
    yrs = lambda fold: {desc[x]["year"] for x in f[fold]}
    blks = lambda fold: {blk(x) for x in f[fold]}
    assert not (blks("train") & blks("test")) and not (yrs("train") & yrs("test"))
    assert not (blks("train") & blks("val")) and not (yrs("train") & yrs("val"))
    assert any(d["reason"].startswith("cross") for d in sp["dropped"])


def test_caught_cell_is_sized_to_the_look_floor():
    ds = caught.from_rows(_caught_rows(), max_cells=400)
    s = ds.scenes["FOD0"]
    assert s.cell_km >= (90000.0 ** 0.5) / 1000.0 - 1e-9          # largest finite floor sets the minimum cell
    f = s.static["floor_m2"]
    assert ((s.state == NO_FIRE).any(0) <= (f <= (s.cell_km * 1000) ** 2)).all()


def test_live_onset_table_with_iso_intervals(tmp_path):
    onset = tmp_path / "onset.csv"
    fires = tmp_path / "fires.csv"
    onset.write_text("fire_id,acres,label_kind,onset_lo_t,onset_hi_t,label_utc,T0\n"
                     "F1,60,two witnesses,2023-07-02T03:00:00Z,2023-07-03T01:00:00Z,2023-07-03T01:00:00Z,2023-07-03T20:00:00Z\n"
                     "F2,50,no earlier onset (anchor kept),,,2023-07-05T12:00:00Z,2023-07-05T12:00:00Z\n")
    fires.write_text("fire_id,lat,lon,acres\nF1,36.0,-119.9,60\nF2,37.0,-120.1,50\n")
    ds = live.read_onset(str(onset), str(fires))
    a, b = ds.scenes["F1"], ds.scenes["F2"]
    assert not a.meta["record_only"] and b.meta["record_only"]
    assert a.interval_slack >= 1
    fire_day = lambda s: int(np.argmax([(s.state[t] == FIRE).any() for t in range(len(s.dates))]))
    # fire starts on the day of onset_hi (July 3) for F1, on the anchor day for F2
    import datetime as dt
    assert dt.date.fromordinal(int(a.dates[fire_day(a)])) == dt.date(2023, 7, 3)
    assert dt.date.fromordinal(int(b.dates[fire_day(b)])) == dt.date(2023, 7, 5)
