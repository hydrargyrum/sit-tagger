# SPDX-License-Identifier: WTFPL

"""File managers inter-operability for copy/pasting files
"""

from urllib.parse import urlparse, unquote
from pathlib import Path

from PyQt5.QtGui import QGuiApplication
from PyQt5.QtCore import QMimeData


MIME_GNOME = "x-special/gnome-copied-files"
MIME_LIST = "text/uri-list"
MIME_TEXT = "text/plain"


class Error(Exception):
    pass


class ClipQt:
    @staticmethod
    def set_clipboard(mimes):
        qmime = QMimeData()
        for mime, data in mimes.items():
            qmime.setData(mime, data.encode("utf-8"))
        QGuiApplication.clipboard().setMimeData(qmime)

    @staticmethod
    def get_clipboard(mime):
        return bytes(QGuiApplication.clipboard().mimeData().data(mime)).decode("utf-8")


def mark_for_copy(files, cls):
    _mark_for(files, "copy", cls)


def mark_for_cut(files, cls):
    _mark_for(files, "cut", cls)


def _mark_for(files, op, cls):
    urls = [file.absolute().as_uri() for file in files]
    cls.set_clipboard({
        MIME_TEXT: "\n".join(urls),
        MIME_LIST: "\r\n".join(urls) + "\r\n",  # requires a trailing newline
        MIME_GNOME: "\n".join([op] + urls),
    })


def _parse_url(url):
    url = urlparse(url)
    if url.scheme != "file":
        raise Error("url %r does not have file:// scheme" % url.geturl())
    return Path(unquote(url.path))


def get_files_clipboard(cls, default_op=None):
    try:
        op, *urls = cls.get_clipboard(MIME_GNOME).split("\n")
    except ValueError:
        urls = cls.get_clipboard(MIME_LIST).strip().split("\r\n")

        if len(urls) == 1 and not urls[0]:
            # "".split("\n") == [""]
            raise Error("no URLs")

        op = default_op
    else:
        if not urls:
            raise Error("no URLs")

        if op not in {"copy", "cut"}:
            raise Error("unknow operation %r" % op)

    paths = []
    for url in urls:
        paths.append(_parse_url(url))

    return op, paths
