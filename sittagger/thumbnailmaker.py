# SPDX-License-Identifier: WTFPL

from collections import OrderedDict
import sys

from PyQt5.QtCore import QObject, pyqtSlot as Slot, pyqtSignal as Signal, QProcess, QThread


class ThumbnailMaker(QObject):
	done = Signal(str, str)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.queue = OrderedDict()
		self.running = 0
		self.queue_max = QThread.idealThreadCount()

	def addTask(self, path):
		if self.running < self.queue_max:
			self._createTask(path)
		else:
			self.queue[path] = None

	def cancelTask(self, path):
		try:
			del self.queue[path]
		except KeyError:  # maybe task is already processed
			pass

	def reprioritizeTask(self, path):
		try:
			self.queue.move_to_end(path, last=False)
		except KeyError:  # maybe task is already processed
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
			p, _ = self.queue.popitem(last=False)
			self._createTask(p)


maker = ThumbnailMaker()
