
import os
from pathlib import Path

from PyQt5.QtCore import (
	QSize, Qt, pyqtSlot as Slot, pyqtSignal as Signal, QAbstractListModel, QVariant,
	QModelIndex,
)
from PyQt5.QtGui import QIcon, QPixmap, QKeySequence, QPixmapCache, QColor
from PyQt5.QtWidgets import (
	QListWidget, QListWidgetItem, QListView,
	QAction, QInputDialog, QLineEdit,
	QMessageBox,
)

from .fm_interop import mark_for_copy, mark_for_cut, ClipQt
from .fsops import move_file
from . import thumbnailmaker


class AbstractFilesModel(QAbstractListModel):
	emptypix = None

	def __init__(self, parent=None):
		super().__init__(parent)

		self.entries = []
		self.thumbs = {}

		thumbnailmaker.maker.done.connect(self.doneThumbnail)
		if self.emptypix is None:
			AbstractFilesModel.emptypix = QPixmap(QSize(256, 256))
			AbstractFilesModel.emptypix.fill(QColor("gray"))

	def rowCount(self, qidx):
		return len(self.entries)

	def data(self, qidx, role):
		path = self.entries[qidx.row()]

		if role == Qt.DisplayRole:
			return QVariant(path.name)
		elif role == Qt.DecorationRole:
			try:
				tpath = self.thumbs[str(path)]
			except KeyError:
				return QVariant(self.emptypix)
			return QVariant(self._pixmap(tpath))
		elif role == Qt.UserRole:
			return QVariant(str(path))
		else:
			return QVariant()

	def flags(self, qidx):
		flags = super().flags(qidx)
		if qidx.isValid():
			flags |= (
				Qt.ItemIsSelectable
				| Qt.ItemIsEnabled
				| Qt.ItemIsDragEnabled
				| Qt.ItemNeverHasChildren
			)
		return flags

	def _pixmap(self, path):
		path = str(path)
		pix = QPixmapCache.find(path)
		if not pix or not pix.isNull():
			pix = QPixmap(path)
			QPixmapCache.insert(path, pix)

		return pix

	def clearEntries(self):
		for path in self.entries:
			thumbnailmaker.maker.cancelTask(str(path))

		self.beginRemoveRows(QModelIndex(), 0, len(self.entries) - 1)
		self.entries = []
		self.thumbs = {}
		self.endRemoveRows()

	def setEntries(self, files):
		self.beginInsertRows(QModelIndex(), 0, len(files) - 1)
		self.entries = files
		self.thumbs = {}
		self.endInsertRows()

		for path in self.entries:
			thumbnailmaker.maker.addTask(str(path))

	@Slot(str, str)
	def doneThumbnail(self, origpath, thumbpath):
		try:
			idx = self.entries.index(Path(origpath))
		except ValueError:
			return

		self.thumbs[origpath] = thumbpath

		qidx = self.index(idx)
		self.dataChanged.emit(qidx, qidx, [Qt.DecorationRole])


class ThumbDirModel(AbstractFilesModel):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.path = None

	def setPath(self, path):
		self.clearEntries()

		self.path = Path(path)

		files = sorted(
			filter(lambda p: p.is_file(), self.path.iterdir()),
			key=lambda p: p.name
		)
		self.setEntries(files)


class ThumbTagModel(AbstractFilesModel):
	def __init__(self, db, parent=None):
		super().__init__(parent)
		self.db = db
		self.tags = None

	def setTags(self, tags):
		self.clearEntries()
		self.tags = tags

		files = sorted(self.db.find_files_by_tags(tags), key=lambda p: p.name)
		self.setEntries(files)


class ImageList(QListView):
	pasteRequested = Signal()

	def __init__(self, *args, **kwargs):
		super(ImageList, self).__init__(*args, **kwargs)

		action = QAction(parent=self)
		action.setShortcut(QKeySequence("F2"))
		action.setShortcutContext(Qt.WidgetShortcut)
		action.triggered.connect(self.popRenameSelected)
		self.addAction(action)

		action = QAction(parent=self)
		action.setShortcut(QKeySequence(QKeySequence.Copy))
		action.setShortcutContext(Qt.WidgetShortcut)
		action.triggered.connect(self.markForCopy)
		self.addAction(action)

		action = QAction(parent=self)
		action.setShortcut(QKeySequence(QKeySequence.Cut))
		action.setShortcutContext(Qt.WidgetShortcut)
		action.triggered.connect(self.markForCut)
		self.addAction(action)

		action = QAction(parent=self)
		action.setShortcut(QKeySequence(QKeySequence.Paste))
		action.setShortcutContext(Qt.WidgetShortcut)
		action.triggered.connect(self.pasteRequested)
		self.addAction(action)

	def selectionChanged(self, new, old):
		self.itemSelectionChanged.emit()

	itemSelectionChanged = Signal()

	def showEvent(self, ev):
		super().showEvent(ev)
		self.verticalScrollBar().setSingleStep(32)

	def browseDir(self, path):
		model = ThumbDirModel()
		model.setPath(path)
		self.setModel(model)

	def browseTags(self, tags):
		model = ThumbTagModel(self.window().db)
		model.setTags(tags)
		self.setModel(model)

	def getFiles(self):
		return list(map(str, self.model().entries))  # TODO this is too raw

	def getCurrentFile(self):
		return str(self.model().entries[self.selectionModel().currentIndex().row()])

	@Slot()
	def popRenameSelected(self):
		raise NotImplementedError()

		db = self.window().db

		selected = self.selectedPaths()
		if len(selected) != 1:
			# cannot rename 0 or multiple files
			return

		current = selected[0]

		new, ok = QInputDialog.getText(
			self,
			self.tr("Rename file"),
			self.tr("New name for file"),
			QLineEdit.Normal,
			current.name
		)

		if not ok or not new or new == current.name:
			return
		if "/" in new:
			QMessageBox.critical(
				self,
				self.tr("Error"),
				self.tr("New name %r cannot contain '/'") % new,
			)
			return

		new = current.with_name(new)

		move_file(current, new, db)

		# TODO reimplement with new models
		item = self.items.pop(str(current))
		item._updatePath(str(new))
		self.items[str(new)] = item

	def selectedPaths(self):
		return [Path(spath).absolute() for spath in self.selectedFiles()]

	def selectedFiles(self):
		return [
			qidx.data(Qt.UserRole)
			for qidx in self.selectedIndexes()
		]

	@Slot()
	def markForCopy(self):
		paths = self.selectedPaths()
		if not paths:
			return
		mark_for_copy(paths, ClipQt)

	@Slot()
	def markForCut(self):
		paths = self.selectedPaths()
		if not paths:
			return
		mark_for_cut(paths, ClipQt)
