#!/usr/bin/env python
# base: 2010-02
# license: WTFPLv2

import sys, os
import time

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
Signal = pyqtSignal
Slot = pyqtSlot

import dbtag
from imagewidgets import ImageList
from tagwidgets import TagEditor, TagChooser
from fullscreenviewer import ImageViewer

# qsplitter = a | b
# a = qtabw 
# a / tagchooser
# a / qtreeview
# b = c - d
# c = qlistview
# d = tageditor


class Win(QMainWindow):
	def __init__(self, options):
		super(Win, self).__init__()

		self.db = dbtag.Db()
		self.db.open(options.db)
		self.db.create_tables()
		self.rootPath = options.filespath

		self._init_widgets()
		self._init_more()

	def _init_widgets(self):
		bigsplitter = QSplitter(Qt.Horizontal, self)
		self.setCentralWidget(bigsplitter)

		leftsplitter = QSplitter(Qt.Vertical, self)

		self.tabWidget = QTabWidget(self)

		self.tagChooser = TagChooser(self.db)
		self.dirChooser = QTreeView(self)

		self.tabWidget.addTab(self.dirChooser, 'Dir')
		self.tabWidget.addTab(self.tagChooser, 'Tags')

		self.tagEditor = TagEditor(self.db)
		self.imageList = ImageList()

		leftsplitter.addWidget(self.tabWidget)
		leftsplitter.addWidget(self.tagEditor)

		bigsplitter.addWidget(leftsplitter)
		bigsplitter.addWidget(self.imageList)

		self.viewer = ImageViewer(self.db)

	def _init_more(self):
		self.setWindowTitle('Tags4')

		self.dirModel = QFileSystemModel()
		self.dirModel.setFilter(QDir.AllDirs | QDir.Drives | QDir.Hidden | QDir.NoDotAndDotDot)
		qidx = self.dirModel.setRootPath(self.rootPath)
		self.dirChooser.setModel(self.dirModel)
		self.dirChooser.setRootIndex(qidx)

		self.dirChooser.clicked.connect(self.browseSelectedDir)
		self.imageList.itemSelectionChanged.connect(self._editTagsItems)
		self.imageList.itemDoubleClicked.connect(self._spawnViewerItem)
		self.imageList.setSelectionMode(QAbstractItemView.ExtendedSelection)

		self.tabWidget.currentChanged.connect(self._tabSelected)
		self.tagChooser.changed.connect(self.browseSelectedTags)

	def editTags(self, path):
		self.tagEditor.setFile(path)

	def editTagsItems(self, paths):
		self.tagEditor.setFiles(paths)

	def spawnViewer(self, files, currentFile):
		self.viewer.spawn(files, currentFile)

	@Slot()
	def _editTagsItems(self):
		self.editTagsItems([qitem.getPath() for qitem in self.imageList.selectedItems()])

	@Slot(QListWidgetItem)
	def _spawnViewerItem(self, qitem):
		self.spawnViewer(self.imageList.getFiles(), qitem.getPath())

	@Slot()
	def browseSelectedDir(self):
		path = self.dirModel.filePath(self.dirChooser.currentIndex())
		if not path:
			return
		files = [os.path.join(path, f) for f in os.listdir(path)]
		files = filter(os.path.isfile, files)
		files.sort()
		self.imageList.setFiles(files)

	@Slot()
	def browseSelectedTags(self):
		self.imageList.setFiles(self.tagChooser.matchingFiles())

	@Slot(int)
	def _tabSelected(self, idx):
		if idx == 0:
			self.browseSelectedDir()
		else:
			self.browseSelectedTags()

	def browsePath(self, path):
		self.imageList.setFiles(os.path.join(path, f) for f in os.listdir(path))


def xdg_config():
	return os.getenv('XDG_CONFIG_HOME', os.getenv('HOME', '/') + '/.config')

def parse_options(args):
	import optparse
	parser = optparse.OptionParser()
	parser.add_option('-d', '--database', metavar='FILE', dest='db')
	parser.add_option('-p', '--path', dest='filespath')
	parser.set_defaults(filespath='/', db=xdg_config() + '/sit-tagger.sqlite')
	opts, _ = parser.parse_args(args)
	return opts

if __name__ == '__main__':
	if sys.excepthook is sys.__excepthook__:
		sys.excepthook = lambda *args: sys.__excepthook__(*args)

	app = QApplication(sys.argv)
	opts = parse_options(list(app.arguments()))
	win = Win(opts)
	win.show()
	app.exec_()
