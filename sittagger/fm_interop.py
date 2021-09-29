
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
    def set_clipboard(mime, data):
        mimeobj = QMimeData()
        mimeobj.setData(mime, data.encode("utf-8"))
        QGuiApplication.clipboard().setMimeData(mimeobj)

    @staticmethod
    def get_clipboard(mime):
        return QGuiApplication.clipboard().mimeData().data(mime).decode("utf-8")


def mark_for_copy(files, cls):
    _mark_for(files, "copy", cls)


def mark_for_cut(files, cls):
    _mark_for(files, "cut", cls)


def _mark_for(files, op, cls):
    urls = [file.absolute().as_uri() for file in files]
    cls.set_clipboard(MIME_TEXT, "\n".join(urls))
    cls.set_clipboard(MIME_LIST, "\n".join(urls))
    cls.set_clipboard(MIME_GNOME, "\n".join([op] + urls))


def get_files_clipboard(cls, default_op=None):
    try:
        op, *urls = cls.get_clipboard(MIME_GNOME).split("\n")
    except ValueError:
        urls = cls.get_clipboard(MIME_LIST).split("\n")

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
        url = urlparse(url)
        if url.scheme != "file":
            raise Error("url %r does not have file:// scheme" % url.geturl())
        paths.append(Path(unquote(url.path)))

    return op, paths
