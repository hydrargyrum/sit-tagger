# SPDX-License-Identifier: WTFPL

from pathlib import Path

from PyQt6.QtCore import QDir, pyqtSlot as Slot, Qt, pyqtSignal as Signal, QMimeData, QCoreApplication
from PyQt6.QtGui import QKeySequence, QAction, QFileSystemModel
from PyQt6.QtWidgets import (
	QTreeView, QInputDialog, QLineEdit,
	QMessageBox, QHeaderView,
)

from .fileoperationdialog import FileOperationProgressDialog
from .fsops import rename_folder, FileOperation, trash_items, can_trash
from .fm_interop import ClipQt, get_files_clipboard, MIME_LIST, _parse_url


class FSModelWithDND(QFileSystemModel):
	def flags(self, qidx):
		flags = super().flags(qidx)
		if qidx.isValid():
			flags |= Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
		return flags

	def mimeTypes(self):
		return [MIME_LIST]

	def mimeData(self, qindexes):
		ret = QMimeData()
		ret.setData(
			MIME_LIST,
			b"\r\n".join(
				Path(self.filePath(qidx)).absolute().as_uri().encode("ascii")
				for qidx in qindexes
			) + b"\r\n"
		)
		return ret

	def supportedDropActions(self):
		return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction

	def canDropMimeData(self, qmime, action, row, column, parent_qidx):
		if column > 0 or row > -1:
			# row is -1 when pointing to a qmodelindex
			# row is >= 0 when pointing between rows
			return False

		files = self._getDroppedPaths(qmime, parent_qidx)
		if not files:
			return False

		return super().canDropMimeData(qmime, action, row, column, parent_qidx)

	def _getDroppedPaths(self, qmime, parent_qidx):
		parent_path = Path(self.filePath(parent_qidx))

		urls = bytes(qmime.data(MIME_LIST)).decode("ascii").rstrip().split("\r\n")
		files = [_parse_url(url) for url in urls]
		files = [src for src in files if src.parent != parent_path]
		return files

	fileOperation = Signal(FileOperation)

	def dropMimeData(self, qmime, action, row, column, parent_qidx):
		if not self.canDropMimeData(qmime, action, row, column, parent_qidx):
			return False

		files = self._getDroppedPaths(qmime, parent_qidx)

		parent_path = Path(self.filePath(parent_qidx))

		if action == Qt.DropAction.MoveAction:
			op = "cut"
		elif action == Qt.DropAction.CopyAction:
			op = "copy"
		else:
			raise NotImplementedError()

		treeop = FileOperation(parent_path, files, op, None)
		self.fileOperation.emit(treeop)

		# this is actually fake, the operation has not finished yet
		return True


class DirTreeView(QTreeView):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		mdl = FSModelWithDND(parent=self)
		mdl.setFilter(QDir.Filter.AllDirs | QDir.Filter.Drives | QDir.Filter.NoDotAndDotDot)
		self.setModel(mdl)
		mdl.fileOperation.connect(self.modelFileOperation)

		# all sections/columns but "filename" are hidden, so filename is the last section
		# it must not be auto-stretched if we want it to auto-expand past the widget's size
		self.header().setStretchLastSection(False)
		self.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		for col in range(1, self.header().count()):
			self.setColumnHidden(col, True)

		# actions
		action = QAction(self.tr("&Rename folder..."), self)
		action.setShortcut(QKeySequence("F2"))
		action.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
		action.triggered.connect(self.popRenameSelected)
		self.addAction(action)

		act = QAction(self.tr("&Create folder..."), self)
		act.triggered.connect(self._createFolder)
		self.addAction(act)

		act = QAction(self.tr("Trash folder..."), self)
		act.triggered.connect(self._trashFolder)
		self.addAction(act)

		action = QAction(self.tr("Show &hidden folders"), self)
		action.setCheckable(True)
		action.toggled.connect(self.toggleHidden)
		self.addAction(action)

		self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

	def setRootPath(self, path):
		self.root_path = path
		qidx = self.model().setRootPath(path)
		self.setRootIndex(qidx)

	def openTo(self, path):
		qidx = self.model().index(path)
		self.scrollTo(qidx, QTreeView.ScrollHint.PositionAtCenter)

	def selectPath(self, path):
		qidx = self.model().index(path)
		self.setCurrentIndex(qidx)

	def selectedPath(self):
		return self.model().filePath(self.currentIndex())

	@Slot()
	def popRenameSelected(self):
		db = self.window().db
		current = Path(self.selectedPath()).absolute()

		new, ok = QInputDialog.getText(
			self,
			self.tr("Rename directory"),
			self.tr("New name for directory"),
			QLineEdit.EchoMode.Normal,
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

		rename_folder(current, new, db)
		self.selectPath(str(new))

	def pasteFiles(self):
		target = Path(self.selectedPath())

		op, files = get_files_clipboard(ClipQt)

		assert op in ("copy", "cut")

		treeop = FileOperation(target, files, op, self.window().db)
		dlg = FileOperationProgressDialog(self)
		treeop.setParent(dlg)
		dlg.setOp(treeop)
		dlg.start()

	@Slot(FileOperation)
	def modelFileOperation(self, treeop):
		treeop.db = self.window().db
		dlg = FileOperationProgressDialog(self)
		dlg.setOp(treeop)
		dlg.setModal(True)
		treeop.setParent(dlg)
		dlg.start()

	@Slot()
	def _trashFolder(self):
		current = Path(self.selectedPath()).absolute()
		if not can_trash():
			QMessageBox.error(
				self,
				self.tr("Trash error"),
				self.tr("trash-put is not installed, cannot trash files"),
			)
			return

		button = QMessageBox.question(
			self,
			self.tr("Send to trash?"),
			self.tr("Are you sure you want to send this to trash?\n%s") % current,
		)
		if button != QMessageBox.StandardButton.Yes:
			return

		trash_items([current])

	@Slot()
	def _createFolder(self):
		current = Path(self.selectedPath()).absolute()

		new, ok = QInputDialog.getText(
			self,
			self.tr("Create directory"),
			self.tr("Name for new directory"),
			QLineEdit.EchoMode.Normal,
			self.tr("new_folder")
		)

		if not ok or not new:
			return
		if "/" in new:
			QMessageBox.critical(
				self,
				self.tr("Error"),
				self.tr("New name %r cannot contain '/'") % new,
			)
			return

		current.joinpath(new).mkdir()

	@Slot(bool)
	def toggleHidden(self, show):
		model = self.model()
		if show:
			model.setFilter(model.filter() | QDir.Filter.Hidden)
		else:
			model.setFilter(model.filter() & ~QDir.Filter.Hidden)

	def wheelEvent(self, event):
		if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
			QCoreApplication.sendEvent(self.horizontalScrollBar(), event)
		else:
			super().wheelEvent(event)
