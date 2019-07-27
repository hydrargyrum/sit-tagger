#!/usr/bin/env python3
# base: 2010-02
# license: WTFPLv2

import sys
import os

from PyQt5.QtCore import Qt, pyqtSlot as Slot
from PyQt5.QtWidgets import (
	QMainWindow, QListWidgetItem, QSplitter, QApplication, QAbstractItemView, QTabWidget,
)

from . import dbtag
from .imagewidgets import ImageList
from .tagwidgets import TagEditor, TagChooser
from .fullscreenviewer import ImageViewer
from .dirwidgets import DirTreeView

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
		self.db.do_migrations()
		self.rootPath = options.filespath

		self._init_widgets()
		self._init_dirchooser()
		self._init_tagchooser()
		self._init_imagelist()
		self._init_tabs()

	def _init_widgets(self):
		bigsplitter = QSplitter(Qt.Horizontal, self)
		self.setCentralWidget(bigsplitter)

		leftsplitter = QSplitter(Qt.Vertical, self)

		self.tabWidget = QTabWidget(self)

		self.tagChooser = TagChooser(self.db, parent=self)
		self.dirChooser = DirTreeView(self)

		self.tabWidget.addTab(self.dirChooser, 'Dir')
		self.tabWidget.addTab(self.tagChooser, 'Tags')

		self.tagEditor = TagEditor(self.db, parent=self)
		self.imageList = ImageList(parent=self)

		leftsplitter.addWidget(self.tabWidget)
		leftsplitter.addWidget(self.tagEditor)

		bigsplitter.addWidget(leftsplitter)
		bigsplitter.addWidget(self.imageList)

		self.viewer = None

	def _init_dirchooser(self):
		self.dirChooser.setRootPath(self.rootPath)
		self.dirChooser.openTo(os.getcwd())
		self.dirChooser.clicked.connect(self.browseSelectedDir)

	def _init_imagelist(self):
		self.imageList.itemSelectionChanged.connect(self._editTagsItems)
		self.imageList.itemDoubleClicked.connect(self._spawnViewerItem)
		self.imageList.setSelectionMode(QAbstractItemView.ExtendedSelection)

	def _init_tabs(self):
		self.tabWidget.currentChanged.connect(self._tabSelected)

	def _init_tagchooser(self):
		self.tagChooser.changed.connect(self.browseSelectedTags)

	def editTags(self, path):
		self.tagEditor.setFile(path)

	def editTagsItems(self, paths):
		self.tagEditor.setFiles(paths)

	def spawnViewer(self, files, currentFile):
		viewer = ImageViewer(self.db, parent=self)
		viewer.spawn(files, currentFile)

	@Slot()
	def _editTagsItems(self):
		self.editTagsItems([qitem.getPath() for qitem in self.imageList.selectedItems()])

	@Slot(QListWidgetItem)
	def _spawnViewerItem(self, qitem):
		self.spawnViewer(self.imageList.getFiles(), qitem.getPath())

	@Slot()
	def browseSelectedDir(self):
		path = self.dirChooser.selectedPath()
		if not path:
			return
		files = [os.path.join(path, f) for f in os.listdir(path)]
		files = [f for f in files if os.path.isfile(f)]
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
	import argparse

	default_db = os.getenv('SITTAGGER_DATABASE') or xdg_config() + '/sit-tagger.sqlite'

	parser = argparse.ArgumentParser()
	parser.add_argument('-d', '--database', metavar='FILE', dest='db')
	parser.add_argument('-p', '--path', dest='filespath')
	parser.set_defaults(filespath='/', db=default_db)
	opts = parser.parse_args(args)
	return opts


def main():
	if sys.excepthook is sys.__excepthook__:
		sys.excepthook = lambda *args: sys.__excepthook__(*args)

	app = QApplication(sys.argv)
	app.setApplicationDisplayName('SIT-Tagger')
	app.setApplicationName('SIT-Tagger')

	opts = parse_options(list(app.arguments())[1:])
	win = Win(opts)
	win.show()
	app.exec_()


if __name__ == '__main__':
	main()
