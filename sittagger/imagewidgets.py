
import os
from pathlib import Path

from PyQt5.QtCore import QSize, Qt, pyqtSlot as Slot
from PyQt5.QtGui import QIcon, QPixmap, QKeySequence
from PyQt5.QtWidgets import (
	QListWidget, QListWidgetItem, QListView,
	QAction, QInputDialog, QLineEdit,
	QMessageBox,
)

from .fsops import move_file
from . import thumbnailmaker


class ThumbnailItem(QListWidgetItem):
	def __init__(self, path, widget=None):
		super(ThumbnailItem, self).__init__(os.path.basename(path), widget)
		self.path = path
		self.setData(Qt.UserRole, self.path)

		emptypix = QPixmap(QSize(256, 256))
		emptypix.fill(self.listWidget().palette().window().color())
		self.setIcon(QIcon(emptypix))

		thumbnailmaker.maker.addTask(self.path)

	def cancelThumbnail(self):
		thumbnailmaker.maker.cancelTask(self.path)

	def getPath(self):
		return self.path

	def getPathObject(self):
		return Path(self.getPath())

	def _updatePath(self, newpath):
		self.path = newpath
		self.setData(Qt.UserRole, self.path)
		self.setText(Path(newpath).name)


class ImageList(QListWidget):
	def __init__(self, *args, **kwargs):
		super(ImageList, self).__init__(*args, **kwargs)
		self.items = {}

		thumbnailmaker.maker.done.connect(self._thumbnailDone)

		action = QAction(parent=self)
		action.setShortcut(QKeySequence("F2"))
		action.setShortcutContext(Qt.WidgetShortcut)
		action.triggered.connect(self.popRenameSelected)
		self.addAction(action)

	@Slot(str, str)
	def _thumbnailDone(self, origpath, thumbpath):
		if origpath not in self.items:
			return
		if thumbpath:
			self.items[origpath].setIcon(QIcon(thumbpath))

	def removeItems(self):
		for i in range(self.count()):
			self.item(i).cancelThumbnail()
		self.clear()

	def setFiles(self, files):
		self.removeItems()
		self.items = {}

		for f in files:
			item = ThumbnailItem(f, self)
			self.items[f] = item

	def getFiles(self):
		return [self.item(i).getPath() for i in range(self.count())]

	@Slot()
	def popRenameSelected(self):
		db = self.window().db

		selected = self.selectedItems()
		if len(selected) != 1:
			# cannot rename 0 or multiple files
			return

		current = selected[0].getPathObject().absolute()

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

		item = self.items.pop(str(current))
		item._updatePath(str(new))
		self.items[str(new)] = item
