
try:
	from PyQt4.QtCore import *
	from PyQt4.QtGui import *
	Signal = pyqtSignal
	Slot = pyqtSlot
except ImportError:
	from PySide.QtCore import *
	from PySide.QtGui import *
import os


class TagEditor(QListWidget):
	def __init__(self, db):
		super(TagEditor, self).__init__()

		self.setContextMenuPolicy(Qt.ActionsContextMenu)
		act = QAction('&Create tag', self)
		act.triggered.connect(self._createTag)
		self.addAction(act)

		act = QAction('&Rename tag', self)
		act.triggered.connect(self._renameTag)
		self.addAction(act)

		self.itemChanged.connect(self._tagStateChanged)

		self.db = db

	@Slot()
	def _createTag(self):
		reply = QInputDialog.getText(self, 'Enter a tag name', 'New tag')
		tag = reply[0]
		if not reply[1]:
			return
		self._addItem(tag)
		#self.tagger.create_tag(tag)
		#self.setFiles(self.paths)

	@Slot()
	def _renameTag(self):
		item = self.currentItem()
		if not item:
			return
		old_tag = item.text()

		qreply = QInputDialog.getText(self, 'Enter a tag name', 'New tag')
		new_tag = qreply[0]
		if not qreply[1]:
			return
		self.db.rename_tag(old_tag, new_tag)
		self.setFiles(self.paths)

	def setFile(self, path):
		return self.setFiles([path])

	def _addItem(self, name):
		item = QListWidgetItem(name)
		item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
		self.addItem(item)
		return item

	def setFiles(self, paths):
		self.clear()
		self.paths = paths

		tags_per_file = dict((path, self.db.find_tags_by_file(path)) for path in paths)
		for tag in sorted(self.db.list_tags()):
			item = self._addItem(tag)
			item.setCheckState(self._state(tag, tags_per_file))

	def _state(self, tag, tags_per_file):
		if not tags_per_file:
			return Qt.Unchecked

		has_tag = any(tag in tags for tags in tags_per_file.values())
		has_untag = any(tag not in tags for tags in tags_per_file.values())
		if has_tag and has_untag:
			return Qt.PartiallyChecked
		elif has_tag:
			return Qt.Checked
		elif has_untag:
			return Qt.Unchecked
		assert False

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
				self.db.untag_file(path, [item.text()])
		else:
			for path in self.paths:
				self.db.tag_file(path, [item.text()])


class TagChooser(QListWidget):
	changed = Signal()

	def __init__(self, db):
		super(TagChooser,self).__init__()
		self.db = db

		self.itemChanged.connect(self.changed)
		for t in sorted(self.db.list_tags()):
			item = QListWidgetItem(t)
			item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
			item.setCheckState(Qt.Unchecked)
			self.addItem(item)

	def setTags(self, tags):
		for i in xrange(self.count()):
			item = self.item(i)
			if item.text() in tags:
				item.setCheckState(Qt.Checked)
			else:
				item.setCheckState(Qt.Unchecked)

	def selectedTags(self):
		tags = []
		for i in xrange(self.count()):
			item = self.item(i)
			if item.checkState() == Qt.Checked:
				tags.append(item.text())
		return tags

	def matchingFiles(self):
		tags = self.selectedTags()

		if not tags:
			return []
		res = list(self.db.find_files_by_tags(tags))
		res.sort()
		return res


class TagChooserDialog(QDialog):
	def __init__(self, db):
		QDialog.__init__(self)
		self.db = db

		self.chooser = TagChooser(db)
		self.setLayout(QVBoxLayout())
		self.layout().addWidget(self.chooser)

	def setTags(self, tags):
		self.chooser.setTags(tags)

	def selectedTags(self):
		return self.chooser.selectedTags()
