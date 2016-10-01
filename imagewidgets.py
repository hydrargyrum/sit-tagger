
import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
Signal = pyqtSignal
Slot = pyqtSlot

import thumbnailmaker


class ThumbnailItem(QListWidgetItem):
	def __init__(self, path, widget=None):
		super(ThumbnailItem, self).__init__(os.path.basename(path), widget)
		self.path = path
		self.setData(Qt.UserRole, self.path)
		
		emptypix = QPixmap(QSize(256, 256))
		emptypix.fill(self.listWidget().palette().window().color())
		self.setIcon(QIcon(emptypix))
		
		thumbnailmaker.maker.addTask(self.path, self._thumbnailDone)

	@Slot(object)
	def _thumbnailDone(self, thumbpath):
		if thumbpath:
			self.setIcon(QIcon(thumbpath))

	def cancelThumbnail(self):
		pass
		#~ thumbnailmaker.maker.cancelTask(self.path)

	def getPath(self):
		return self.path


class ImageList(QListWidget):
	def __init__(self):
		super(ImageList, self).__init__()
		self.setViewMode(QListView.IconMode)
		self.setMovement(QListView.Static)
		self.setResizeMode(QListView.Adjust)
		self.setIconSize(QSize(256, 256))
		self.setGridSize(QSize(256, 256))
		#~ self.setUniformItemSizes(True)
		self.setLayoutMode(QListView.Batched)
		self.setBatchSize(1)

	def removeItems(self):
		for i in xrange(self.count()):
			self.item(i).cancelThumbnail()
		self.clear()

	def setFiles(self, files):
		self.removeItems()
		
		for f in files:
			item = ThumbnailItem(f, self)

	def getFiles(self):
		return [self.item(i).getPath() for i in xrange(self.count())]
