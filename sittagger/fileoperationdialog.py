# SPDX-License-Identifier: WTFPL

from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QProgressDialog


class FileOperationProgressDialog(QProgressDialog):
	def __init__(self, parent):
		super().__init__(parent)
		self.setAutoReset(False)
		self.setAutoClose(False)
		self.setMinimumDuration(0)
		self.setModal(True)
		self.finished.connect(self.deleteLater)
		self.op = None

	def setOp(self, op):
		self.op = op
		self.op.processing.connect(self.onProgress)
		self.op.started.connect(self.exec_)
		self.op.finished.connect(self.accept)
		self.canceled.connect(self.op.cancel)

	@Slot(str, int, int)
	def onProgress(self, name, current, total):
		self.setLabelText(name)
		self.setValue(current * 100 // total)

	def start(self):
		self.show()
		self.open()
		self.op.start()

	def showEvent(self, ev):
		super().showEvent(ev)
		if self.op.isFinished():
			self.accept()
