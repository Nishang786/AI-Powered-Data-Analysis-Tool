import base64

import pandas as pd
import pytest

from app.services.visualization_service import _render


@pytest.fixture
def dataframe():
    return pd.DataFrame(
        {
            "a": [1, 2, 2, 3, 4, 5, 100],
            "b": [10, 11, 10, 13, 14, 15, 16],
            "c": ["x", "y", "x", "y", "x", "z", "x"],
        }
    )


@pytest.mark.parametrize(
    "spec",
    [
        {"type": "hist", "x": "a", "title": "hist a"},
        {"type": "count", "x": "c", "title": "counts c"},
        {"type": "scatter", "x": "a", "y": "b", "hue": "c", "title": "scatter"},
        {"type": "heatmap", "title": "correlation"},
    ],
)
def test_render_returns_png_image(dataframe, spec):
    rendered = _render(dataframe, spec)

    assert base64.b64decode(rendered).startswith(b"\x89PNG\r\n\x1a\n")
