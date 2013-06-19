#!/usr/bin/env python
# base: 2010-02
# license: WTFPLv2

try:
	from PyQt4.QtCore import *
	from PyQt4.QtGui import *
	Signal = pyqtSignal
	Slot = pyqtSlot
except ImportError:
	from PySide.QtCore import *
	from PySide.QtGui import *
import sys, os
import time

import taglib
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

bitset = lambda num, bit, value: (num | (1 << bit)) ^ ((1 ^ value) << bit)
bitset2 = lambda num, bits, value: (num | bits) ^ ((value and [0] or [bits])[0])


class Win(QMainWindow):
	def __init__(self, options):
		super(Win, self).__init__()
		
		self.tagger = taglib.TaggingWithRoot(options.db, options.filespath)
		self.rootPath = options.filespath
		
		self._init_widgets()
		self._init_more()
	
	def _init_widgets(self):
		bigsplitter = QSplitter(Qt.Horizontal, self)
		self.setCentralWidget(bigsplitter)
		
		leftsplitter = QSplitter(Qt.Vertical, self)
		
		self.tabWidget = QTabWidget(self)
		
		self.tagChooser = TagChooser(self.tagger)
		self.dirChooser = QTreeView(self)
		
		self.tabWidget.addTab(self.dirChooser, 'Dir')
		self.tabWidget.addTab(self.tagChooser, 'Tags')
		
		self.tagEditor = TagEditor(self.tagger)
		self.imageList = ImageList()
		
		leftsplitter.addWidget(self.tabWidget)
		leftsplitter.addWidget(self.tagEditor)

		bigsplitter.addWidget(leftsplitter)
		bigsplitter.addWidget(self.imageList)
		
		self.viewer = ImageViewer(self.tagger)
	
	def _init_more(self):
		self.setWindowTitle('Tags4')
		
		self.dirModel = QFileSystemModel()
		self.dirModel.setFilter(QDir.AllDirs | QDir.Drives | QDir.Hidden)
		qidx = self.dirModel.setRootPath(self.rootPath)
		self.dirChooser.setModel(self.dirModel)
		self.dirChooser.setRootIndex(qidx)
		
		toPath = lambda qidx: str(self.dirModel.filePath(qidx))
		#~ self.dirChooser.clicked.connect(lambda qidx: self.setDisplayedDir(toPath(qidx)))
		self.dirChooser.clicked.connect(self._setDirSource)
		#~ self.imageList.itemClicked.connect(lambda qitem: self.editTags(str(qitem.data(Qt.UserRole).toString())))
		self.imageList.itemClicked.connect(self._editTagsSlot)
		self.imageList.itemDoubleClicked.connect(self._spawnViewerSlot)
		
		self.tabWidget.currentChanged.connect(self._setFilesSource)
		self.tagChooser.changed.connect(self._setTagsSource)
	
	def editTags(self, path):
		self.tagEditor.setFile(path)
	
	def spawnViewer(self, files, currentFile):
		self.viewer.spawn(files, currentFile)
	
	@Slot(QListWidgetItem)
	def _editTagsSlot(self, qitem):
		self.editTags(qitem.getPath())
	@Slot(QListWidgetItem)
	def _spawnViewerSlot(self, qitem):
		self.spawnViewer(self.imageList.getFiles(), qitem.getPath())
	
	@Slot()
	def _setDirSource(self):
		self._setFilesSource(0)
	@Slot()
	def _setTagsSource(self):
		self._setFilesSource(1)
	
	@Slot(int)
	def _setFilesSource(self, idx):
		if idx == 0:
			path = str(self.dirModel.filePath(self.dirChooser.currentIndex()))
			files = [os.path.join(path, f) for f in os.listdir(path)]
			files = filter(os.path.isfile, files)
			files.sort()
			self.imageList.setFiles(files)
		else:
			self.imageList.setFiles(self.tagChooser.matchingFiles())
	
	def setDisplayedDir(self, path):
		self.imageList.setFiles(os.path.join(path, f) for f in os.listdir(path))


def parse_options(args):
	import optparse
	parser = optparse.OptionParser()
	parser.add_option('-d', '--database', metavar='FILE', dest='db')
	parser.add_option('-p', '--path', dest='filespath')
	opts, _ = parser.parse_args(args)
	if not opts.db:
		parser.error('No database specified')
	elif not opts.filespath:
		parser.error('No path specified')
	return opts

if __name__ == '__main__':
	app = QApplication(sys.argv)
	opts = parse_options(list(map(str, app.arguments())))
	win = Win(opts)
	win.show()
	app.exec_()
