import pandas as pd
from app.services.visualization_service import _render_bokeh, BOKEH_AVAILABLE


def make_df():
    return pd.DataFrame({
        'a': [1,2,2,3,4,5,100],
        'b': [10,11,10,13,14,15,16],
        'c': ['x','y','x','y','x','z','x']
    })


def test_render_hist():
    df = make_df()
    spec = {'type': 'hist', 'x': 'a', 'title': 'hist a'}
    html = _render_bokeh(df, spec)
    if BOKEH_AVAILABLE:
        assert html is not None and '<script' in html
    else:
        assert html is None


def test_render_count():
    df = make_df()
    spec = {'type': 'count', 'x': 'c', 'title': 'counts c'}
    html = _render_bokeh(df, spec)
    if BOKEH_AVAILABLE:
        assert html is not None and '<div' in html
    else:
        assert html is None


def test_render_scatter():
    df = make_df()
    spec = {'type': 'scatter', 'x': 'a', 'y': 'b', 'hue': 'c', 'title': 'scatter'}
    html = _render_bokeh(df, spec)
    if BOKEH_AVAILABLE:
        assert html is not None
    else:
        assert html is None


def test_render_heatmap():
    df = make_df()
    spec = {'type': 'heatmap', 'title': 'corr'}
    html = _render_bokeh(df, spec)
    if BOKEH_AVAILABLE:
        assert html is not None
    else:
        assert html is None
