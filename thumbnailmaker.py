
from PyQt5.QtCore import QObject, pyqtSlot as Slot, pyqtSignal as Signal, QProcess


class ThumbnailMaker(QObject):
	done = Signal(unicode, unicode)

	def __init__(self, *args, **kwargs):
		super(ThumbnailMaker, self).__init__(*args, **kwargs)
		self.queue = []
		self.running = 0

	def addTask(self, path):
		if self.running < 5:
			self._createTask(path)
		else:
			self.queue.append(path)

	def _createTask(self, path):
		proc = QProcess(self)

		proc.input = path
		proc.readyReadStandardOutput.connect(self.hasOutput)
		proc.finished.connect(self.finished)
		proc.start('python', ['-m', 'vignette', path])
		self.running += 1

	@Slot()
	def hasOutput(self):
		proc = self.sender()
		line = proc.readLine()
		line = unicode(line).strip()
		self.done.emit(proc.input, line)

	@Slot()
	def finished(self):
		proc = self.sender()
		proc.deleteLater()

		self.running -= 1
		if self.queue:
			p = self.queue.pop()
			self._createTask(p)


maker = ThumbnailMaker()
