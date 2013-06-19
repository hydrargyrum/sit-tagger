
try:
	from PyQt4.QtCore import *
	from PyQt4.QtGui import *
	Signal = pyqtSignal
	Slot = pyqtSlot
except ImportError:
	from PySide.QtCore import *
	from PySide.QtGui import *

from tagwidgets import TagEditor

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
	def __init__(self, tagger):
		super(ImageViewer, self).__init__()
		
		self.tagger = tagger
		self.currentIndex = -1
		self.files = []
		
		self._init_widgets()
		
	def _init_widgets(self):
		self.labimg = QLabel()
		self.labimg.setMouseTracking(True)

		#self.toolbar = AutoHideToolBar()
		self.toolbar = QToolBar()
		self.addToolBar(self.toolbar)
		self.toolbar.hide()
		self.toolbar.addAction('Z 1:1').triggered.connect(self.doNormalZoom)
		self.toolbar.addAction('Z Fit').triggered.connect(self.doFitAllZoom)
		self.toolbar.addAction('Z FitExp').triggered.connect(self.doFitCutZoom)
		self.toolbar.addAction('Z x1.5').triggered.connect(self.zoom)
		self.toolbar.addAction('Z /1.5').triggered.connect(self.unzoom)

		self.toolbar.addAction('Copy tags').triggered.connect(self.copyPreviousTags)

		self.fullscreenAction = self.toolbar.addAction('Fullscreen')
		self.fullscreenAction.setCheckable(True)
		self.fullscreenAction.toggled.connect(self.setFullscreen)

		self.navPrevAction = act = self.toolbar.addAction('Prev')
		act.setShortcut(QKeySequence(Qt.Key_Backspace))
		act.triggered.connect(self.prevFile)
		self.navNextAction = act = self.toolbar.addAction('Next')
		act.setShortcut(QKeySequence(Qt.Key_Space))
		act.triggered.connect(self.nextFile)
		#~ act.setShortcutContext(Qt.WidgetWithChildrenShortcut)

		self.tageditor = TagEditor(self.tagger)
		self.docktagger = AutoHideDock()
		self.docktagger.setWidget(self.tageditor)
		self.addDockWidget(Qt.LeftDockWidgetArea, self.docktagger)
		self.docktagger.hide()

		self.scrollview = ImageViewerCenter(self.labimg)
		self.scrollview.installEventFilter(self) ### !
		self.setCentralWidget(self.scrollview)

		self.scrollview.topZoneEntered.connect(self.toolbar.show)
		self.scrollview.topZoneLeft.connect(self.toolbar.hide)
		self.scrollview.leftZoneEntered.connect(self.docktagger.show)
		self.scrollview.leftZoneLeft.connect(self.docktagger.hide)

		#~ self.setWindowState(self.windowState() | Qt.WindowMaximized)

		'''
		self.qtagwl = QListWidget()
		self.qtagwl.setParent(self)
		self.qtagwl.hide()
		#self.qtagwl.setFixedSize(self.qtagwl.minimumSizeHint())
		self.qtagwl.setFrameShape(QFrame.NoFrame)
		self.qtagwl.setStyleSheet('QListWidget{background-color: rgba(255,255,255,200);}\n *{background-color:rgba(0,255,255,255);}')
		self.qtagwl.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
		
		self.qthtimer = QTimer()
		self.connect(self.qthtimer, SIGNAL('timeout()'), self.qtaghide)
		'''

	def doNormalZoom(self):
		self.scrollview.setZoomFactor(1.)

	def doFitAllZoom(self):
		self.scrollview.setZoomMode(ZOOM_FITALL)

	def doFitCutZoom(self):
		self.scrollview.setZoomMode(ZOOM_FITCUT)

	def zoom(self):
		self.scrollview.multiplyZoomFactor(1.5)

	def unzoom(self):
		self.scrollview.multiplyZoomFactor(1/1.5)

	def spawn(self, files, currentFile):
		self.files = files
		self.currentIndex = files.index(currentFile)
		
		self.showFile(currentFile)
		if self.isHidden():
			#~ self.setWindowState(self.windowState() | Qt.WindowMaximized)
			#~ self.show()
			self.fullscreenAction.setChecked(True)
			#~ self.showMaximized()
		else:
			self.show()
	
	def showFile(self, file):
		self.tageditor.setFile(file)
		self.scrollview.setFile(file)
	
	def eventFilter(self, sview, ev):
		if ev.type() == QEvent.KeyPress:
			if ev.key() == Qt.Key_Escape:
				self.fullscreenAction.setChecked(False)
				return True
			elif ev.key() in [Qt.Key_PageUp, Qt.Key_Backspace]: # qactions
				self.prevFile()
				return True
			elif ev.key() in [Qt.Key_PageDown, Qt.Key_Space]:
				self.nextFile()
				return True
		return super(ImageViewer, self).eventFilter(sview, ev)
	
	def copyPreviousTags(self):
		tags = self.tagger.get_tags(self.files[self.currentIndex - 1])
		self.tagger.set_tags(self.files[self.currentIndex], tags)
		self.tagger.sync()
		self.tageditor.setFile(self.files[self.currentIndex])
		
	
	def setFullscreen(self, full):
		#~ print 'OMG', full
		if full:
			#~ self.setWindowState(self.windowState() | Qt.WindowFullScreen)
			self.showFullScreen()
		else:
			#~ self.setWindowState(self.windowState() & ~Qt.WindowFullScreen)
			self.showNormal()

	def prevFile(self):
		if self.currentIndex > 0:
			self.currentIndex -= 1
			self.showFile(self.files[self.currentIndex])
	
	def nextFile(self):
		if self.currentIndex < len(self.files) - 1:
			self.currentIndex += 1
			self.showFile(self.files[self.currentIndex])
		
	#~ def resizeEvent(self, ev):
		#~ QMainWindow.resizeEvent(self, ev)
		#~ if self.zoomMode in (1,2):
			#~ self._redraw()


class ImageViewerCenter(QScrollArea):
	topZoneEntered = Signal()
	topZoneLeft = Signal()
	leftZoneEntered = Signal()
	leftZoneLeft = Signal()

	def __init__(self, imgWidget):
		QScrollArea.__init__(self)
		self.zoomMode = ZOOM_FACTOR
		self.zoomFactor = 1
		self.moving = None

		self.setWidget(imgWidget)

		imgWidget.setAlignment(Qt.AlignCenter)
		self.setAlignment(Qt.AlignCenter)
		self.setMouseTracking(True)
		self.setFrameShape(self.NoFrame)
		self.setWidgetResizable(True)
		pal = QPalette()
		pal.setColor(QPalette.Window, Qt.black)
		self.setPalette(pal)

		self.leftZone = False
		self.topZone = False

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
			newLeft = (ev.x() < 30)
			if newLeft and not self.leftZone:
				self.leftZoneEntered.emit()
			elif self.leftZone and not newLeft:
				self.leftZoneLeft.emit()
			self.leftZone = newLeft

			newTop = (ev.y() < 30)
			if newTop and not self.topZone:
				self.topZoneEntered.emit()
			elif self.topZone and not newTop:
				self.topZoneLeft.emit()
			self.topZone = newTop

	def resizeEvent(self, ev):
		super(ImageViewerCenter, self).resizeEvent(ev)
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

	def setZoomMode(self, mode):
		self.zoomMode = mode
		self._rebuildZoom()

	def setZoomFactor(self, factor):
		self.zoomFactor = factor
		self.setZoomMode(ZOOM_FACTOR)

	def multiplyZoomFactor(self, factor):
		self.setZoomFactor(self.zoomFactor * factor)

	def _rebuildZoom(self):
		if self.zoomMode == ZOOM_FACTOR:
			if self.zoomFactor == 1:
				self._setPixmap(self.fullPix)
			else:
				self._setPixmap(self._scaledFull(self.fullPix.size() * self.zoomFactor))
		elif self.zoomMode == ZOOM_FITALL:
			newpix = self._scaledFull(self.viewport().size())
			self._setPixmap(newpix)
			self.zoomFactor = newpix.size().width() / float(self.fullPix.size().width())
		elif self.zoomMode == ZOOM_FITCUT:
			newpix = self._scaledFull(self.viewport().size(), Qt.KeepAspectRatioByExpanding)
			self._setPixmap(newpix)
			self.zoomFactor = newpix.size().width() / float(self.fullPix.size().width())
	
	def _scaledFull(self, size, mode=Qt.KeepAspectRatio):
		return self.fullPix.scaled(size, mode, Qt.SmoothTransformation)
	
	def _setPixmap(self, pixmap):
		self.widget().setPixmap(pixmap)
	
	def setFile(self, file):
		self.file = file
		self.fullPix = QPixmap(file)
		#~ self.widget().setPixmap()
		self._rebuildZoom()

