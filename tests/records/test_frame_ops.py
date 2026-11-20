import pandas as pd
import pytest

from firewitness.core import Patch, PatchConflict, missing
from firewitness.records import frame_ops as F


def table():
    return pd.DataFrame({"rid": ["1", "2", "3"], "name": ["A ", "B", ""], "acres": ["10", "-999", "5"]})


def test_apply_revert_byte_for_byte():
    t = table()
    ps = [Patch("1", "name", "A ", "A", "val:hidden"), Patch("2", "acres", "-999", missing(), "val:placeholder"),
          Patch("3", "name", missing(), "C", "x"), Patch("2", "dup_of", missing(), "1", "dup")]
    c = F.apply_frame(t, ps, "rid")
    assert c.loc[1, "acres"] == "" and c.loc[2, "name"] == "C" and c.loc[1, "dup_of"] == "1"
    assert t.equals(table())
    assert F.changed_cells(t, c, "rid") == {("1", "name"), ("2", "acres"), ("3", "name"), ("2", "dup_of")}
    back = F.revert_frame(c, ps, "rid", t.columns)
    assert F.sha256_frame(back) == F.sha256_frame(t)


def test_strict_conflict():
    with pytest.raises(PatchConflict):
        F.apply_frame(table(), [Patch("1", "acres", "99", "1", "r")], "rid")
