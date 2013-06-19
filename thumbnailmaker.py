
try:
	from PyQt4.QtCore import *
	from PyQt4.QtGui import *
	Signal = pyqtSignal
	Slot = pyqtSlot
except ImportError:
	from PySide.QtCore import *
	from PySide.QtGui import *
import time

import thumbnail


class ThumbnailMaker(QThreadPool):
	def __init__(self):
		super(ThumbnailMaker, self).__init__()
		self.tasks = {}
		self.tasksMutex = QMutex()
		#~ self.tasksExistCondition = QWaitCondition()
	
	def createThumbnailTask(self, path):
		self.tasksMutex.lock()
		try:
			if path not in self.tasks:
				task = ThumbnailMaker.Task(path)
				task.emitter.thumbnailDone.connect(self._finish)
				self.start(task)
				self.tasks[path] = task
			else:
				task = self.tasks[path]
			return task
		finally:
			self.tasksMutex.unlock()
	
	@Slot(str)
	def _finish(self, path):
		self.tasksMutex.lock()
		try:
			if path in self.tasks:
				del self.tasks[path]
		finally:
			self.tasksMutex.unlock()
	
	def cancelTask(self, path):
		self.tasksMutex.lock()
		try:
			if path in self.tasks:
				self.tasks[path].abort = True
				del self.tasks[path]
		finally:
			self.tasksMutex.unlock()

	class Task(QRunnable):
		class Emitter(QObject):
			thumbnailDone = Signal(str)
			
			def emitItDamnit(self, p):
				self.thumbnailDone.emit(p)
		
		def __init__(self, path):
			QRunnable.__init__(self)
			self.emitter = ThumbnailMaker.Task.Emitter()
			
			self.path = path
			self.isFinished = False
			self.result = None
			self.cancelMutex = QMutex()
			self.abort = False
		
		def run(self):
			abort = self.abort
			if not self.abort:
				res = thumbnail.gen_image_thumbnail(self.path)
				if res:
					self.emitter.emitItDamnit(res)
					self.result = res
			self.isFinished = True

maker = ThumbnailMaker()
