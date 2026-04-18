from __future__ import annotations

import json
import pathlib
from typing import Any

import anywidget
import traitlets

import altair as alt
from altair import TopLevelSpec
from altair.utils._vegafusion_data import (
    compile_to_vegafusion_chart_state,
    using_vegafusion,
)
from altair.utils.selection import IndexSelection, IntervalSelection, PointSelection

_here = pathlib.Path(__file__).parent


class Params(traitlets.HasTraits):
    """Traitlet class storing a JupyterChart's params."""

    def __init__(self, trait_values):
        super().__init__()

        for key, value in trait_values.items():
            if isinstance(value, (int, float)):
                traitlet_type = traitlets.Float()
            elif isinstance(value, str):
                traitlet_type = traitlets.Unicode()
            elif isinstance(value, list):
                traitlet_type = traitlets.List()
            elif isinstance(value, dict):
                traitlet_type = traitlets.Dict()
            else:
                traitlet_type = traitlets.Any()

            # Add the new trait.
            self.add_traits(**{key: traitlet_type})

            # Set the trait's value.
            setattr(self, key, value)

    def __repr__(self):
        return f"Params({self.trait_values()})"


class Selections(traitlets.HasTraits):
    """Traitlet class storing a JupyterChart's selections."""

    def __init__(self, trait_values):
        super().__init__()

        for key, value in trait_values.items():
            if isinstance(value, IndexSelection):
                traitlet_type = traitlets.Instance(IndexSelection)
            elif isinstance(value, PointSelection):
                traitlet_type = traitlets.Instance(PointSelection)
            elif isinstance(value, IntervalSelection):
                traitlet_type = traitlets.Instance(IntervalSelection)
            else:
                msg = f"Unexpected selection type: {type(value)}"
                raise ValueError(msg)

            # Add the new trait.
            self.add_traits(**{key: traitlet_type})

            # Set the trait's value.
            setattr(self, key, value)

            # Make read-only
            self.observe(self._make_read_only, names=key)

    def __repr__(self):
        return f"Selections({self.trait_values()})"

    def _make_read_only(self, change):
        """Work around to make traits read-only, but still allow us to change them internally."""
        pass

    def _set_value(self, key, value):
        pass


def load_js_src() -> str:
    return (_here / "js" / "index.js").read_text()


class JupyterChart(anywidget.AnyWidget):
    _esm = load_js_src()
    _css = r"""
    .vega-embed {
        /* Make sure action menu isn't cut off */
        overflow: visible;
    }
    """

    # Public traitlets
    chart = traitlets.Instance(TopLevelSpec, allow_none=True)
    spec = traitlets.Dict(allow_none=True).tag(sync=True)
    debounce_wait = traitlets.Float(default_value=10).tag(sync=True)
    max_wait = traitlets.Bool(default_value=True).tag(sync=True)
    local_tz = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    debug = traitlets.Bool(default_value=False)
    embed_options = traitlets.Dict(default_value=None, allow_none=True).tag(sync=True)

    # Internal selection traitlets
    _selection_types = traitlets.Dict()
    _vl_selections = traitlets.Dict().tag(sync=True)

    # Internal param traitlets
    _params = traitlets.Dict().tag(sync=True)

    # Internal comm traitlets for VegaFusion support
    _chart_state = traitlets.Any(allow_none=True)
    _js_watch_plan = traitlets.Any(allow_none=True).tag(sync=True)
    _js_to_py_updates = traitlets.Any(allow_none=True).tag(sync=True)
    _py_to_js_updates = traitlets.Any(allow_none=True).tag(sync=True)

    # Track whether charts are configured for offline use
    _is_offline = False

    @classmethod
    def enable_offline(cls, offline: bool = True):
        """
        Configure JupyterChart's offline behavior.

        Parameters
        ----------
        offline: bool
            If True, configure JupyterChart to operate in offline mode where JavaScript
            dependencies are loaded from vl-convert.
            If False, configure it to operate in online mode where JavaScript dependencies
            are loaded from CDN dynamically. This is the default behavior.
        """
        pass

    def __init__(
        self,
        chart: TopLevelSpec,
        debounce_wait: int = 10,
        max_wait: bool = True,
        debug: bool = False,
        embed_options: dict | None = None,
        **kwargs: Any,
    ):
        """
        Jupyter Widget for displaying and updating Altair Charts, and retrieving selection and parameter values.

        Parameters
        ----------
        chart: Chart
            Altair Chart instance
        debounce_wait: int
             Debouncing wait time in milliseconds. Updates will be sent from the client to the kernel
             after debounce_wait milliseconds of no chart interactions.
        max_wait: bool
             If True (default), updates will be sent from the client to the kernel every debounce_wait
             milliseconds even if there are ongoing chart interactions. If False, updates will not be
             sent until chart interactions have completed.
        debug: bool
             If True, debug messages will be printed
        embed_options: dict
             Options to pass to vega-embed.
             See https://github.com/vega/vega-embed?tab=readme-ov-file#options
        """
        self.params = Params({})
        self.selections = Selections({})
        super().__init__(
            chart=chart,
            debounce_wait=debounce_wait,
            max_wait=max_wait,
            debug=debug,
            embed_options=embed_options,
            **kwargs,
        )

    @traitlets.observe("chart")
    def _on_change_chart(self, change):  # noqa: C901
        """Updates the JupyterChart's internal state when the wrapped Chart instance changes."""
        pass

    def _init_with_vegafusion(self, local_tz: str):
        pass

    @traitlets.observe("_params")
    def _on_change_params(self, change):
        pass

    @traitlets.observe("_vl_selections")
    def _on_change_selections(self, change):
        """Updates the JupyterChart's public selections traitlet in response to changes that the JavaScript logic makes to the internal _selections traitlet."""
        pass


def collect_transform_params(chart: TopLevelSpec) -> set[str]:
    """
    Collect the names of params that are defined by transforms.

    Parameters
    ----------
    chart: Chart from which to extract transform params

    Returns
    -------
    set of param names
    """
    pass
