
import sqlite3


def iter2list(func):
	def wrapper(*args, **kwargs):
		return list(func(*args, **kwargs))
	return wrapper


class Db(object):
	def __init__(self):
		self.db = None
		self.db_path = None

	def open(self, path):
		self.db_path = path
		self.db = sqlite3.connect(path)

	def close(self):
		self.db_path = None
		self.db.close()
		self.db = None

	def __enter__(self, *args):
		return self.db.__enter__(*args)

	def __exit__(self, *args):
		return self.db.__exit__(*args)

	def remove_file(self, path):
		self.db.execute('delete from tags_files where file = ?', (path,))

	def remove_tag(self, name):
		self.db.execute('delete from tags_files where tag = ?', (name,))

	def rename_tag(self, old, new):
		self.db.execute('update tags_files set tag = ? where tag = ?', (new, old))

	def rename_file(self, old, new):
		self.db.execute('update tags_files set file = ? where file = ?', (new, old))

	def tag_file(self, path, tags, start=None, end=None):
		if isinstance(tags, str):
			tags = [tags]

		for tag in tags:
			self.db.execute('insert or replace into tags_files (file, tag, start, end) values (?, ?, ?, ?)',
					(path, tag, start, end))

	def untag_file(self, path, tags):
		if isinstance(tags, str):
			tags = [tags]

		for tag in tags:
			self.db.execute('delete from tags_files where file = ? and tag = ?',
					(path, tag))

	def list_tags(self):
		for row in self.db.execute('select distinct tag from tags_files'):
			yield row[0]

	def list_files(self):
		for row in self.db.execute('select distinct file from tags_files'):
			yield row[0]

	@iter2list
	def find_tags_by_file(self, path):
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
