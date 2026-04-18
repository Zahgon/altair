"""Magic functions for rendering vega-lite specifications."""

from __future__ import annotations

import json
import warnings
from importlib.util import find_spec
from typing import Any

from IPython.core import magic_arguments
from narwhals.stable.v1.dependencies import is_pandas_dataframe

from altair.vegalite import v6 as vegalite_v6

__all__ = ["vegalite"]

RENDERERS = {
    "vega-lite": {
        "6": vegalite_v6.VegaLite,
    },
}


TRANSFORMERS = {
    "vega-lite": {
        "6": vegalite_v6.data_transformers,
    },
}


def _prepare_data(data, data_transformers):
    """Convert input data to data for use within schema."""
    if data is None or isinstance(data, dict):
        return data
    elif is_pandas_dataframe(data):
        if func := data_transformers.get():
            data = func(data)
        return data
    elif isinstance(data, str):
        return {"url": data}
    else:
        warnings.warn(f"data of type {type(data)} not recognized", stacklevel=1)
        return data


def _get_variable(name: str) -> Any:
    """Get a variable from the notebook namespace."""
    pass


@magic_arguments.magic_arguments()
@magic_arguments.argument(
    "data",
    nargs="?",
    help="local variablename of a pandas DataFrame to be used as the dataset",
)
@magic_arguments.argument("-v", "--version", dest="version", default="v6")
@magic_arguments.argument("-j", "--json", dest="json", action="store_true")
def vegalite(line, cell) -> vegalite_v6.VegaLite:
    """
    Cell magic for displaying vega-lite visualizations in CoLab.

    %%vegalite [dataframe] [--json] [--version='v6']

    Visualize the contents of the cell using Vega-Lite, optionally
    specifying a pandas DataFrame object to be used as the dataset.

    if --json is passed, then input is parsed as json rather than yaml.
    """
    pass
