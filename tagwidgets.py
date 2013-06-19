
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

		self.itemChanged.connect(self._tagStateChanged)

		self.tagger = tagger

	@Slot()
	def _createTag(self):
		qreply = QInputDialog.getText(self, 'Enter a tag name', 'New tag')
		tag = str(qreply[0])
		if not qreply[1]:
			return
		self.tagger.create_tag(tag)
		self.setFile(self.path)

	def setFile(self, path):
		self.clear()

		self.path = path
		filetags = self.tagger.get_tags(self.path)
		for t in sorted(self.tagger.all_tags()):
			item = QListWidgetItem(t)
			item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
			if t in filetags:
				item.setCheckState(Qt.Checked)
			else:
				item.setCheckState(Qt.Unchecked)
			self.addItem(item)

	@Slot(QListWidgetItem)
	def _tagStateChanged(self, item):
		if item.checkState() == Qt.Unchecked:
			self.tagger.del_tags(self.path, [str(item.text())])
		else:
			self.tagger.add_tags(self.path, [str(item.text())])
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
				tags.append(str(item.text()))
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
