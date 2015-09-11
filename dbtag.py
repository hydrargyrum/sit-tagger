
import sqlite3

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

	def create_tables(self):
		c = self.db.cursor()
		c.execute('create table if not exists tags_files (file, tag, extra,'
		          ' constraint pk_tf primary key(file, tag))')
		c.execute('create index if not exists idx_tags on tags_files (tag)')
		c.execute('create index if not exists idx_files on tags_files (file)')

	def remove_file(self, path):
		with self.db:
			self.db.execute('delete from tags_files where file = ?', path)

	def remove_tag(self, name):
		with self.db:
			self.db.execute('delete from tags_files where tag = ?', name)

	def rename_tag(self, old, new):
		with self.db:
			self.db.execute('update tags_files set tag = ? where tag = ?', (new, old))

	def tag_file(self, path, tags, extra=None):
		if isinstance(tags, (str, unicode)):
			tags = [tags]

		data = [(path, tag, extra) for tag in tags]
		with self.db:
			self.db.executemany('insert or replace into tags_files (file, tag, extra) values (?, ?, ?)',
			                    data)

	def untag_file(self, path, tags):
		if isinstance(tags, (str, unicode)):
			tags = [tags]

		with self.db:
			for tag in tags:
				self.db.execute('delete from tags_files where file = ? and tag = ?',
				                (path, tag))

	def list_tags(self):
		with self.db:
			for row in self.db.execute('select distinct tag from tags_files'):
				yield row[0]

	def find_tags_by_file(self, path):
		with self.db:
			for row in self.db.execute('select tag from tags_files where file = ?', path):
				yield row[0]

	def find_files_by_tags(self, tags):
		if isinstance(tags, (str, unicode)):
			tags = [tags]
		items = ','.join('?' * len(tags))
		params = list(tags) + [len(tags)]
		with self.db:
			for row in self.db.execute('select file, extra from tags_files where tag in (%s)'
			                           ' group by file having count(*) = ?' % items, params):
				yield row[0]
