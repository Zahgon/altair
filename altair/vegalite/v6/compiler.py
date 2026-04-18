from typing import Final

from altair.utils._importers import import_vl_convert
from altair.utils.compiler import VegaLiteCompilerRegistry

ENTRY_POINT_GROUP: Final = "altair.vegalite.v6.vegalite_compiler"
vegalite_compilers = VegaLiteCompilerRegistry(entry_point_group=ENTRY_POINT_GROUP)


def vl_convert_compiler(vegalite_spec: dict) -> dict:
    """Vega-Lite to Vega compiler that uses vl-convert."""
    pass


vegalite_compilers.register("vl-convert", vl_convert_compiler)
vegalite_compilers.enable("vl-convert")
