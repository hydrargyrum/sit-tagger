
import time

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
Signal = pyqtSignal
Slot = pyqtSlot

import thumbnail


class ThumbnailMaker(QObject):
	def __init__(self):
		super(ThumbnailMaker, self).__init__()
		self.queue = []
		self.running = 0

	def addTask(self, path, cb):
		if self.running < 5:
			self._createTask(path, cb)
		else:
			self.queue.append((path, cb))

	def _createTask(self, path, cb):
		proc = QProcess(self)
		proc.cb = cb
		proc.readyReadStandardOutput.connect(self.hasOutput)
		proc.finished.connect(self.finished)
		proc.start('python', ['thumbnail.py', path])
		self.running += 1

	@Slot()
	def hasOutput(self):
		proc = self.sender()
		line = proc.readLine()
		line = unicode(line).strip()
		proc.cb(line)

	@Slot()
	def finished(self):
		self.sender().setParent(None)

		self.running -= 1
		if self.queue:
			p = self.queue.pop()
			self._createTask(*p)


class xThumbnailMaker(QThreadPool):
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
