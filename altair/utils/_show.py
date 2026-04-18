from __future__ import annotations

import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def open_html_in_browser(
    html: str | bytes,
    using: str | Iterable[str] | None = None,
    port: int | None = None,
) -> None:
    """
    Display an html document in a web browser without creating a temp file.

    Instantiates a simple http server and uses the webbrowser module to
    open the server's URL

    Parameters
    ----------
    html: str
        HTML string to display
    using: str or iterable of str
        Name of the web browser to open (e.g. "chrome", "firefox", etc.).
        If an iterable, choose the first browser available on the system.
        If none, choose the system default browser.
    port: int
        Port to use. Defaults to a random port
    """
    pass
