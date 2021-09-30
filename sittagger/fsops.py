
import os
from pathlib import Path
import shutil
from threading import Event

from PyQt5.QtCore import QThread, pyqtSignal as Signal, pyqtSlot as Slot
import vignette


_os_rename = os.rename


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


def move_file(old, new, db):
	old = Path(old).absolute()
	new = Path(new).absolute()

	if _get_dev(old) != _get_dev(new.parent):
		raise NotImplementedError()

	_rename_with_thumb(str(old), str(new))
	with db:
		db.rename_file(str(old), str(new))


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


def move_folder(old, new, db):
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
	processing = Signal(str, int, int)

	def __init__(self, dest, sources, op):
		super().__init__()
		self.dest = dest
		self.sources = sources
		self.op = op
		self.is_cancelled = Event()
		assert op in ("cut", "copy")

	def copytree(self, src, dst):
		shutil.copytree(src, dst, copy=self._copy)

	def movetree(self, src, dst):
		shutil.move(src, dst, copy_function=self._copy)

	def _copy(self, src, dst):
		if self.is_cancelled.is_set():
			raise Cancelled()

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

	def run(self):
		names = {src.name for src in self.sources}
		if len(self.sources) != len(names):
			# TODO
			return

		try:
			getattr(self, "run_%s" % self.op)()
		except Cancelled:
			pass

	def run_copy(self):
		for src in self.sources:
			if self.is_cancelled.is_set():
				break

			if src.is_file():
				dest = self.dest.joinpath(src.name)
				self._copy(src, dest)
			elif src.is_dir():
				self.copytree(src, self.dest)

	def run_cut(self):
		for src in self.sources:
			if self.is_cancelled.is_set():
				break

			self.movetree(src, self.dest)

	@Slot()
	def cancel(self):
		self.is_cancelled.set()
