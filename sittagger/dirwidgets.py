# SPDX-License-Identifier: WTFPL

from pathlib import Path

from PyQt5.QtCore import QDir, pyqtSlot as Slot, Qt, pyqtSignal as Signal, QMimeData
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
	QTreeView, QFileSystemModel, QAction, QInputDialog, QLineEdit,
	QMessageBox,
)

from .fileoperationdialog import FileOperationProgressDialog
from .fsops import rename_folder, FileOperation
from .fm_interop import ClipQt, get_files_clipboard, MIME_LIST, _parse_url


class FSModelWithDND(QFileSystemModel):
	def flags(self, qidx):
		flags = super().flags(qidx)
		if qidx.isValid():
			flags |= Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
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
		return Qt.CopyAction | Qt.MoveAction

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

		if action == Qt.MoveAction:
			op = "cut"
		elif action == Qt.CopyAction:
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
		mdl.setFilter(QDir.AllDirs | QDir.Drives | QDir.NoDotAndDotDot)
		self.setModel(mdl)
		mdl.fileOperation.connect(self.modelFileOperation)

		for col in range(1, self.header().count()):
			self.setColumnHidden(col, True)

		# actions
		action = QAction(self.tr("&Rename folder..."), self)
		action.setShortcut(QKeySequence("F2"))
		action.setShortcutContext(Qt.WidgetShortcut)
		action.triggered.connect(self.popRenameSelected)
		self.addAction(action)

		act = QAction(self.tr("&Create folder..."), self)
		act.triggered.connect(self._createFolder)
		self.addAction(act)

		action = QAction(self.tr("Show &hidden folders"), self)
		action.setCheckable(True)
		action.toggled.connect(self.toggleHidden)
		self.addAction(action)

		self.setContextMenuPolicy(Qt.ActionsContextMenu)

	def setRootPath(self, path):
		self.root_path = path
		qidx = self.model().setRootPath(path)
		self.setRootIndex(qidx)

	def openTo(self, path):
		qidx = self.model().index(path)
		self.scrollTo(qidx, self.PositionAtCenter)

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
	def _createFolder(self):
		current = Path(self.selectedPath()).absolute()

		new, ok = QInputDialog.getText(
			self,
			self.tr("Create directory"),
			self.tr("Name for new directory"),
			QLineEdit.Normal,
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
			model.setFilter(model.filter() | QDir.Hidden)
		else:
			model.setFilter(model.filter() & ~QDir.Hidden)
