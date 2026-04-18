from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

from altair import (
    Chart,
    ConcatChart,
    ConcatSpecGenericSpec,
    FacetChart,
    FacetedUnitSpec,
    FacetSpec,
    HConcatChart,
    HConcatSpecGenericSpec,
    LayerChart,
    LayerSpec,
    NonNormalizedSpec,
    TopLevelConcatSpec,
    TopLevelFacetSpec,
    TopLevelHConcatSpec,
    TopLevelLayerSpec,
    TopLevelUnitSpec,
    TopLevelVConcatSpec,
    UnitSpec,
    UnitSpecWithFrame,
    VConcatChart,
    VConcatSpecGenericSpec,
    data_transformers,
)
from altair.utils._vegafusion_data import get_inline_tables, import_vegafusion
from altair.utils.schemapi import Undefined

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import TypeAlias

    from altair.typing import ChartType
    from altair.utils.core import DataFrameLike

Scope: TypeAlias = tuple[int, ...]
FacetMapping: TypeAlias = dict[tuple[str, Scope], tuple[str, Scope]]


# For the transformed_data functionality, the chart classes in the values
# can be considered equivalent to the chart class in the key.
_chart_class_mapping = {
    Chart: (
        Chart,
        TopLevelUnitSpec,
        FacetedUnitSpec,
        UnitSpec,
        UnitSpecWithFrame,
        NonNormalizedSpec,
    ),
    LayerChart: (LayerChart, TopLevelLayerSpec, LayerSpec),
    ConcatChart: (ConcatChart, TopLevelConcatSpec, ConcatSpecGenericSpec),
    HConcatChart: (HConcatChart, TopLevelHConcatSpec, HConcatSpecGenericSpec),
    VConcatChart: (VConcatChart, TopLevelVConcatSpec, VConcatSpecGenericSpec),
    FacetChart: (FacetChart, TopLevelFacetSpec, FacetSpec),
}


@overload
def transformed_data(
    chart: Chart | FacetChart,
    row_limit: int | None = None,
    exclude: Iterable[str] | None = None,
) -> DataFrameLike | None: ...


@overload
def transformed_data(
    chart: LayerChart | HConcatChart | VConcatChart | ConcatChart,
    row_limit: int | None = None,
    exclude: Iterable[str] | None = None,
) -> list[DataFrameLike]: ...


def transformed_data(chart, row_limit=None, exclude=None):
    """
    Evaluate a Chart's transforms.

    Evaluate the data transforms associated with a Chart and return the
    transformed data as one or more DataFrames

    Parameters
    ----------
    chart : Chart, FacetChart, LayerChart, HConcatChart, VConcatChart, or ConcatChart
        Altair chart to evaluate transforms on
    row_limit : int (optional)
        Maximum number of rows to return for each DataFrame. None (default) for unlimited
    exclude : iterable of str
        Set of the names of charts to exclude

    Returns
    -------
    DataFrame or list of DataFrames or None
        If input chart is a Chart or Facet Chart, returns a DataFrame of the
        transformed data. Otherwise, returns a list of DataFrames of the
        transformed data
    """
    pass


# The equivalent classes from _chart_class_mapping should also be added
# to the type hints below for `chart` as the function would also work for them.
# However, this was not possible so far as mypy then complains about
# "Overloaded function signatures 1 and 2 overlap with incompatible return types [misc]"
# This might be due to the complex type hierarchy of the chart classes.
# See also https://github.com/python/mypy/issues/5119
# and https://github.com/python/mypy/issues/4020 which show that mypy might not have
# a very consistent behavior for overloaded functions.
# The same error appeared when trying it with Protocols for the concat and layer charts.
# This function is only used internally and so we accept this inconsistency for now.
def _assign_chart_name(chart: ChartType) -> None:
    """Assign a name to a chart if it doesn't have one."""
    pass


def _get_subcharts(chart: ChartType) -> list[Any]:
    """Get the subcharts for a composite chart."""
    pass


def name_views(
    chart: ChartType, i: int = 0, exclude: Iterable[str] | None = None
) -> list[str]:
    """
    Name unnamed chart views.

    Name unnamed charts views so that we can look them up later in
    the compiled Vega spec.

    Note: This function mutates the input chart by applying names to
    unnamed views.

    Parameters
    ----------
    chart : Chart, FacetChart, LayerChart, HConcatChart, VConcatChart, or ConcatChart
        Altair chart to apply names to
    i : int (default 0)
        Starting chart index
    exclude : iterable of str
        Names of charts to exclude

    Returns
    -------
    list of str
        List of the names of the charts and subcharts
    """
    pass


def get_group_mark_for_scope(
    vega_spec: dict[str, Any], scope: Scope
) -> dict[str, Any] | None:
    """
    Get the group mark at a particular scope.

    Parameters
    ----------
    vega_spec : dict
        Top-level Vega specification dictionary
    scope : tuple of int
        Scope tuple. If empty, the original Vega specification is returned.
        Otherwise, the nested group mark at the scope specified is returned.

    Returns
    -------
    dict or None
        Top-level Vega spec (if scope is empty)
        or group mark (if scope is non-empty)
        or None (if group mark at scope does not exist)

    Examples
    --------
    >>> spec = {
    ...     "marks": [
    ...         {"type": "group", "marks": [{"type": "symbol"}]},
    ...         {"type": "group", "marks": [{"type": "rect"}]},
    ...     ]
    ... }
    >>> get_group_mark_for_scope(spec, (1,))
    {'type': 'group', 'marks': [{'type': 'rect'}]}
    """
    pass


def get_datasets_for_scope(vega_spec: dict[str, Any], scope: Scope) -> list[str]:
    """
    Get the names of the datasets that are defined at a given scope.

    Parameters
    ----------
    vega_spec : dict
        Top-level Vega specification
    scope : tuple of int
        Scope tuple. If empty, the names of top-level datasets are returned
        Otherwise, the names of the datasets defined in the nested group mark
        at the specified scope are returned.

    Returns
    -------
    list of str
        List of the names of the datasets defined at the specified scope

    Examples
    --------
    >>> spec = {
    ...     "data": [{"name": "data1"}],
    ...     "marks": [
    ...         {
    ...             "type": "group",
    ...             "data": [{"name": "data2"}],
    ...             "marks": [{"type": "symbol"}],
    ...         },
    ...         {
    ...             "type": "group",
    ...             "data": [
    ...                 {"name": "data3"},
    ...                 {"name": "data4"},
    ...             ],
    ...             "marks": [{"type": "rect"}],
    ...         },
    ...     ],
    ... }

    >>> get_datasets_for_scope(spec, ())
    ['data1']

    >>> get_datasets_for_scope(spec, (0,))
    ['data2']

    >>> get_datasets_for_scope(spec, (1,))
    ['data3', 'data4']

    Returns empty when no group mark exists at scope
    >>> get_datasets_for_scope(spec, (1, 3))
    []
    """
    pass


def get_definition_scope_for_data_reference(
    vega_spec: dict[str, Any], data_name: str, usage_scope: Scope
) -> Scope | None:
    """
    Return the scope that a dataset is defined at, for a given usage scope.

    Parameters
    ----------
    vega_spec: dict
        Top-level Vega specification
    data_name: str
        The name of a dataset reference
    usage_scope: tuple of int
        The scope that the dataset is referenced in

    Returns
    -------
    tuple of int
        The scope where the referenced dataset is defined,
        or None if no such dataset is found

    Examples
    --------
    >>> spec = {
    ...     "data": [{"name": "data1"}],
    ...     "marks": [
    ...         {
    ...             "type": "group",
    ...             "data": [{"name": "data2"}],
    ...             "marks": [
    ...                 {
    ...                     "type": "symbol",
    ...                     "encode": {
    ...                         "update": {
    ...                             "x": {"field": "x", "data": "data1"},
    ...                             "y": {"field": "y", "data": "data2"},
    ...                         }
    ...                     },
    ...                 }
    ...             ],
    ...         }
    ...     ],
    ... }

    data1 is referenced at scope [0] and defined at scope []
    >>> get_definition_scope_for_data_reference(spec, "data1", (0,))
    ()

    data2 is referenced at scope [0] and defined at scope [0]
    >>> get_definition_scope_for_data_reference(spec, "data2", (0,))
    (0,)

    If data2 is not visible at scope [] (the top level),
    because it's defined in scope [0]
    >>> repr(get_definition_scope_for_data_reference(spec, "data2", ()))
    'None'
    """
    pass


def get_facet_mapping(group: dict[str, Any], scope: Scope = ()) -> FacetMapping:
    """
    Create mapping from facet definitions to source datasets.

    Parameters
    ----------
    group : dict
        Top-level Vega spec or nested group mark
    scope : tuple of int
        Scope of the group dictionary within a top-level Vega spec

    Returns
    -------
    dict
        Dictionary from (facet_name, facet_scope) to (dataset_name, dataset_scope)

    Examples
    --------
    >>> spec = {
    ...     "data": [{"name": "data1"}],
    ...     "marks": [
    ...         {
    ...             "type": "group",
    ...             "from": {
    ...                 "facet": {
    ...                     "name": "facet1",
    ...                     "data": "data1",
    ...                     "groupby": ["colA"],
    ...                 }
    ...             },
    ...         }
    ...     ],
    ... }
    >>> get_facet_mapping(spec)
    {('facet1', (0,)): ('data1', ())}
    """
    pass


def get_from_facet_mapping(
    scoped_dataset: tuple[str, Scope], facet_mapping: FacetMapping
) -> tuple[str, Scope]:
    """
    Apply facet mapping to a scoped dataset.

    Parameters
    ----------
    scoped_dataset : (str, tuple of int)
        A dataset name and scope tuple
    facet_mapping : dict from (str, tuple of int) to (str, tuple of int)
        The facet mapping produced by get_facet_mapping

    Returns
    -------
    (str, tuple of int)
        Dataset name and scope tuple that has been mapped as many times as possible

    Examples
    --------
    Facet mapping as produced by get_facet_mapping
    >>> facet_mapping = {
    ...     ("facet1", (0,)): ("data1", ()),
    ...     ("facet2", (0, 1)): ("facet1", (0,)),
    ... }
    >>> get_from_facet_mapping(("facet2", (0, 1)), facet_mapping)
    ('data1', ())
    """
    pass


def get_datasets_for_view_names(
    group: dict[str, Any],
    vl_chart_names: list[str],
    facet_mapping: FacetMapping,
    scope: Scope = (),
) -> dict[str, tuple[str, Scope]]:
    """
    Get the Vega datasets that correspond to the provided Altair view names.

    Parameters
    ----------
    group : dict
        Top-level Vega spec or nested group mark
    vl_chart_names : list of str
        List of the Vega-Lite
    facet_mapping : dict from (str, tuple of int) to (str, tuple of int)
        The facet mapping produced by get_facet_mapping
    scope : tuple of int
        Scope of the group dictionary within a top-level Vega spec

    Returns
    -------
    dict from str to (str, tuple of int)
        Dict from Altair view names to scoped datasets
    """
    pass
