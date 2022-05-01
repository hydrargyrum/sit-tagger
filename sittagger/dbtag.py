# SPDX-License-Identifier: WTFPL

from logging import getLogger
from pathlib import Path
import sqlite3


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
		self.db.execute('delete from tags_files where file = ?', (path,))

	def remove_tag(self, name):
		LOGGER.info("untracking tag %r", name)
		self.db.execute('delete from tags_files where tag = ?', (name,))

	def rename_tag(self, old, new):
		LOGGER.info("renaming tag %r to %r", old, new)
		self.db.execute('update tags_files set tag = ? where tag = ?', (new, old))

	def rename_file(self, old, new):
		LOGGER.info("renaming file %r to %r", old, new)
		old = from_path(old)
		new = from_path(new)
		self.db.execute('update tags_files set file = ? where file = ?', (new, old))

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
			update tags_files
			set file = ? || substring(file, ?)
			where substring(file, 1, ?) = ?
			''',
			(new, len(old) + 1, len(old), old)
		)

	def tag_file(self, path, tags, start=None, end=None):
		LOGGER.info("tagging file: %r + %r", path, tags)

		if isinstance(tags, str):
			tags = [tags]
		path = from_path(path)

		for tag in tags:
			self.db.execute('insert or replace into tags_files (file, tag, start, end) values (?, ?, ?, ?)',
					(path, tag, start, end))

	def untag_file(self, path, tags):
		LOGGER.info("untagging file: %r - %r", path, tags)

		if isinstance(tags, str):
			tags = [tags]
		path = from_path(path)

		for tag in tags:
			self.db.execute('delete from tags_files where file = ? and tag = ?',
					(path, tag))

	untrack_file = remove_file

	def list_tags(self):
		for row in self.db.execute('select distinct tag from tags_files'):
			yield row[0]

	def list_files(self):
		for row in self.db.execute('select distinct file from tags_files'):
			yield row[0]

	@iter2list
	def find_tags_by_file(self, path):
		path = from_path(path)
		for row in self.db.execute('select distinct tag from tags_files where file = ?', (path,)):
			yield row[0]

	@iter2list
	def find_files_by_tags(self, tags):
		if isinstance(tags, str):
			tags = [tags]
		items = ','.join('?' * len(tags))
		params = list(tags) + [len(tags)]
		for row in self.db.execute('select file from tags_files where tag in (%s)'
					   ' group by file having count(*) = ?' % items, params):
			yield row[0]

	@iter2list
	def get_extras_for_file(self, path, tag):
		path = from_path(path)
		for row in self.db.execute('select start, end from tags_files where file = ? and tag = ?',
					   (path, tag)):
			yield row[0], row[1]

	def do_migrations(self):
		c = self.db.cursor()
		c.execute('create table if not exists version (version integer primary key)')

		base_version = 0
		for row in self.db.execute('select version from version'):
			base_version = row[0]

		for ver in range(base_version, max(UPGRADES) + 1):
			LOGGER.debug("database migration for version %r", ver)
			with self.db:
				for stmt in UPGRADES[ver]:
					self.db.execute(stmt)
				self.db.execute('update version set version = ?', (ver + 1,))


# key: version to reach from preceding version
# value: list of statements to execute

UPGRADES = {
	0: [
		'insert into version values(0)',
		'''
		create table if not exists tags_files (
			file, tag, start, end,
			constraint pk_tf primary key(file, tag, start, end)
		)
		''',
		'create index if not exists idx_tags on tags_files (tag)',
		'create index if not exists idx_files on tags_files (file)',
	],
}
