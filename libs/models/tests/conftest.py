# Fixtures are imported directly instead of via `pytest_plugins`: defining
# `pytest_plugins` in a non-top-level conftest is no longer supported by pytest.
from fixtures_models.models import (  # noqa: E402,F401
    bid,
    bid_factory,
    metrics,
    metrics_factory,
    put_result,
    put_result_factory,
)
