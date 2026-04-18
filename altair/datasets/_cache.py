from __future__ import annotations

import os
import sys
from collections import defaultdict
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, TypeVar, cast

import narwhals.stable.v1 as nw

from altair.datasets._exceptions import AltairDatasetsError

if sys.version_info >= (3, 12):
    from typing import Protocol
else:
    from typing_extensions import Protocol

if TYPE_CHECKING:
    from collections.abc import (
        Iterable,
        Iterator,
        Mapping,
        MutableMapping,
        MutableSequence,
        Sequence,
    )
    from io import IOBase
    from typing import Any, Final, TypeAlias
    from urllib.request import OpenerDirector

    from _typeshed import StrPath
    from narwhals.stable.v1.dtypes import DType
    from narwhals.stable.v1.typing import IntoExpr

    from altair.datasets._typing import Dataset, Metadata

    if sys.version_info >= (3, 12):
        from typing import Unpack
    else:
        from typing_extensions import Unpack

    if sys.version_info >= (3, 11):
        from typing import LiteralString
    else:
        from typing_extensions import LiteralString

    from altair.datasets._typing import FlFieldStr
    from altair.vegalite.v6.schema._typing import OneOrSeq

    _Dataset: TypeAlias = "Dataset | LiteralString"
    _FlSchema: TypeAlias = Mapping[str, FlFieldStr]

__all__ = ["CsvCache", "DatasetCache", "SchemaCache", "csv_cache"]


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")
_T = TypeVar("_T")

_METADATA_DIR: Final[Path] = Path(__file__).parent / "_metadata"

_DTYPE_TO_FIELD: Mapping[type[DType], FlFieldStr] = {
    nw.Int64: "integer",
    nw.Float64: "number",
    nw.Boolean: "boolean",
    nw.String: "string",
    nw.Struct: "object",
    nw.List: "array",
    nw.Date: "date",
    nw.Datetime: "datetime",
    nw.Duration: "duration",
    # nw.Time: "time" (Not Implemented, but we don't have any cases using it anyway)
}
"""
Similar to `pl.datatypes.convert.dtype_to_ffiname`_.

But using `narwhals.dtypes`_ to the string repr of ``frictionless`` `Field Types`_.

.. _pl.datatypes.convert.dtype_to_ffiname:
    https://github.com/pola-rs/polars/blob/85d078c066860e012f5e7e611558e6382b811b82/py-polars/polars/datatypes/convert.py#L139-L165
.. _Field Types:
    https://datapackage.org/standard/table-schema/#field-types
.. _narwhals.dtypes:
    https://narwhals-dev.github.io/narwhals/api-reference/dtypes/
"""

_FIELD_TO_DTYPE: Mapping[FlFieldStr, type[DType]] = {
    v: k for k, v in _DTYPE_TO_FIELD.items()
}


def _iter_metadata(df: nw.DataFrame[Any], /) -> Iterator[Metadata]:
    """
    Yield rows from ``df``, where each represents a dataset.

    See Also
    --------
    ``altair.datasets._typing.Metadata``
    """
    yield from cast("Iterator[Metadata]", df.iter_rows(named=True))


class CompressedCache(Protocol[_KT, _VT]):
    fp: Path
    _mapping: MutableMapping[_KT, _VT]

    def read(self) -> Any: ...
    def __getitem__(self, key: _KT, /) -> _VT: ...

    def __enter__(self) -> IOBase:
        import gzip

        return gzip.open(self.fp, mode="rb").__enter__()

    def __exit__(self, *args) -> None:
        return

    def get(self, key: _KT, default: _T, /) -> _VT | _T:
        return self.mapping.get(key, default)

    @property
    def mapping(self) -> MutableMapping[_KT, _VT]:
        pass


class CsvCache(CompressedCache["_Dataset", "Metadata"]):
    """
    `csv`_, `gzip`_ -based, lazy metadata lookup.

    Used as a fallback for 2 scenarios:

    1. ``url(...)`` when no optional dependencies are installed.
    2. ``(Loader|load)(...)`` when the backend is missing* ``.parquet`` support.

    Notes
    -----
    *All backends *can* support ``.parquet``, but ``pandas`` requires an optional dependency.

    .. _csv:
        https://docs.python.org/3/library/csv.html
    .. _gzip:
        https://docs.python.org/3/library/gzip.html
    """

    fp = _METADATA_DIR / "metadata.csv.gz"

    def __init__(
        self,
        *,
        tp: type[MutableMapping[_Dataset, Metadata]] = dict["_Dataset", "Metadata"],
    ) -> None:
        self._mapping: MutableMapping[_Dataset, Metadata] = tp()
        self._rotated: MutableMapping[str, MutableSequence[Any]] = defaultdict(list)

    def read(self) -> Any:
        import csv

        with self as f:
            b_lines = f.readlines()
        reader = csv.reader((bs.decode() for bs in b_lines), dialect=csv.unix_dialect)
        header = tuple(next(reader))
        return {row[0]: dict(self._convert_row(header, row)) for row in reader}

    def _convert_row(
        self, header: Iterable[str], row: Iterable[str], /
    ) -> Iterator[tuple[str, Any]]:
        map_tf = {"true": True, "false": False}
        for col, value in zip(header, row, strict=False):
            if col.startswith(("is_", "has_")):
                yield col, map_tf[value]
            elif col == "bytes":
                yield col, int(value)
            else:
                yield col, value

    @property
    def rotated(self) -> Mapping[str, Sequence[Any]]:
        """Columnar view."""
        pass

    def __getitem__(self, key: _Dataset, /) -> Metadata:
        if meta := self.get(key, None):
            return meta
        msg = f"{key!r} does not refer to a known dataset."
        raise TypeError(msg)

    def url(self, name: _Dataset, /) -> str:
        pass

    def __repr__(self) -> str:
        return f"<{type(self).__name__}: {'COLLECTED' if self._mapping else 'READY'}>"


class SchemaCache(CompressedCache["_Dataset", "_FlSchema"]):
    """
    `json`_, `gzip`_ -based, lazy schema lookup.

    - Primarily benefits ``pandas``, which needs some help identifying **temporal** columns.
    - Utilizes `data package`_ schema types.
    - All methods return falsy containers instead of exceptions

    .. _json:
        https://docs.python.org/3/library/json.html
    .. _gzip:
        https://docs.python.org/3/library/gzip.html
    .. _data package:
        https://github.com/vega/vega-datasets/pull/631
    """

    fp = _METADATA_DIR / "schemas.json.gz"

    def __init__(
        self,
        *,
        tp: type[MutableMapping[_Dataset, _FlSchema]] = dict["_Dataset", "_FlSchema"],
        implementation: nw.Implementation = nw.Implementation.UNKNOWN,
    ) -> None:
        self._mapping: MutableMapping[_Dataset, _FlSchema] = tp()
        self._implementation: nw.Implementation = implementation

    def read(self) -> Any:
        import json

        with self as f:
            return json.load(f)

    def __getitem__(self, key: _Dataset, /) -> _FlSchema:
        return self.get(key, {})

    def by_dtype(self, name: _Dataset, *dtypes: type[DType]) -> list[str]:
        """
        Return column names specfied in ``name``'s schema.

        Parameters
        ----------
        name
            Dataset name.
        *dtypes
            Optionally, only return columns matching the given data type(s).
        """
        if (match := self[name]) and dtypes:
            include = {_DTYPE_TO_FIELD[tp] for tp in dtypes}
            return [col for col, tp_str in match.items() if tp_str in include]
        else:
            return list(match)

    def is_active(self) -> bool:
        pass

    def schema(self, name: _Dataset, /) -> nw.Schema:
        it = ((col, _FIELD_TO_DTYPE[tp_str]()) for col, tp_str in self[name].items())
        return nw.Schema(it)

    def schema_kwds(self, meta: Metadata, /) -> dict[str, Any]:
        pass


class _SupportsScanMetadata(Protocol):
    _opener: ClassVar[OpenerDirector]

    def _scan_metadata(
        self, *predicates: OneOrSeq[IntoExpr], **constraints: Unpack[Metadata]
    ) -> nw.LazyFrame[Any]: ...


class DatasetCache:
    """Opt-out caching of remote dataset requests."""

    _ENV_VAR: ClassVar[LiteralString] = "ALTAIR_DATASETS_DIR"
    _XDG_CACHE: ClassVar[Path] = (
        Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "altair"
    ).resolve()

    def __init__(self, reader: _SupportsScanMetadata, /) -> None:
        self._rd: _SupportsScanMetadata = reader

    def clear(self) -> None:
        """Delete all previously cached datasets."""
        pass

    def download_all(self) -> None:
        """
        Download any missing datasets for latest version.

        Requires **30-50MB** of disk-space.
        """
        pass

    def _maybe_download(self, meta: Metadata, /) -> Path:
        pass

    def _download_one(self, url: str, fp: Path, /) -> Path:
        pass

    @property
    def path(self) -> Path:
        """
        Returns path to datasets cache.

        Defaults to (`XDG_CACHE_HOME`_)::

            "$XDG_CACHE_HOME/altair/"

        But can be configured using the environment variable::

            "$ALTAIR_DATASETS_DIR"

        You can set this for the current session via::

            from pathlib import Path
            from altair.datasets import load

            load.cache.path = Path.home() / ".altair_cache"

            load.cache.path.relative_to(Path.home()).as_posix()
            ".altair_cache"

        You can *later* disable caching via::

           load.cache.path = None

        .. _XDG_CACHE_HOME:
            https://specifications.freedesktop.org/basedir-spec/latest/#variables
        """
        pass

    @path.setter
    def path(self, source: StrPath | None, /) -> None:
        pass

    def path_meta(self, meta: Metadata, /) -> Path:
        pass

    def __iter__(self) -> Iterator[Path]:
        yield from self.path.iterdir()

    def __repr__(self) -> str:
        name = type(self).__name__
        if self.is_not_active():
            return f"{name}<UNSET>"
        else:
            return f"{name}<{self.path.as_posix()!r}>"

    def is_active(self) -> bool:
        pass

    def is_not_active(self) -> bool:
        return os.environ.get(self._ENV_VAR) == ""

    def is_empty(self) -> bool:
        """Cache is active, but no files are stored in ``self.path``."""
        return next(iter(self), None) is None

    def _ensure_active(self) -> None:
        pass


csv_cache: CsvCache


def __getattr__(name):
    if name == "csv_cache":
        global csv_cache
        csv_cache = CsvCache()
        return csv_cache

    else:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
