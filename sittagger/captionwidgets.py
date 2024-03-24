# SPDX-License-Identifier: WTFPL

from PyQt6.QtCore import Qt, pyqtSignal as Signal, pyqtSlot as Slot
from PyQt6.QtWidgets import QLineEdit, QTextEdit, QWidget

from .captiontools import tags_to_caption, extract_tags_from_caption


class CaptionEditor(QLineEdit):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.db = None
		self.path = None

		self.returnPressed.connect(self._on_validate)

	def setDb(self, db):
		self.db = db

	def setFile(self, path):
		raise NotImplementedError()
		self.path = path
		caption = self.db.get_caption(path)
		if caption:
			self.setText(caption)
			return

		tags = self.db.get_tags(path)
		caption = tags_to_caption(tags, "")
		self.setText(caption)

	@Slot()
	def _on_validate(self):
		caption = self.text()
		self.db.set_caption(self.path, caption)
		return
		tags = extract_tags_from_caption(caption)
		self.db.set_caption(caption)
		self.db.set_tags(self.path, tags)


class CaptionTextEditor(QTextEdit):
	returnPressed = Signal()
	modificationChanged = Signal(bool)

	def __init__(self, *args, **kwargs):
		super().__init__()
		self.document().modificationChanged.connect(self.modificationChanged)

	def setText(self, text):
		super().setText(text)
		self.document().setModified(False)

	def setModified(self, b):
		self.document().setModified(b)

	def keyReleaseEvent(self, ev):
		if ev.key() == Qt.Key.Key_Return and ev.modifiers() == Qt.KeyboardModifier.ControlModifier:
			self.returnPressed.emit()
		else:
			super().keyReleaseEvent(ev)


class CaptionEditorWidget(QWidget):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
	# 	self.editor = QLineEdit()
	# 	self.button = QToolButton()
	# 	self.setLayout(QHBoxLayout())
	# 	self.layout().addWidget(self.editor)
	# 	self.layout().addWidget(self.button)

	@property
	def captionEdit(self):
		return self.findChild(QWidget, "captionEdit")

	@property
	def captionSaveButton(self):
		return self.findChild(QWidget, "captionSaveButton")

	def init_sigs(self):
		self.captionSaveButton.clicked.connect(self._on_validate)
		self.captionEdit.returnPressed.connect(self._on_validate)
		self.captionEdit.modificationChanged.connect(self._on_edit)

	def setDb(self, db):
		self.db = db

	def setFiles(self, paths):
		if len(paths) != 1:
			self.captionEdit.setText("")
			self.captionEdit.setEnabled(False)
			self.captionSaveButton.setEnabled(False)
			return

		self.captionEdit.setEnabled(True)
		self.paths = paths
		caption = self.db.get_caption(paths[0])
		if caption:
			self.captionEdit.setText(caption)
			self.captionSaveButton.setEnabled(False)
			return

		# bad
		tags = self.db.find_tags_by_file(paths[0])
		caption = tags_to_caption(tags, "")
		self.captionEdit.setText(caption)
		self.captionSaveButton.setEnabled(False)

	@Slot(bool)
	def _on_edit(self, can_undo):
		self.captionSaveButton.setEnabled(can_undo)

	@Slot()
	def _on_validate(self):
		with self.db:
			for path in self.paths:
				self.db.set_caption(path, self.captionEdit.toPlainText().strip() or None)
		self.captionSaveButton.setEnabled(False)
		self.captionEdit.setModified(False)
