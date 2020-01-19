
import sys

from PyQt5.QtCore import QObject, pyqtSlot as Slot, pyqtSignal as Signal, QProcess, QThread


class ThumbnailMaker(QObject):
	done = Signal(str, str)

	def __init__(self, *args, **kwargs):
		super(ThumbnailMaker, self).__init__(*args, **kwargs)
		self.queue = []
		self.running = 0
		self.queue_max = QThread.idealThreadCount()

	def addTask(self, path):
		if self.running < self.queue_max:
			self._createTask(path)
		else:
			self.queue.append(path)

	def cancelTask(self, path):
		try:
			self.queue.remove(path)
		except ValueError:  # maybe task is already processed
			pass

	def _createTask(self, path):
		proc = QProcess(self)

		proc.input = path
		proc.readyReadStandardOutput.connect(self.hasOutput)
		proc.finished.connect(self.finished)
		proc.start(sys.executable, ['-m', 'vignette', path])
		self.running += 1

	@Slot()
	def hasOutput(self):
		proc = self.sender()
		line = proc.readLine()
		line = bytes(line).decode('utf-8').strip()
		self.done.emit(proc.input, line)

	@Slot()
	def finished(self):
		proc = self.sender()
		proc.deleteLater()

		self.running -= 1
		if self.queue:
			p = self.queue.pop(0)
			self._createTask(p)


maker = ThumbnailMaker()
