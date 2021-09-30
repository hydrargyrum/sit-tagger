
from pathlib import Path

from PyQt5.QtCore import QDir, pyqtSlot as Slot, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
	QTreeView, QFileSystemModel, QAction, QInputDialog, QLineEdit,
	QMessageBox, QProgressDialog,
)

from .fsops import move_folder, FileOperation
from .fm_interop import ClipQt, get_files_clipboard


class DirTreeView(QTreeView):
	def __init__(self, *args, **kwargs):
		super(DirTreeView, self).__init__(*args, **kwargs)

		mdl = QFileSystemModel(parent=self)
		mdl.setFilter(QDir.AllDirs | QDir.Drives | QDir.Hidden | QDir.NoDotAndDotDot)
		self.setModel(mdl)

		action = QAction(parent=self)
		action.setShortcut(QKeySequence("F2"))
		action.setShortcutContext(Qt.WidgetShortcut)
		action.triggered.connect(self.popRenameSelected)
		self.addAction(action)

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

		move_folder(current, new, db)
		self.selectPath(str(new))

	def pasteFiles(self):
		target = Path(self.selectedPath())

		op, files = get_files_clipboard(ClipQt)

		assert op in ("copy", "cut")

		treeop = FileOperation(target, files, op)
		dlg = FileOperationProgress(self)
		dlg.setOp(treeop)
		dlg.show()
		dlg.open()
		treeop.start()


class FileOperationProgress(QProgressDialog):
	def __init__(self, parent):
		super().__init__(parent)
		self.setAutoReset(False)
		self.setAutoClose(False)
		self.setMinimumDuration(0)
		self.finished.connect(self.deleteLater)
		self.op = None

	def setOp(self, op):
		self.op = op
		self.op.processing.connect(self.onProgress)
		self.op.started.connect(self.exec_)
		self.op.finished.connect(self.accept)
		self.canceled.connect(self.op.cancel)

	@Slot(str, int, int)
	def onProgress(self, name, current, total):
		print(name, current)
		self.setLabelText(name)
		self.setValue(current * 100 // total)
