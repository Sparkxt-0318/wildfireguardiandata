import pytest

from firewitness.score.adapters import synthetic


@pytest.fixture(scope="session")
def ds():
    return synthetic.build(90, 40, seed=3)
