
import os

from PyQt5.QtCore import QSize, Qt, pyqtSlot as Slot
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QListView

import thumbnailmaker


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
		pass
		#~ thumbnailmaker.maker.cancelTask(self.path)

	def getPath(self):
		return self.path


class ImageList(QListWidget):
	def __init__(self):
		super(ImageList, self).__init__()
		self.items = {}

		self.setViewMode(QListView.IconMode)
		self.setMovement(QListView.Static)
		self.setResizeMode(QListView.Adjust)
		self.setIconSize(QSize(256, 256))
		self.setGridSize(QSize(256, 256))
		#~ self.setUniformItemSizes(True)
		self.setLayoutMode(QListView.Batched)
		self.setBatchSize(1)

		thumbnailmaker.maker.done.connect(self._thumbnailDone)

	@Slot(unicode, unicode)
	def _thumbnailDone(self, origpath, thumbpath):
		if origpath not in self.items:
			return
		if thumbpath:
			self.items[origpath].setIcon(QIcon(thumbpath))

	def removeItems(self):
		for i in xrange(self.count()):
			self.item(i).cancelThumbnail()
		self.clear()

	def setFiles(self, files):
		self.removeItems()
		self.items = {}

		for f in files:
			item = ThumbnailItem(f, self)
			self.items[f] = item

	def getFiles(self):
		return [self.item(i).getPath() for i in xrange(self.count())]
