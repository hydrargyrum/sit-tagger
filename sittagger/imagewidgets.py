
from pathlib import Path

from PyQt5.QtCore import (
	QSize, Qt, pyqtSlot as Slot, pyqtSignal as Signal, QAbstractListModel, QVariant,
	QModelIndex, QMimeData,
)
from PyQt5.QtGui import QPixmap, QKeySequence, QPixmapCache, QColor
from PyQt5.QtWidgets import (
	QListView, QAction, QInputDialog, QLineEdit, QMessageBox,
)

from .fileoperationdialog import FileOperationProgressDialog
from .fm_interop import mark_for_copy, mark_for_cut, ClipQt, MIME_LIST, _parse_url
from .fsops import rename_file, FileOperation
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

	def flags(self, qidx):
		flags = super().flags(qidx)
		if not qidx.isValid():
			flags |= Qt.ItemIsDropEnabled
		return flags

	def setPath(self, path):
		self.clearEntries()

		self.path = Path(path)

		files = sorted(
			filter(lambda p: p.is_file(), self.path.iterdir()),
			key=lambda p: p.name
		)
		self.setEntries(files)

	def mimeTypes(self):
		return [MIME_LIST]

	def mimeData(self, qindexes):
		ret = QMimeData()
		ret.setData(
			MIME_LIST,
			b"\r\n".join(
				self.entries[qidx.row()].absolute().as_uri().encode("ascii")
				for qidx in qindexes
			) + b"\r\n"
		)
		return ret

	def supportedDropActions(self):
		return Qt.CopyAction | Qt.MoveAction

	def canDropMimeData(self, qmime, action, row, column, parent_qidx):
		if column > 0:
			return False

		files = self._getDroppedPaths(qmime)
		if not files:
			return False

		return super().canDropMimeData(qmime, action, row, column, parent_qidx)

	def _getDroppedPaths(self, qmime):
		urls = bytes(qmime.data(MIME_LIST)).decode("ascii").rstrip().split("\r\n")
		files = [_parse_url(url) for url in urls]
		files = [src for src in files if src.parent != self.path]
		return files

	def dropMimeData(self, qmime, action, row, column, parent_qidx):
		if not self.canDropMimeData(qmime, action, row, column, parent_qidx):
			return False

		files = self._getDroppedPaths(qmime)
		if not files:
			return False

		if action == Qt.MoveAction:
			op = "cut"
		elif action == Qt.CopyAction:
			op = "copy"
		else:
			raise NotImplementedError()

		treeop = FileOperation(self.path, files, op, db=None)
		self.fileOperation.emit(treeop)

		# this is actually fake, the operation has not finished yet
		return True

	fileOperation = Signal(FileOperation)


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
		model.fileOperation.connect(self.modelFileOperation)
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

		rename_file(current, new, db)
		# TODO update model

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

	@Slot(FileOperation)
	def modelFileOperation(self, treeop):
		treeop.db = self.window().db
		dlg = FileOperationProgressDialog(self)
		dlg.setOp(treeop)
		dlg.setModal(True)
		treeop.setParent(dlg)
		dlg.start()
