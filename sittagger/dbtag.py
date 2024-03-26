# SPDX-License-Identifier: WTFPL

from logging import getLogger
from pathlib import Path
import sqlite3

from . import captiontools


LOGGER = getLogger(__name__)


def iter2list(func):
	def wrapper(*args, **kwargs):
		return list(func(*args, **kwargs))
	return wrapper


def from_path(path):
	if isinstance(path, Path):
		return str(path.absolute())
	return path


class Db:
	def __init__(self, multithread=False):
		self.db = None
		self.db_path = None
		self.multithread = multithread

	def open(self, path):
		self.db_path = path
		self.db = sqlite3.connect(path, check_same_thread=not self.multithread)

	def close(self):
		self.db_path = None
		self.db.close()
		self.db = None

	def __enter__(self, *args):
		return self.db.__enter__(*args)

	def __exit__(self, *args):
		return self.db.__exit__(*args)

	def remove_file(self, path):
		LOGGER.info("untracking file %r", path)
		path = from_path(path)
		self.db.execute('DELETE FROM tags_files WHERE file = ?', (path,))
		self.db.execute('DELETE FROM caption WHERE file = ?', (path,))

	def remove_tag(self, name):
		LOGGER.info("untracking tag %r", name)
		self.db.execute('DELETE FROM tags_files WHERE tag = ?', (name,))

	def rename_tag(self, old, new):
		LOGGER.info("renaming tag %r to %r", old, new)

		for (file,) in self.db.execute(
				'SELECT DISTINCT file FROM tags_files JOIN caption USING (file) '
				+ 'WHERE tag = ? AND caption IS NOT NULL', (old,)):
			# the file has the old tag and has a caption: the old tag is in the caption
			caption = self.get_caption(file)
			caption = captiontools.rename_tag_in_caption(caption, old, new)
			self._set_caption_base(file, caption)

		self.db.execute('UPDATE tags_files SET tag = ? WHERE tag = ?', (new, old))

	def rename_file(self, old, new):
		LOGGER.info("renaming file %r to %r", old, new)
		old = from_path(old)
		new = from_path(new)
		self.db.execute('UPDATE caption SET file = ? WHERE file = ?', (new, old))
		self.db.execute('UPDATE tags_files SET file = ? WHERE file = ?', (new, old))

	def rename_folder(self, old, new):
		LOGGER.info("renaming folder %r to %r", old, new)
		old = from_path(old)
		new = from_path(new)

		# force slashes to avoid matching /aaabbb with /aaa pattern but only /aaa/bbb
		old = old + '/'
		new = new + '/'

		# don't use LIKE in WHERE because old could contain '%' or metacharacters
		self.db.execute(
			'''
			UPDATE tags_files
			SET file = ? || SUBSTRING(file, ?)
			WHERE SUBSTRING(file, 1, ?) = ?
			''',
			(new, len(old) + 1, len(old), old)
		)
		self.db.execute(
			'''
			UPDATE caption
			SET file = ? || SUBSTRING(file, ?)
			WHERE SUBSTRING(file, 1, ?) = ?
			''',
			(new, len(old) + 1, len(old), old)
		)

	def tag_file(self, path, tags, start=None, end=None):
		self._tag_file_base(path, tags, start, end)
		self._update_caption(path)

	def _tag_file_base(self, path, tags, start=None, end=None):
		LOGGER.info("tagging file: %r + %r", path, tags)

		if isinstance(tags, str):
			tags = [tags]
		path = from_path(path)

		for tag in tags:
			self.db.execute('INSERT OR REPLACE INTO tags_files (file, tag, start, end) VALUES (?, ?, ?, ?)',
					(path, tag, start, end))

		self._update_caption(path)

	def untag_file(self, path, tags):
		self._untag_file_base(path, tags)
		self._update_caption(path)

	def _untag_file_base(self, path, tags):
		LOGGER.info("untagging file: %r - %r", path, tags)

		if isinstance(tags, str):
			tags = [tags]
		path = from_path(path)

		for tag in tags:
			self.db.execute('DELETE FROM tags_files WHERE file = ? AND tag = ?',
					(path, tag))

	untrack_file = remove_file

	def list_tags(self):
		for row in self.db.execute('SELECT DISTINCT tag FROM tags_files'):
			yield row[0]

	def list_files(self):
		for row in self.db.execute('SELECT DISTINCT file FROM tags_files'):
			yield row[0]

	@iter2list
	def find_tags_by_file(self, path):
		path = from_path(path)
		for row in self.db.execute('SELECT DISTINCT tag FROM tags_files WHERE file = ?', (path,)):
			yield row[0]

	@iter2list
	def find_files_by_tags(self, tags):
		if isinstance(tags, str):
			tags = [tags]
		items = ','.join('?' * len(tags))
		params = list(tags) + [len(tags)]
		for row in self.db.execute('SELECT file FROM tags_files WHERE tag IN (%s)'
					   ' GROUP BY file HAVING COUNT(DISTINCT tag) = ?' % items, params):
			yield row[0]

	@iter2list
	def get_extras_for_file(self, path, tag):
		path = from_path(path)
		for row in self.db.execute('SELECT start, end FROM tags_files WHERE file = ? AND tag = ?',
					   (path, tag)):
			yield row[0], row[1]

	def get_caption(self, path):
		path = from_path(path)
		for row in self.db.execute("SELECT caption FROM caption WHERE file = ?", (path,)):
			return row[0]
		return None

	def _update_caption(self, path):
		caption = self.get_caption(path)
		if not caption:
			return

		caption = captiontools.tags_to_caption(self.find_tags_by_file(path), caption)
		self._set_caption_base(path, caption)

	def set_caption(self, path, caption):
		path = from_path(path)
		if not caption or not caption.strip():
			# when deleting caption, don't delete tags
			self._set_caption_base(path, None)
			return

		target_tags = set(captiontools.extract_tags_from_caption(caption))
		current_tags = set(self.find_tags_by_file(path))

		self._set_caption_base(path, caption)
		self._untag_file_base(path, current_tags - target_tags)
		self._tag_file_base(path, target_tags - current_tags)

	def _set_caption_base(self, path, caption):
		self.db.execute(
			"INSERT OR REPLACE INTO caption (file, caption) VALUES (?, ?)",
			(path, caption)
		)

	def do_migrations(self):
		c = self.db.cursor()
		c.execute('CREATE TABLE IF NOT EXISTS version (version INTEGER PRIMARY KEY)')

		base_version = 0
		for row in self.db.execute('SELECT version FROM version'):
			base_version = row[0]

		for ver in range(base_version, max(UPGRADES) + 1):
			LOGGER.debug("database migration for version %r", ver)
			with self.db:
				for stmt in UPGRADES[ver]:
					self.db.execute(stmt)
				self.db.execute('UPDATE version SET version = ?', (ver + 1,))


# key: version to reach from preceding version
# value: list of statements to execute

UPGRADES = {
	0: [
		'INSERT INTO version VALUES(0)',
		'''
		CREATE TABLE IF NOT EXISTS tags_files (
			file, tag, start, end,
			CONSTRAINT pk_tf PRIMARY KEY(file, tag, start, end)
		)
		''',
		'CREATE INDEX IF NOT EXISTS idx_tags ON tags_files (tag)',
		'CREATE INDEX IF NOT EXISTS idx_files ON tags_files (file)',
	],
	1: [
		"CREATE TABLE IF NOT EXISTS caption (file TEXT PRIMARY KEY, caption TEXT)",
	],
}
