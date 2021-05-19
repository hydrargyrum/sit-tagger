
import os
from pathlib import Path

import vignette


_os_rename = os.rename


def _get_dev(path):
	return path.lstat().st_dev


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
