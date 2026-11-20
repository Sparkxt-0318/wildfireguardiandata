import pytest

from firewitness.fuel import spread

pytestmark = pytest.mark.skipif(not spread.available(), reason="pyretechnics not installed (firewitness/fuel/scripts/setup_pyretechnics.sh)")


def test_head_rate_order_and_nonburnable():
    mo = (0.03, 0.04, 0.06, 0.4, 0.6)
    gr2 = spread.head_rate(102, 8.0, 270.0, 0.0, 0.0, 0.0, 0.0, *mo)
    tl3 = spread.head_rate(183, 8.0, 270.0, 0.0, 0.0, 0.0, 0.0, *mo)
    assert gr2 > tl3 > 0
    assert spread.head_rate(99, 8.0, 270.0, 0.0, 0.0, 0.0, 0.0, *mo) == 0.0
    # more wind, more spread
    assert spread.head_rate(102, 12.0, 270.0, 0.0, 0.0, 0.0, 0.0, *mo) > gr2
