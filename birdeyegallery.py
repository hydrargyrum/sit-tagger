#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

from pathlib import Path
import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

Signal = pyqtSignal
Slot = pyqtSlot

import vignette


PICS = {}
THUMBS = {}
COLUMNS = 8
NULLPIX = None


class Scanner(QThread):
	@staticmethod
	def is_image(entry):
		return entry.name.endswith(".jpg")

	def __init__(self, root):
		super().__init__()
		self.root = root

	newdir = Signal(Path)
	newfile = Signal(Path)

	def run(self):
		self.scan(self.root)

	def scan(self, root):
		dirs = []

		for sub in root.iterdir():
			if sub.is_dir():
				# files then dirs
				dirs.append(sub)

			elif sub.is_file() and self.is_image(sub):
				thumb = vignette.get_thumbnail(str(sub))
				if thumb:
					if root not in PICS:
						PICS[root] = []
						self.newdir.emit(root)

					PICS[root].append(sub)
					THUMBS[sub] = Path(thumb)
					self.newfile.emit(sub)

		for sub in dirs:
			# depth first
			self.scan(sub)


class LazyImageView(QPushButton):
	def __init__(self, path):
		super().__init__()
		self.path = str(path)
		self.thumb = str(THUMBS[path])

	def buildPix(self):
		pix = QPixmapCache.find(self.path)
		if not pix:
			print(f"rebuilding pix of {self.path}")
			pix = QPixmap()
			pix.load(self.path)
			if pix.isNull():
				# TODO does NULLPIX count in cache more than once?
				pix = NULLPIX
			else:
				pix = pix.scaled(
					NULLPIX.size(),
					Qt.KeepAspectRatio,
					Qt.SmoothTransformation,
				)

			QPixmapCache.insert(self.path, pix)
		return pix

	def paintEvent(self, ev):
		pix = self.buildPix()

		if 0:
			pnt = QPainter(self)
			pnt.drawPixmap(0, 0, pix)
		else:
			pnt = QStylePainter(self)
			option = QStyleOptionFocusRect()
			option.initFrom(self)
			option.backgroundColor = self.palette().color(QPalette.Background)

			pnt.drawItemPixmap(option.rect, Qt.AlignCenter, pix)
			pnt.drawPrimitive(int(QStyle.CE_PushButton), option)

	def sizeHint(self):
		return NULLPIX.size()

	minimumSizeHint = sizeHint


class DirView(QWidget):
	def __init__(self, path):
		super().__init__()
		# TODO use some sort of flow layout? make qlistview lazy?
		self.setLayout(QGridLayout())
		self.path = path
		self.files = []

	def add_file(self, sub):
		row, col = divmod(len(self.files), COLUMNS)
		self.files.append(sub)
		self.layout().addWidget(LazyImageView(sub), row * 2, col, Qt.AlignCenter)

		label = QLabel(sub.name)
		label.setWordWrap(True)
		self.layout().addWidget(label, row * 2 + 1, col)


class BirdEye(QWidget):
	def __init__(self):
		super().__init__()
		self.dirs = {}
		self.setLayout(QVBoxLayout())

	@Slot(Path)
	def add_dir(self, path):
		title = QPushButton(str(path))
		title.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"file://{path}")))
		self.layout().addWidget(title)
		self.dirs[path] = DirView(path)
		self.layout().addWidget(self.dirs[path])

	@Slot(Path)
	def add_file(self, file):
		parent = file.parent
		self.dirs[parent].add_file(file)

	def sizeHint(self):
		return QSize(100, sum(self.layout().itemAt(i).sizeHint().height() for i in range(self.layout().count())))


QPixmapCache.setCacheLimit(100 << 10)

app = QApplication([])
#NULLPIX = QPixmap(QSize(256, 256))
NULLPIX = QPixmap(QSize(128, 128))
NULLPIX.fill(Qt.black)

beye = BirdEye()
scroller = QScrollArea()
scroller.setWidgetResizable(True)
#beye.show()
scroller.setWidget(beye)
scroller.show()

root = Path(sys.argv[1]).resolve()
scanner = Scanner(root)
scanner.newdir.connect(beye.add_dir)
scanner.newfile.connect(beye.add_file)
scanner.start()

app.exec()
