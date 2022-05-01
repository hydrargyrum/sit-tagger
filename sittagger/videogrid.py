#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSplitter, QMainWindow, QApplication, QInputDialog, QFileDialog

from .videowidgets import BasicVideoWidget, VideoControl


class GridManager(QSplitter):
	def __init__(self, *args, **kwargs):
		super().__init__(Qt.Horizontal, *args, **kwargs)
		self.addColumn()

	def addColumn(self):
		w = QSplitter(Qt.Vertical)
		self.addWidget(w)
		w.splitterMoved.connect(self.subMoved)
		return w

	def subMoved(self, pos, index):
		sender = self.sender()
		for i in range(self.count()):
			sub = self.widget(i)
			if sub is sender:
				continue
			sub.moveSplitter(pos, index)

	def widgets(self):
		return [self.widget(i) for i in range(self.count())]

	def addWidgetInGrid(self, w):
		basecount = self.widget(0).count()

		for sub in self.widgets()[1:]:
			if sub.count() < basecount:
				sub.addWidget(w)
				return

		if basecount >= self.count():
			sub = self.addColumn()
			sub.addWidget(w)
		else:
			self.widget(0).addWidget(w)


class Video(BasicVideoWidget):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.setMuted(True)
		self.setMouseTracking(True)
		self.controls = None

	def mouseDoubleClickEvent(self, ev):
		self.playPause()

	def resizeEvent(self, ev):
		super().resizeEvent(ev)
		if self.controls:
			r = self.rect()
			r.setTop(r.bottom() - 40)
			self.controls.setGeometry(r)

	def createControls(self):
		self.controls = VideoControl(self, parent=self)
		self.controls.setAutoFillBackground(True)
		r = self.rect()
		r.setTop(r.bottom() - 40)
		self.controls.setGeometry(r)

	def mouseMoveEvent(self, ev):
		if ev.pos().y() > self.size().height() - 40:
			if not self.controls:
				self.createControls()
				self.controls.show()
		elif self.controls:
			self.controls.hide()
			self.controls.setParent(None)
			self.controls.close()
			self.controls = None


class Win(QMainWindow):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.setCentralWidget(GridManager())

		m = self.menuBar().addMenu('&Open')
		m.addAction('Open &file...').triggered.connect(self.openFile)
		m.addAction('Open &URL...').triggered.connect(self.openUrl)

	def openFile(self):
		f, _ = QFileDialog.getOpenFileName(self, 'Open', '.')
		if not f:
			return
		v = Video()
		v.load(f)
		self.centralWidget().addWidgetInGrid(v)

	def openUrl(self):
		u, _ = QInputDialog.getText(self, 'Open')
		if not u:
			return
		v = Video()
		v.loadUrl(u)
		self.centralWidget().addWidgetInGrid(v)


if __name__ == '__main__':
	app = QApplication(sys.argv)
	w = Win()
	w.show()

	for f in app.arguments()[1:]:
		v = Video()
		if f.startswith('/'):
			v.load(f)
		else:
			v.loadUrl(f)
		v.play()
		w.centralWidget().addWidgetInGrid(v)

	app.exec_()
