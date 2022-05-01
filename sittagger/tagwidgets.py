# SPDX-License-Identifier: WTFPL

from PyQt5.QtCore import Qt, pyqtSignal as Signal, pyqtSlot as Slot, QSortFilterProxyModel
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QInputDialog, QVBoxLayout, QAction, QDialog, QListView, QLineEdit


class TagFilter(QLineEdit):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.textChanged.connect(self.updateFilter)
		self.widget = None

	def setWidget(self, widget):
		self.widget = widget

	@Slot()
	def updateFilter(self):
		if not self.widget:
			return

		self.widget.proxy.setFilterFixedString(self.text())


class TagEditor(QListView):
	changedTags = Signal()

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.db = None
		self.paths = []

		self.data = QStandardItemModel(self)
		self.proxy = QSortFilterProxyModel(self)
		self.proxy.setSourceModel(self.data)
		self.setModel(self.proxy)

		self.setContextMenuPolicy(Qt.ActionsContextMenu)
		act = QAction('&Create tag', self)
		act.triggered.connect(self._createTag)
		self.addAction(act)

		act = QAction('&Rename tag', self)
		act.triggered.connect(self._renameTag)
		self.addAction(act)

		self.data.itemChanged.connect(self._tagStateChanged)

	def setDb(self, db):
		self.db = db

	@Slot()
	def _createTag(self):
		tag, ok = QInputDialog.getText(self, 'Enter a tag name', 'New tag')
		if not ok:
			return
		self.data.appendRow(self._createItem(tag))
		self.changedTags.emit()

	@Slot()
	def _renameTag(self):
		item = self.currentItem()
		if not item:
			return
		old_tag = item.text()

		new_tag, ok = QInputDialog.getText(self, 'Enter a tag name', 'New tag')
		if not ok:
			return
		with self.db:
			self.db.rename_tag(old_tag, new_tag)
		self.setFiles(self.paths)
		self.changedTags.emit()

	def setFile(self, path):
		return self.setFiles([path])

	def _createItem(self, name):
		item = QStandardItem(name)
		item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
		item.setCheckState(Qt.Unchecked)
		return item

	def setFiles(self, paths):
		self.data.clear()
		self.paths = paths

		tags_per_file = {path: self.db.find_tags_by_file(path) for path in paths}
		for tag in sorted(self.db.list_tags()):
			item = self._createItem(tag)
			item.setCheckState(self._state(tag, tags_per_file))
			self.data.appendRow(item)

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

	@Slot('QStandardItem*')
	def _tagStateChanged(self, item):
		with self.db:
			if item.checkState() == Qt.Unchecked:
				for path in self.paths:
					self.db.untag_file(path, [item.text()])
			else:
				for path in self.paths:
					self.db.tag_file(path, [item.text()])

	@Slot()
	def refreshTags(self):
		self.setFiles(self.paths)


class TagChooser(QListView):
	changed = Signal()

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.db = None

		self.filter = ''

		self.data = QStandardItemModel(self)
		self.proxy = QSortFilterProxyModel(self)
		self.proxy.setSourceModel(self.data)
		self.setModel(self.proxy)

		self.data.itemChanged.connect(self.changed)

		self.setContextMenuPolicy(Qt.ActionsContextMenu)
		act = QAction('&Refresh tags', self)
		act.triggered.connect(self.refreshTags)
		self.addAction(act)

	def setDb(self, db):
		self.db = db

		for t in sorted(self.db.list_tags()):
			item = QStandardItem(t)
			item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
			item.setCheckState(Qt.Unchecked)
			self.data.appendRow(item)

	def setTags(self, tags):
		for i in range(self.data.rowCount()):
			item = self.data.item(i)
			if item.text() in tags:
				item.setCheckState(Qt.Checked)
			else:
				item.setCheckState(Qt.Unchecked)

	def selectedTags(self):
		tags = []
		for i in range(self.data.rowCount()):
			item = self.data.item(i)
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

	@Slot()
	def refreshTags(self):
		selected = self.selectedTags()
		self.setDb(self.db)
		self.setTags(selected)


class TagChooserDialog(QDialog):
	def __init__(self, db, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.db = db

		self.chooser = TagChooser(db, parent=self)
		self.setLayout(QVBoxLayout())
		self.layout().addWidget(self.chooser)

	def setTags(self, tags):
		self.chooser.setTags(tags)

	def selectedTags(self):
		return self.chooser.selectedTags()
