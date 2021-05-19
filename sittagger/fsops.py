
import os
from pathlib import Path

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
