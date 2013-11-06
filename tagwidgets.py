
try:
	from PyQt4.QtCore import *
	from PyQt4.QtGui import *
	Signal = pyqtSignal
	Slot = pyqtSlot
except ImportError:
	from PySide.QtCore import *
	from PySide.QtGui import *
import os
import taglib


class TagEditor(QListWidget):
	def __init__(self, tagger):
		super(TagEditor, self).__init__()

		self.setContextMenuPolicy(Qt.ActionsContextMenu)
		act = QAction('&Create tag', self)
		act.triggered.connect(self._createTag)
		self.addAction(act)

		act = QAction('&Rename tag', self)
		act.triggered.connect(self._renameTag)
		self.addAction(act)

		self.itemChanged.connect(self._tagStateChanged)

		self.tagger = tagger

	@Slot()
	def _createTag(self):
		qreply = QInputDialog.getText(self, 'Enter a tag name', 'New tag')
		tag = unicode(qreply[0])
		if not qreply[1]:
			return
		self.tagger.create_tag(tag)
		self.setFiles(self.paths)

	@Slot()
	def _renameTag(self):
		item = self.currentItem()
		if not item:
			return
		old_tag = unicode(item.text())
		
		qreply = QInputDialog.getText(self, 'Enter a tag name', 'New tag')
		new_tag = unicode(qreply[0])
		if not qreply[1]:
			return
		self.tagger.rename_tag(old_tag, new_tag)
		self.setFiles(self.paths)

	def setFile(self, path):
		return self.setFiles([path])

	def setFiles(self, paths):
		self.clear()
		self.paths = paths

		tags_per_file = dict((path, self.tagger.get_tags(path)) for path in paths)
		for t in sorted(self.tagger.all_tags()):
			item = QListWidgetItem(t)
			item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
			item.setCheckState(self._state(t, tags_per_file))
			self.addItem(item)

	def _state(self, tag, tags_per_file):
		if not tags_per_file:
			return Qt.Unchecked
		
		it = iter(tags_per_file.values())
		first = (tag in it.next())
		for tags in it:
			current = (tag in tags)
			if first != current:
				return Qt.PartiallyChecked
		if first:
			return Qt.Checked
		else:
			return Qt.Unchecked

	@Slot(QListWidgetItem)
	def _tagStateChanged(self, item):
		if item.checkState() == Qt.Unchecked:
			for path in self.paths:
				self.tagger.del_tags(path, [unicode(item.text())])
		else:
			for path in self.paths:
				self.tagger.add_tags(path, [unicode(item.text())])
		self.tagger.sync()


class TagChooser(QListWidget):
	changed = Signal()

	def __init__(self, tagger):
		super(TagChooser,self).__init__()
		self.tagger = tagger
		
		self.itemChanged.connect(self.changed)
		for t in sorted(self.tagger.all_tags()):
			item = QListWidgetItem(t)
			item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
			item.setCheckState(Qt.Unchecked)
			self.addItem(item)

	def selectedTags(self):
		tags = []
		for i in xrange(self.count()):
			item = self.item(i)
			if item.checkState() == Qt.Checked:
				tags.append(unicode(item.text()))
		return tags

	def matchingFiles(self):
		tags = self.selectedTags()
		
		if not tags:
			return []
		res = set(self.tagger.get_files(tags[0]))
		for tag in tags[1:]:
			res &= set(self.tagger.get_files(tag))
		res = list(res)
		res.sort()
		return res
