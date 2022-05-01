# SPDX-License-Identifier: WTFPL

from logging import getLogger
import os
from pathlib import Path
import shutil
import subprocess
from threading import Event

from PyQt5.QtCore import QThread, pyqtSignal as Signal, pyqtSlot as Slot
import vignette


LOGGER = getLogger(__name__)


_os_rename = os.rename


def _call_log_exc(func, *args, **kwargs):
	try:
		return func(*args, **kwargs)
	except Exception as exc:
		LOGGER.info("failed calling %s: %s", func, exc)


def _get_dev(path):
	return path.lstat().st_dev


def _rename_with_thumb(src, dst):
	if src.startswith(vignette._thumb_path_prefix()):
		return _os_rename(src, dst)

	tsrc = vignette.try_get_thumbnail(src, 'large')
	if not tsrc:
		return _os_rename(src, dst)

	ret = _os_rename(src, dst)

	vignette.put_thumbnail(dst, 'large', tsrc)

	return ret


THUMB_SIZES = ("normal", "large")


def _pre_copy_thumb(src):
	if isinstance(src, Path):
		src = str(src)

	if src.startswith(vignette._thumb_path_prefix()):
		return {}

	thumbs = {}
	for sz in THUMB_SIZES:
		tsrc = vignette.try_get_thumbnail(src, sz)
		if tsrc:
			thumbs[sz] = tsrc

	return thumbs


def _post_copy_thumb(thumbs, dst):
	if thumbs is None:
		return

	if isinstance(dst, Path):
		dst = str(dst)

	for sz, tsrc in thumbs.items():
		LOGGER.debug("copying old thumb of %r: %r", dst, tsrc)
		vignette.put_thumbnail(dst, sz, tsrc)


def rename_file(old, new, db):
	old = Path(old).absolute()
	new = Path(new).absolute()

	if _get_dev(old) != _get_dev(new.parent):
		raise NotImplementedError()

	thumbs = _call_log_exc(_pre_copy_thumb, old)

	_os_rename(str(old), str(new))
	with db:
		db.rename_file(str(old), str(new))

	_call_log_exc(_post_copy_thumb, thumbs, new)


def _scan_thumbs(path):
	ret = {}
	for sub in path.rglob('*'):
		if not sub.is_file():
			continue

		thumb = vignette.try_get_thumbnail(str(sub), 'large')
		if thumb:
			ret[sub.lstat().st_ino] = thumb

	return ret


def _restore_thumbs(path, inodes):
	for sub in path.rglob('*'):
		thumb = inodes.get(sub.lstat().st_ino)
		if thumb:
			vignette.put_thumbnail(str(sub), 'large', thumb)


def rename_folder(old, new, db):
	old = Path(old).absolute()
	new = Path(new).absolute()

	if _get_dev(old) != _get_dev(new.parent):
		raise NotImplementedError()

	inodes = _scan_thumbs(old)
	_os_rename(old, new)
	_restore_thumbs(new, inodes)
	with db:
		db.rename_folder(str(old), str(new))


class Cancelled(Exception):
	pass


class FileOperation(QThread):
	"""Long copy/cut files/trees operation

	Emits progress information for current file, not the whole tree.
	"""

	processing = Signal(str, int, int)

	def __init__(self, dest, sources, op, db):
		super().__init__()
		self.dest = dest
		self.sources = sources
		self.op = op
		self.db = db
		self.is_cancelled = Event()
		assert op in ("cut", "copy")
		assert self.dest.is_dir()

	def _copytree(self, src, dst):
		shutil.copytree(src, dst, copy=self._copy)

	def _movetree(self, src, dstdir):
		is_dir = src.is_dir()
		xdev = _get_dev(src) != _get_dev(dstdir)

		thumbs_inodes = None
		thumbs = None
		if not xdev:
			if is_dir:
				thumbs_inodes = _scan_thumbs(src)
			else:
				thumbs = _call_log_exc(_pre_copy_thumb, src)

		shutil.move(src, dstdir, copy_function=self._copy_for_move)

		if not xdev:
			dstentry = dstdir.joinpath(src.name)

			if is_dir:
				with self.db:
					self.db.rename_folder(src, dstentry)

				_restore_thumbs(dstentry, thumbs_inodes)
			else:
				with self.db:
					self.db.rename_file(src, dstentry)

				_call_log_exc(_post_copy_thumb, thumbs, dstentry)

	def _copy_for_move(self, src, dst):
		self._copy(src, dst)
		with self.db:
			self.db.rename_file(src, dst)

	def _copy(self, src, dst):
		if self.is_cancelled.is_set():
			raise Cancelled()

		thumbs = _call_log_exc(_pre_copy_thumb, src)

		total = os.path.getsize(src)
		current = 0
		self.processing.emit(str(src), 0, total)
		length = shutil.COPY_BUFSIZE

		with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
			fsrc_read = fsrc.read
			fdst_write = fdst.write

			while True:
				if self.is_cancelled.is_set():
					raise Cancelled()

				buf = fsrc_read(length)
				if not buf:
					break
				fdst_write(buf)
				current += len(buf)

				self.processing.emit(str(src), current, total)

		shutil.copystat(src, dst)
		_call_log_exc(_post_copy_thumb, thumbs, dst)

	def run(self):
		names = {src.name for src in self.sources}
		if len(self.sources) != len(names):
			# TODO
			return

		try:
			getattr(self, "_run_%s" % self.op)()
		except Cancelled:
			pass

	def _run_copy(self):
		for src in self.sources:
			if self.is_cancelled.is_set():
				break

			if src.is_file():
				dest = self.dest.joinpath(src.name)
				self._copy(src, dest)
			elif src.is_dir():
				self._copytree(src, self.dest)

	def _run_cut(self):
		for src in self.sources:
			if self.is_cancelled.is_set():
				break

			self._movetree(src, self.dest)

	@Slot()
	def cancel(self):
		self.is_cancelled.set()


def can_trash():
	return bool(shutil.which("trash-put"))


def trash_items(paths):
	LOGGER.info("sending %s to trash", paths)
	subprocess.run(["trash-put", "-v", *map(str, paths)])
