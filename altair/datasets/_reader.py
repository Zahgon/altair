"""
Backend for ``alt.datasets.Loader``.

Notes
-----
Extending would be more ergonomic if `read`, `scan`, `_constraints` were available under a single export::

    from altair.datasets import ext, reader
    import polars as pl

    impls = (
        ext.read(pl.read_parquet, ext.is_parquet),
        ext.read(pl.read_csv, ext.is_csv),
        ext.read(pl.read_json, ext.is_json),
    )
    user_reader = reader(impls)
    user_reader.dataset("airports")
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from importlib import import_module
from importlib.util import find_spec
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Literal, overload
from urllib.request import build_opener as _build_opener

from narwhals.stable import v1 as nw
from packaging.requirements import Requirement

from altair.datasets import _readimpl
from altair.datasets._cache import CsvCache, DatasetCache, SchemaCache, _iter_metadata
from altair.datasets._constraints import is_parquet
from altair.datasets._exceptions import AltairDatasetsError, module_not_found
from altair.datasets._readimpl import IntoDataFrameT, IntoLazyFrameT, is_available

if TYPE_CHECKING:
    import sys
    from collections.abc import Callable, Sequence
    from urllib.request import OpenerDirector

    import pandas as pd
    import polars as pl
    import pyarrow as pa
    from narwhals.stable.v1.typing import IntoExpr

    from altair.datasets._readimpl import BaseImpl, R, Read, Scan
    from altair.datasets._typing import Dataset, Extension, Metadata
    from altair.vegalite.v6.schema._typing import OneOrSeq

    if sys.version_info >= (3, 13):
        from typing import TypeIs, TypeVar
    else:
        from typing_extensions import TypeIs, TypeVar
    if sys.version_info >= (3, 12):
        from typing import Unpack
    else:
        from typing_extensions import Unpack
    if sys.version_info >= (3, 11):
        from typing import LiteralString
    else:
        from typing_extensions import LiteralString
    from typing import TypeAlias

    _Polars: TypeAlias = Literal["polars"]
    _Pandas: TypeAlias = Literal["pandas"]
    _PyArrow: TypeAlias = Literal["pyarrow"]
    _PandasAny: TypeAlias = Literal[_Pandas, "pandas[pyarrow]"]
    _Backend: TypeAlias = Literal[_Polars, _PandasAny, _PyArrow]
    _CuDF: TypeAlias = Literal["cudf"]
    _Dask: TypeAlias = Literal["dask"]
    _DuckDB: TypeAlias = Literal["duckdb"]
    _Ibis: TypeAlias = Literal["ibis"]
    _PySpark: TypeAlias = Literal["pyspark"]
    _NwSupport: TypeAlias = Literal[
        _Polars, _Pandas, _PyArrow, _CuDF, _Dask, _DuckDB, _Ibis, _PySpark
    ]
    _NwSupportT = TypeVar(
        "_NwSupportT",
        _Polars,
        _Pandas,
        _PyArrow,
        _CuDF,
        _Dask,
        _DuckDB,
        _Ibis,
        _PySpark,
    )
    _EagerAllowedImpl: TypeAlias = Literal[
        nw.Implementation.PANDAS,
        nw.Implementation.POLARS,
        nw.Implementation.PYARROW,
    ]
    _EagerAllowed: TypeAlias = Literal[_Pandas, _Polars, _PyArrow]

_SupportProfile: TypeAlias = Mapping[
    Literal["supported", "unsupported"], "Sequence[Dataset]"
]
"""
Dataset support varies between backends and available dependencies.

Any name listed in ``"unsupported"`` will raise an error on::

    from altair.datasets import load

    load("7zip")

Instead, they can be loaded via::

    import altair as alt
    from altair.datasets import url

    alt.Chart(url("7zip"))
"""


class Reader(Generic[IntoDataFrameT, IntoLazyFrameT]):
    """
    Modular file reader, targeting remote & local tabular resources.

    .. warning::
        Use ``reader(...)`` instead of instantiating ``Reader`` directly.
    """

    _read: Sequence[Read[IntoDataFrameT]]
    """Eager file read functions."""

    _scan: Sequence[Scan[IntoLazyFrameT]]
    """Lazy file read functions."""

    _name: str
    """
    Used in error messages, repr and matching ``@overload``(s).

    Otherwise, has no concrete meaning.
    """

    _implementation: _EagerAllowedImpl
    """
    Corresponding `narwhals implementation`_.

    .. _narwhals implementation:
        https://github.com/narwhals-dev/narwhals/blob/9b6a355530ea46c590d5a6d1d0567be59c0b5742/narwhals/utils.py#L61-L290
    """

    _opener: ClassVar[OpenerDirector] = _build_opener()
    _metadata_path: ClassVar[Path] = (
        Path(__file__).parent / "_metadata" / "metadata.parquet"
    )

    def __init__(
        self,
        read: Sequence[Read[IntoDataFrameT]],
        scan: Sequence[Scan[IntoLazyFrameT]],
        name: str,
        implementation: _EagerAllowedImpl,
    ) -> None:
        self._read = read
        self._scan = scan
        self._name = name
        self._implementation = implementation
        self._schema_cache = SchemaCache(implementation=implementation)

    def __repr__(self) -> str:
        from textwrap import indent

        PREFIX = " " * 4
        NL = "\n"
        body = f"read\n{indent(NL.join(str(el) for el in self._read), PREFIX)}"
        if self._scan:
            body += f"\nscan\n{indent(NL.join(str(el) for el in self._scan), PREFIX)}"
        return f"Reader[{self._name}] {self._implementation!r}\n{body}"

    def read_fn(self, meta: Metadata, /) -> Callable[..., IntoDataFrameT]:
        return self._solve(meta, self._read)

    def scan_fn(self, meta: Metadata | Path | str, /) -> Callable[..., IntoLazyFrameT]:
        meta = meta if isinstance(meta, Mapping) else {"suffix": _into_suffix(meta)}
        return self._solve(meta, self._scan)

    @property
    def cache(self) -> DatasetCache:
        pass

    def _handle_pyarrow_date_error(self, e: Exception, name: str) -> None:
        """Handle PyArrow date parsing errors with informative error messages, see https://github.com/apache/arrow/issues/41488."""
        pass

    def dataset(
        self,
        name: Dataset | LiteralString,
        suffix: Extension | None = None,
        /,
        **kwds: Any,
    ) -> IntoDataFrameT:
        pass

    def url(
        self, name: Dataset | LiteralString, suffix: Extension | None = None, /
    ) -> str:
        pass

    # TODO: (Multiple)
    # - Settle on a better name
    # - Add method to `Loader`
    # - Move docs to `Loader.{new name}`
    def open_markdown(self, name: Dataset, /) -> None:
        """
        Learn more about a dataset, opening `vega-datasets/datapackage.md`_ with the default browser.

        Additional info *may* include: `description`_, `schema`_, `sources`_, `licenses`_.

        .. _vega-datasets/datapackage.md:
            https://github.com/vega/vega-datasets/blob/main/datapackage.md
        .. _description:
            https://datapackage.org/standard/data-resource/#description
        .. _schema:
            https://datapackage.org/standard/table-schema/#schema
        .. _sources:
            https://datapackage.org/standard/data-package/#sources
        .. _licenses:
            https://datapackage.org/standard/data-package/#licenses
        """
        pass

    @overload
    def profile(self, *, show: Literal[False] = ...) -> _SupportProfile: ...

    @overload
    def profile(self, *, show: Literal[True]) -> None: ...

    def profile(self, *, show: bool = False) -> _SupportProfile | None:
        """
        Describe which datasets can be loaded as tabular data.

        Parameters
        ----------
        show
            Print a densely formatted repr *instead of* returning a mapping.
        """
        pass

    def _query(
        self, name: Dataset | LiteralString, suffix: Extension | None = None, /
    ) -> nw.DataFrame[IntoDataFrameT]:
        """
        Query a tabular version of `vega-datasets/datapackage.json`_.

        Applies a filter, erroring out when no results would be returned.

        .. _vega-datasets/datapackage.json:
            https://github.com/vega/vega-datasets/blob/main/datapackage.json
        """
        pass

    def _merge_kwds(self, meta: Metadata, kwds: dict[str, Any], /) -> Mapping[str, Any]:
        """
        Extend user-provided arguments with dataset & library-specfic defaults.

        .. important:: User-provided arguments have a higher precedence.
        """
        pass

    @property
    def _metadata_frame(self) -> nw.LazyFrame[IntoLazyFrameT]:
        pass

    def _scan_metadata(
        self, *predicates: OneOrSeq[IntoExpr], **constraints: Unpack[Metadata]
    ) -> nw.LazyFrame[IntoLazyFrameT]:
        pass

    def _solve(
        self, meta: Metadata, impls: Sequence[BaseImpl[R]], /
    ) -> Callable[..., R]:
        """
        Return the first function that satisfies dataset constraints.

        See Also
        --------
        ``altair.datasets._readimpl.BaseImpl.unwrap_or_skip``
        """
        items = meta.items()
        it = (some for impl in impls if (some := impl.unwrap_or_skip(items)))
        if fn_or_err := next(it, None):
            if _is_err(fn_or_err):
                raise fn_or_err.from_tabular(meta, self._name)
            return fn_or_err
        raise AltairDatasetsError.from_tabular(meta, self._name)


def _dataset_names(
    frame: nw.LazyFrame, *predicates: OneOrSeq[IntoExpr]
) -> Sequence[Dataset]:
    # NOTE: helper function for `Reader.profile`
    pass


class _NoParquetReader(Reader[IntoDataFrameT]):
    def __repr__(self) -> str:
        return f"{super().__repr__()}\ncsv_cache\n    {self.csv_cache!r}"

    @property
    def csv_cache(self) -> CsvCache:
        pass

    @property
    def _metadata_frame(self) -> nw.LazyFrame[Any]:
        pass


@overload
def reader(
    read_fns: Sequence[Read[IntoDataFrameT]],
    scan_fns: tuple[()] = ...,
    *,
    name: str | None = ...,
    implementation: nw.Implementation = ...,
) -> Reader[IntoDataFrameT]: ...


@overload
def reader(
    read_fns: Sequence[Read[IntoDataFrameT]],
    scan_fns: Sequence[Scan[IntoLazyFrameT]],
    *,
    name: str | None = ...,
    implementation: nw.Implementation = ...,
) -> Reader[IntoDataFrameT, IntoLazyFrameT]: ...


def reader(
    read_fns: Sequence[Read[IntoDataFrameT]],
    scan_fns: Sequence[Scan[IntoLazyFrameT]] = (),
    *,
    name: str | None = None,
    implementation: nw.Implementation = nw.Implementation.UNKNOWN,
) -> Reader[IntoDataFrameT, IntoLazyFrameT] | Reader[IntoDataFrameT]:
    name = name or Counter(el._inferred_package for el in read_fns).most_common(1)[0][0]
    if not _is_eager_allowed(implementation):
        implementation = _into_implementation(Requirement(name))
    if scan_fns:
        return Reader(read_fns, scan_fns, name, implementation)
    if stolen := _steal_eager_parquet(read_fns):
        return Reader(read_fns, stolen, name, implementation)
    else:
        return _NoParquetReader[IntoDataFrameT](read_fns, (), name, implementation)


def infer_backend(
    *, priority: Sequence[_Backend] = ("polars", "pandas[pyarrow]", "pandas", "pyarrow")
) -> Reader[Any, Any]:
    """
    Return the first available reader in order of `priority`.

    Notes
    -----
    - ``"polars"``: can natively load every dataset (including ``(Geo|Topo)JSON``)
    - ``"pandas[pyarrow]"``: can load *most* datasets, guarantees ``.parquet`` support
    - ``"pandas"``: supports ``.parquet``, if `fastparquet`_ is installed
    - ``"pyarrow"``: least reliable

    .. _fastparquet:
        https://github.com/dask/fastparquet
    """
    pass


@overload
def _from_backend(name: _Polars, /) -> Reader[pl.DataFrame, pl.LazyFrame]: ...
@overload
def _from_backend(name: _PandasAny, /) -> Reader[pd.DataFrame]: ...
@overload
def _from_backend(name: _PyArrow, /) -> Reader[pa.Table]: ...


# FIXME: The order this is defined in makes splitting the module complicated
# - Can't use a classmethod, since some result in a subclass used
def _from_backend(name: _Backend, /) -> Reader[Any, Any]:
    """
    Reader initialization dispatcher.

    FIXME: Works, but defining these in mixed shape functions seems off.
    """
    if not _is_backend(name):
        msg = f"Unknown backend {name!r}"
        raise TypeError(msg)
    implementation = _into_implementation(name)
    if name == "polars":
        rd, sc = _readimpl.pl_only()
        return reader(rd, sc, name=name, implementation=implementation)
    elif name == "pandas[pyarrow]":
        return reader(_readimpl.pd_pyarrow(), name=name, implementation=implementation)
    elif name == "pandas":
        return reader(_readimpl.pd_only(), name=name, implementation=implementation)
    elif name == "pyarrow":
        return reader(_readimpl.pa_any(), name=name, implementation=implementation)


def _is_backend(obj: Any) -> TypeIs[_Backend]:
    return obj in {"polars", "pandas", "pandas[pyarrow]", "pyarrow"}


def _is_err(obj: Any) -> TypeIs[type[AltairDatasetsError]]:
    return obj is AltairDatasetsError


def _into_constraints(
    name: Dataset | LiteralString, suffix: Extension | None, /
) -> Metadata:
    """Transform args into a mapping to column names."""
    pass


def _is_eager_allowed(impl: nw.Implementation, /) -> TypeIs[_EagerAllowedImpl]:
    return impl in {
        nw.Implementation.PANDAS,
        nw.Implementation.POLARS,
        nw.Implementation.PYARROW,
    }


def _into_implementation(
    backend: _NwSupport | _PandasAny | nw.Implementation | Requirement, /
) -> _EagerAllowedImpl:
    req = (
        Requirement(str(backend)) if isinstance(backend, nw.Implementation) else backend
    )
    primary = _import_guarded(req)
    impl = nw.Implementation.from_backend(primary)
    if not _is_eager_allowed(impl):
        if impl is nw.Implementation.UNKNOWN:
            msg = f"Package {primary!r} is not supported by `narwhals`."
            raise ValueError(msg)
        raise NotImplementedError(impl)
    return impl


def _into_suffix(obj: Path | str, /) -> Any:
    if isinstance(obj, Path):
        return obj.suffix
    elif isinstance(obj, str):
        return obj
    else:
        msg = f"Unexpected type {type(obj).__name__!r}"
        raise TypeError(msg)


def _steal_eager_parquet(
    read_fns: Sequence[Read[IntoDataFrameT]], /
) -> Sequence[Scan[Any]] | None:
    if convertable := next((rd for rd in read_fns if rd.include <= is_parquet), None):
        return (_readimpl.into_scan(convertable),)
    return None


@overload
def _import_guarded(req: _PandasAny, /) -> _Pandas: ...


@overload
def _import_guarded(req: _NwSupportT, /) -> _NwSupportT: ...


@overload
def _import_guarded(req: Requirement, /) -> LiteralString: ...


def _import_guarded(req: Any, /) -> LiteralString:
    requires = _requirements(req)
    for name in requires:
        if spec := find_spec(name):
            import_module(spec.name)
        else:
            raise module_not_found(str(req), requires, missing=name)
    return requires[0]


def _requirements(req: Requirement | str, /) -> tuple[Any, ...]:
    req = Requirement(req) if isinstance(req, str) else req
    return (req.name, *req.extras)
