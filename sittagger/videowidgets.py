# SPDX-License-Identifier: WTFPL

import os.path

from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, QUrl, Qt
from PyQt5.QtWidgets import QLabel, QWidget, QPushButton, QTableWidget, QTableWidgetItem, QSlider, QHBoxLayout, QVBoxLayout
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtMultimedia import (
	QMediaContent, QMediaPlayer, QMediaPlaylist,
)

from .tagwidgets import TagChooserDialog


class SeekSlider(QSlider):
	def __init__(self, mp):
		super().__init__(Qt.Horizontal)
		self.mediaPlayer = mp
		self.mediaPlayer.durationChanged.connect(self._setMax)
		self.mediaPlayer.seekableChanged.connect(self.setEnabled)
		self.mediaPlayer.positionChanged.connect(self._slide)
		self.valueChanged.connect(self.mediaPlayer.setPosition)

		self.setEnabled(self.mediaPlayer.isSeekable())
		if self.mediaPlayer.duration():
			self._setMax(self.mediaPlayer.duration())
		if self.mediaPlayer.position():
			self._slide(self.mediaPlayer.position())

	@Slot(int)
	def _slide(self, pos):
		blocking = self.blockSignals(True)
		self.setValue(pos)
		self.blockSignals(blocking)

	@Slot(int)
	def _setMax(self, duration):
		self.setMaximum(duration)


class PositionLabel(QLabel):
	def __init__(self, mp, format='{fsec:03.0f} ({min:02.0f}:{sec:02.0f})'):
		super().__init__()
		self.format = format
		self.max = 0
		self.mediaPlayer = mp
		self.mediaPlayer.durationChanged.connect(self._setMax)
		self.mediaPlayer.positionChanged.connect(self.updateLabel)

	@Slot(int)
	def _setMax(self, ms):
		self.max = ms

	@Slot(int)
	def updateLabel(self, ms):
		min, sec = divmod(ms / 1000, 60)
		tmin, tsec = divmod(self.max / 1000, 60)
		d = {
			'ms': ms,
			'fsec': ms // 1000,
			'min': min,
			'sec': sec,
			'tmin': tmin,
			'tsec': tsec,
		}
		self.setText(self.format.format(**d))


class BasicVideoWidget(QVideoWidget):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.mediaPlayer = QMediaPlayer(parent=self)
		self.setMediaObject(self.mediaPlayer)

		self.playlist = QMediaPlaylist()
		self.playlist.setPlaybackMode(QMediaPlaylist.Loop)
		self.mediaPlayer.setPlaylist(self.playlist)

		self.mediaPlayer.positionChanged.connect(self._positionChanged)
		self.mediaPlayer.mutedChanged.connect(self.mutedChanged)
		self.mediaPlayer.durationChanged.connect(self._durationChanged)
		self.mediaPlayer.stateChanged.connect(self.stateChanged)
		self.mediaPlayer.seekableChanged.connect(self.seekableChanged)

	def loadUrl(self, url):
		mc = QMediaContent(url)
		self.playlist.clear()
		self.playlist.addMedia(mc)

	def load(self, path):
		self.loadUrl(QUrl.fromLocalFile(os.path.abspath(path)))

	@Slot()
	def play(self):
		self.mediaPlayer.play()

	@Slot()
	def pause(self):
		self.mediaPlayer.pause()

	@Slot()
	def stop(self):
		self.mediaPlayer.stop()

	@Slot(bool)
	def setMuted(self, b):
		self.mediaPlayer.setMuted(b)

	mutedChanged = Signal(bool)

	@Slot()
	def playPause(self):
		if self.mediaPlayer.state() != QMediaPlayer.PlayingState:
			self.mediaPlayer.play()
		else:
			self.mediaPlayer.pause()

	def state(self):
		return self.mediaPlayer.state()

	stateChanged = Signal(QMediaPlayer.State)

	def duration(self):
		return self.mediaPlayer.duration()

	durationChanged = Signal(int)

	@Slot(int)
	def setPosition(self, p):
		self.mediaPlayer.setPosition(p)

	def position(self):
		return self.mediaPlayer.position()

	@Slot('qint64')
	def _positionChanged(self, p):
		self.positionChanged.emit(p)

	positionChanged = Signal(int)

	@Slot('qint64')
	def _durationChanged(self, p):
		self.durationChanged.emit(p)

	seekableChanged = Signal(bool)

	def isSeekable(self):
		return self.mediaPlayer.isSeekable()


class VideoControl(QWidget):
	def __init__(self, video, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.video = video
		self.setLayout(QHBoxLayout())

		self.playPauseButton = QPushButton('▶')
		self.playPauseButton.clicked.connect(self.video.playPause)
		self.layout().addWidget(self.playPauseButton)

		self.seeker = SeekSlider(self.video)
		self.seeker.setSingleStep(1000)
		self.layout().addWidget(self.seeker)

		self.posLabel = PositionLabel(self.video)
		self.layout().addWidget(self.posLabel)

		self.video.stateChanged.connect(self.stateChanged)
		self.stateChanged(video.state())

	@Slot(QMediaPlayer.State)
	def stateChanged(self, state):
		if state == QMediaPlayer.PlayingState:
			self.playPauseButton.setText('▋▋')
		else:
			self.playPauseButton.setText('▶')

	def showEvent(self, ev):
		super().showEvent(ev)
		self.update()


class VideoTagEditor(QWidget):
	def __init__(self, db):
		super().__init__()

		self.path = None
		self.db = db
		self.initUi()

	def initUi(self):
		self.setLayout(QVBoxLayout())

		self.video = BasicVideoWidget()
		self.layout().addWidget(self.video, 1)

		self.row2 = QWidget()
		self.row2.setLayout(QHBoxLayout())
		self.layout().addWidget(self.row2)

		self.playPauseButton = QPushButton('▶')
		self.playPauseButton.clicked.connect(self.playPause)
		self.row2.layout().addWidget(self.playPauseButton)

		self.seeker = SeekSlider(self.video)
		self.seeker.setSingleStep(1000)
		#~ self.seeker.valueChanged.connect(self.video.seek)
		self.row2.layout().addWidget(self.seeker)

		self.posLabel = PositionLabel(self.video)
		self.row2.layout().addWidget(self.posLabel)

		startSet = QPushButton('<')
		startSet.clicked.connect(self.rowSetStart)
		self.layout().addWidget(startSet)

		endSet = QPushButton('>')
		endSet.clicked.connect(self.rowSetEnd)
		self.layout().addWidget(endSet)

		self.endRow = QWidget()
		self.endRow.setLayout(QHBoxLayout())
		self.layout().addWidget(self.endRow)

		self.table = QTableWidget()
		self.table.setColumnCount(3)
		self.table.setHorizontalHeaderLabels(['Tags', 'Start time', 'End time'])
		self.table.itemChanged.connect(self._itemChanged)
		self.table.itemDoubleClicked.connect(self._itemDClicked)
		self.layout().addWidget(self.table)

		self.addRowButton = QPushButton('Add')
		self.addRowButton.clicked.connect(self.addRow)
		self.endRow.layout().addWidget(self.addRowButton)

		self.delRowButton = QPushButton('Remove')
		self.delRowButton.clicked.connect(self.delRow)
		self.endRow.layout().addWidget(self.delRowButton)

	def setFile(self, path):
		self.path = path

		if self.video.state() == QMediaPlayer.PlayingState:
			self.video.pause()

		self.video.load(path)

		self.loadTags()

	@Slot()
	def playPause(self):
		if self.video.state() != QMediaPlayer.PlayingState:
			self.video.play()
			self.playPauseButton.setText('▋▋')
		else:
			self.video.pause()
			self.playPauseButton.setText('▶')

	def chooseTags(self, row):
		row = self.table.currentRow()
		taglist = self.table.item(row, 0).text().split(' ')

		dialog = TagChooserDialog(self.db)
		dialog.setTags(list(taglist))
		dialog.exec_()
		taglist = dialog.selectedTags()
		self.table.item(row, 0).setText(' '.join(taglist))
		#~ self.saveTags()

	@Slot()
	def rowSetStart(self):
		ms = self.video.position()
		n = self.table.currentRow()
		self.table.item(n, 1).setText('%d' % (ms / 1000))
		#~ self.saveTags()

	@Slot()
	def rowSetEnd(self):
		ms = self.video.position()
		n = self.table.currentRow()
		self.table.item(n, 2).setText('%d' % (ms / 1000))
		#~ self.saveTags()

	@Slot()
	def delRow(self):
		self.table.removeRow(self.table.currentRow())
		self.saveTags()

	@Slot()
	def addRow(self):
		n = self.table.rowCount()
		self.table.insertRow(n)
		for col in range(self.table.columnCount()):
			self.table.setItem(n, col, QTableWidgetItem())

	def loadTags(self):
		blocking = self.table.signalsBlocked()
		try:
			self.table.blockSignals(True)
			tags = self.db.find_tags_by_file(self.path)
			for t in tags:
				for start, end in self.db.get_extras_for_file(self.path, t):
					n = self.table.rowCount()
					self.table.insertRow(n)
					self.table.setItem(n, 0, QTableWidgetItem(t))
					self.table.setItem(n, 1, QTableWidgetItem('%d' % (start / 1000)))
					self.table.setItem(n, 2, QTableWidgetItem('%d' % (end / 1000)))
		finally:
			self.table.blockSignals(blocking)

	def saveTags(self):
		duration = self.video.duration() / 1000

		with self.db:
			self.db.remove_file(self.path)
			for i in range(self.table.rowCount()):
				tags = self.table.item(i, 0).text().split(' ')
				tags = [t for t in tags if t]
				if not tags:
					continue
				start = int(self.table.item(i, 1).text() or 0) * 1000
				end = int(self.table.item(i, 2).text() or duration) * 1000
				for tag in tags:
					self.db.tag_file(self.path, tag, start, end)

	def _itemChanged(self, qitem):
		self.saveTags()
		pass

	def _itemDClicked(self, item):
		if item.column() != 0:
			pass
		self.chooseTags(item.row())
