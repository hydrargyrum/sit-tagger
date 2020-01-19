
from PyQt5.QtCore import QDir
from PyQt5.QtWidgets import QTreeView, QFileSystemModel


class DirTreeView(QTreeView):
	def __init__(self, *args, **kwargs):
		super(DirTreeView, self).__init__(*args, **kwargs)

		mdl = QFileSystemModel(parent=self)
		mdl.setFilter(QDir.AllDirs | QDir.Drives | QDir.Hidden | QDir.NoDotAndDotDot)
		self.setModel(mdl)

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
