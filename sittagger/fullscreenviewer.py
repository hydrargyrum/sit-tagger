# SPDX-License-Identifier: WTFPL

from PyQt5.QtCore import (
	Qt, QEvent, pyqtSignal as Signal, pyqtSlot as Slot, QTimer, QPointF,
)
from PyQt5.QtGui import (
	QKeySequence, QPalette, QPixmap, QMovie, QIcon, QImageReader, QCursor,
)
from PyQt5.QtWidgets import QMainWindow, QScrollArea, QDockWidget, QToolBar, QLabel

from .tagwidgets import TagEditor


ZOOM_FACTOR = 0
ZOOM_FITALL = 1
ZOOM_FITCUT = 2


class AutoHideMixin:
	def leaveEvent(self, ev):
		self.hide()


class AutoHideDock(QDockWidget, AutoHideMixin):
	pass
#class AutoHideToolBar(QToolBar, AutoHideMixin):
#	pass


class ImageViewer(QMainWindow):
	def __init__(self, db, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.db = db
		self.currentIndex = -1
		self.files = []

		self._init_widgets()

	def _init_widgets(self):
		#self.toolbar = AutoHideToolBar()
		self.toolbar = QToolBar()
		self.addToolBar(self.toolbar)
		self.toolbar.hide()

		act = self.toolbar.addAction(QIcon.fromTheme('go-previous'), 'Previous')
		act.setShortcut(QKeySequence(Qt.Key_Backspace))
		act.triggered.connect(self.showPreviousFile)
		act = self.toolbar.addAction(QIcon.fromTheme('go-next'), 'Next')
		act.setShortcut(QKeySequence(Qt.Key_Space))
		act.triggered.connect(self.showNextFile)
		self.toolbar.addSeparator()

		self.scrollview = ImageViewerCenter()
		self.scrollview.installEventFilter(self) ### !
		self.setCentralWidget(self.scrollview)

		self.toolbar.addAction(QIcon.fromTheme('zoom-original'), 'Z 1:1').triggered.connect(self.scrollview.doNormalZoom)
		self.toolbar.addAction(QIcon.fromTheme('zoom-fit-best'), 'Z Fit').triggered.connect(self.scrollview.doFitAllZoom)
		self.toolbar.addAction(QIcon.fromTheme('zoom-fit-best'), 'Z FitExp').triggered.connect(self.scrollview.doFitCutZoom)
		self.toolbar.addAction(QIcon.fromTheme('zoom-in'), 'Z In').triggered.connect(self.scrollview.zoom)
		self.toolbar.addAction(QIcon.fromTheme('zoom-out'), 'Z Out').triggered.connect(self.scrollview.unzoom)

		self.fullscreenAction = self.toolbar.addAction(QIcon.fromTheme('view-fullscreen'), 'Fullscreen')
		self.fullscreenAction.setCheckable(True)
		self.fullscreenAction.toggled.connect(self.setFullscreen)
		self.toolbar.addSeparator()

		self.toolbar.addAction('Copy tags').triggered.connect(self.copyPreviousTags)

		self.tageditor = TagEditor()
		self.tageditor.setDb(self.db)

		self.docktagger = AutoHideDock()
		self.docktagger.setWidget(self.tageditor)
		self.addDockWidget(Qt.LeftDockWidgetArea, self.docktagger)
		self.docktagger.hide()

		self.scrollview.topZoneEntered.connect(self.toolbar.show)
		self.scrollview.topZoneLeft.connect(self.toolbar.hide)
		self.scrollview.leftZoneEntered.connect(self.docktagger.show)
		self.scrollview.leftZoneLeft.connect(self.docktagger.hide)

	def eventFilter(self, sview, ev):
		if ev.type() == QEvent.KeyPress:
			if ev.key() == Qt.Key_Escape:
				self.fullscreenAction.setChecked(False)
				return True
			elif ev.key() in [Qt.Key_PageUp, Qt.Key_Backspace]: # qactions
				self.showPreviousFile()
				return True
			elif ev.key() in [Qt.Key_PageDown, Qt.Key_Space]:
				self.showNextFile()
				return True
		return super().eventFilter(sview, ev)

	def spawn(self, files, currentFile):
		self.files = files
		self.currentIndex = files.index(currentFile)

		self.setFile(currentFile)
		if self.isHidden():
			#~ self.setWindowState(self.windowState() | Qt.WindowMaximized)
			#~ self.show()
			self.fullscreenAction.setChecked(False)
			self.fullscreenAction.setChecked(True)
			#~ self.showMaximized()
		else:
			self.show()

	def setFile(self, file):
		self.tageditor.setFile(file)
		self.scrollview.setFile(file)
		self.setWindowTitle(file)

	@Slot()
	def copyPreviousTags(self):
		tags = self.db.find_tags_by_file(self.files[self.currentIndex - 1])
		with self.db:
			self.db.tag_file(self.files[self.currentIndex], tags)
		self.tageditor.setFile(self.files[self.currentIndex])

	def setFullscreen(self, full):
		if full:
			self.showFullScreen()
		else:
			self.showNormal()

	@Slot()
	def showPreviousFile(self):
		if self.currentIndex > 0:
			self.currentIndex -= 1
			self.setFile(self.files[self.currentIndex])

	@Slot()
	def showNextFile(self):
		if self.currentIndex < len(self.files) - 1:
			self.currentIndex += 1
			self.setFile(self.files[self.currentIndex])


class ImageViewerCenter(QScrollArea):
	topZoneEntered = Signal()
	topZoneLeft = Signal()
	leftZoneEntered = Signal()
	leftZoneLeft = Signal()

	leftMargin = 30
	topMargin = 30

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.zoomMode = ZOOM_FACTOR
		self.zoomFactor = 1
		self.oldZoomFactor = self.zoomFactor
		self.moving = None

		imgWidget = QLabel()
		imgWidget.setMouseTracking(True)
		imgWidget.setAlignment(Qt.AlignCenter)
		self.setWidget(imgWidget)

		self.setAlignment(Qt.AlignCenter)
		self.setMouseTracking(True)
		self.setFrameShape(self.NoFrame)
		self.setWidgetResizable(True)

		pal = QPalette()
		pal.setColor(QPalette.Window, Qt.black)
		self.setPalette(pal)

		self.leftZone = False
		self.topZone = False

		self.file = None
		self.movie = None

	### events
	def mousePressEvent(self, ev):
		self.moving = (ev.pos().x(), ev.pos().y())
		self.movingScrolls = (self.horizontalScrollBar().value(), self.verticalScrollBar().value())

	def mouseReleaseEvent(self, ev):
		self.moving = False

	def mouseMoveEvent(self, ev):
		if self.moving:
			p = ev.pos()
			self.horizontalScrollBar().setValue(self.movingScrolls[0] - (p.x() - self.moving[0]))
			self.verticalScrollBar().setValue(self.movingScrolls[1] - (p.y() - self.moving[1]))
		else:
			newLeft = (ev.x() < self.leftMargin)
			if newLeft and not self.leftZone:
				self.leftZoneEntered.emit()
			elif self.leftZone and not newLeft:
				self.leftZoneLeft.emit()
			self.leftZone = newLeft

			newTop = (ev.y() < self.topMargin)
			if newTop and not self.topZone:
				self.topZoneEntered.emit()
			elif self.topZone and not newTop:
				self.topZoneLeft.emit()
			self.topZone = newTop

	def resizeEvent(self, ev):
		super().resizeEvent(ev)
		if self.zoomMode != ZOOM_FACTOR:
			self._rebuildZoom()

	def keyPressEvent_(self, ev):
		if ev.key() not in (Qt.Key_PageUp, Qt.Key_PageDown):
			QScrollArea.keyPressEvent(self, ev)

	def keyReleaseEvent_(self, ev):
		if ev.key() == Qt.Key_PageUp:
			self.imageviewer.prevImage_s()
		elif ev.key() == Qt.Key_PageDown:
			self.imageviewer.nextImage_s()
		else:
			QScrollArea.keyReleaseEvent(self, ev)

	def wheelEvent(self, event):
		if not (event.modifiers() & Qt.ControlModifier):
			return super().wheelEvent(event)

		delta = event.angleDelta()
		if delta.isNull() or not delta.y():
			return
		if delta.y() > 0:
			self.zoom(at_cursor=True)
		else:
			self.unzoom(at_cursor=True)

	### public
	@Slot()
	def doNormalZoom(self):
		self.setZoomFactor(1.)

	@Slot()
	def doFitAllZoom(self):
		self.setZoomMode(ZOOM_FITALL)

	@Slot()
	def doFitCutZoom(self):
		self.setZoomMode(ZOOM_FITCUT)

	@Slot()
	def zoom(self, at_cursor=False):
		self.multiplyZoomFactor(1.1, at_cursor)

	@Slot()
	def unzoom(self, at_cursor=False):
		self.multiplyZoomFactor(1 / 1.1, at_cursor)

	def setZoomMode(self, mode, at_cursor=False):
		self.zoomMode = mode
		self._rebuildZoom(at_cursor)

	def setZoomFactor(self, factor, at_cursor):
		self.oldZoomFactor = self.zoomFactor
		self.zoomFactor = factor
		self.setZoomMode(ZOOM_FACTOR, at_cursor)

	def multiplyZoomFactor(self, factor, at_cursor):
		self.setZoomFactor(self.zoomFactor * factor, at_cursor)

	def setFile(self, file):
		self.file = file
		if file.lower().endswith('.gif'):
			self.movie = QMovie(file)
			self.widget().setMovie(self.movie)
			self.movie.finished.connect(self.movie.start)
			self.movie.start()
		else:
			self.movie = None

			img_reader = QImageReader(file)
			img_reader.setAutoTransform(True)
			img = img_reader.read()

			self.originalPixmap = QPixmap.fromImage(img)
			self._rebuildZoom()

	###
	def _rebuildZoom(self, at_cursor=False):
		if self.movie:
			return

		# save relative scroll position to restore it later
		vbar = self.verticalScrollBar()
		hbar = self.horizontalScrollBar()
		vpos = hpos = 0
		if vbar.maximum():
			vpos = vbar.value() / vbar.maximum()
		if hbar.maximum():
			hpos = hbar.value() / hbar.maximum()

		oldScale = self.oldZoomFactor
		scrollbarPos = QPointF(hbar.value(), vbar.value())

		if at_cursor:
			# zoom at cursor algorithm from https://stackoverflow.com/a/32269574/6541288
			gcur = QPointF(QCursor.pos())
			deltaToPos = self.mapFromGlobal(gcur.toPoint()) / oldScale - self.widget().pos() / oldScale
		else:
			deltaToPos = QPointF(self.viewport().rect().center()) / oldScale - QPointF(self.widget().pos()) / oldScale

		if self.zoomMode == ZOOM_FACTOR:
			if self.zoomFactor == 1:
				self._setPixmap(self.originalPixmap)
			else:
				self._setPixmap(self._getScaledPixmap(self.originalPixmap.size() * self.zoomFactor))
		elif self.zoomMode == ZOOM_FITALL:
			newpix = self._getScaledPixmap(self.viewport().size())
			self._setPixmap(newpix)
			self.oldZoomFactor = self.zoomFactor
			self.zoomFactor = newpix.size().width() / float(self.originalPixmap.size().width())
		elif self.zoomMode == ZOOM_FITCUT:
			newpix = self._getScaledPixmap(self.viewport().size(), Qt.KeepAspectRatioByExpanding)
			self._setPixmap(newpix)
			self.oldZoomFactor = self.zoomFactor
			self.zoomFactor = newpix.size().width() / float(self.originalPixmap.size().width())

		def scroll_after_zoom():
			hbar.setValue(int(scrollbarPos.x() + delta.x()))
			vbar.setValue(int(scrollbarPos.y() + delta.y()))

		newScale = self.zoomFactor
		delta = deltaToPos * newScale - deltaToPos * oldScale

		# XXX the pixmap is not fully loaded and displayed yet, so the scrollbars maximum values
		# are not up to date yet, so we have to wait before restoring the relative scroll position
		QTimer.singleShot(0, scroll_after_zoom)

	def _getScaledPixmap(self, size, mode=Qt.KeepAspectRatio):
		return self.originalPixmap.scaled(size, mode, Qt.SmoothTransformation)

	def _setPixmap(self, pixmap):
		self.widget().setPixmap(pixmap)
