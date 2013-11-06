
# 2010-02-08

import shelve
import os

def tos(u):
	if isinstance(u, str):
		return u
	else:
		return u.encode('utf-8')

def froms(u):
	if isinstance(u, str):
		return u.decode('utf-8')
	else:
		return u

class Tagging(object):
	def __init__(self, dbpath):
		self.dbpath = dbpath
		self.db = shelve.open(dbpath, writeback=True)
		self.rev = {}
		for path in self.db:
			for v in self.db[path]:
				self.rev.setdefault(v, {})[path] = None
	
	def create_tag(self, tag):
		self.rev.setdefault(tag, {})
	
	def all_tags(self):
		return list(self.rev.keys())
	
	def get_tags(self, upath):
		path = tos(upath)
		if tos(path) not in self.db:
			return []
		return list(self.db[path].keys())
	
	def get_files(self, tag):
		return list(map(froms, self.rev[tag].keys()))
	
	def set_tags(self, upath, tags):
		path = tos(upath)
		if path in self.db:
			for old in self.db[path]:
				del self.rev[old][path]
		self.db[path] = {}
		for t in tags:
			self.db[path][t] = None
			self.rev.setdefault(t, {})[path] = None
	
	def add_tags(self, upath, tags):
		path = tos(upath)
		if path not in self.db:
			self.db[path] = {}
		for t in tags:
			self.db[path][t] = None
			self.rev.setdefault(t, {})[path] = None
	
	def del_tags(self, upath, tags):
		path = tos(upath)
		if path not in self.db:
			return
		for t in tags:
			try:
				del self.db[path][t]
				del self.rev[t][path]
			except KeyError:
				pass

	def rename_tag(self, old, new):
		for tags in self.db.values():
			if old in tags:
				del tags[old]
				tags[new] = None

		self.rev[new] = self.rev[old]
		del self.rev[old]

	def sync(self):
		self.db.sync()


class TaggingWithRoot(Tagging):
	def __init__(self, dbpath, rootpath):
		self.root = rootpath
		super(TaggingWithRoot, self).__init__(dbpath)
		self.super = super(TaggingWithRoot, self)
	
	def get_files(self, tag):
		return [self._AbsFromRel(relp) for relp in self.super.get_files(tag)]
	
	def get_tags(self, absp):
		return self.super.get_tags(self._relFromAbs(absp))
	
	def set_tags(self, absp, tags):
		self.super.set_tags(self._relFromAbs(absp), tags)
	
	def add_tags(self, absp, tags):
		self.super.add_tags(self._relFromAbs(absp), tags)
		
	def del_tags(self, absp, tags):
		self.super.del_tags(self._relFromAbs(absp), tags)
	
	def _relFromAbs(self, absp):
		if absp.startswith(self.root):
			t = absp[len(self.root):]
			if self.root.endswith('/'):
				return t
			else:
				return t[1:]
		return absp
		
	def _AbsFromRel(self, relp):
		return os.path.join(self.root, relp)

