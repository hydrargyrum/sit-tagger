# SPDX-License-Identifier: WTFPL

import math

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmapCache, QTransform, QPixmap
from PyQt5.QtWidgets import QGraphicsView, QGraphicsItem, QGraphicsScene, QGraphicsPixmapItem


MODE_MOVE = 0
MODE_ZOOM = 1
MODE_ROT = 2


def vectorLength(qp):
	return math.sqrt(qp.x() * qp.x() + qp.y() * qp.y())


class ItemMixin:
	def __init__(self):
		super().__init__()

		self.setFlag(self.ItemIsSelectable, True)
		self.setFlag(self.ItemIsMovable, True)
		self.mode = MODE_MOVE
		self._angle = 0
		self._scale = 1

	def setMode(self, mode):
		self.mode = mode
		if mode == MODE_MOVE:
			self.setFlag(self.ItemIsMovable, True)
		elif mode == MODE_ZOOM:
			self.setFlag(self.ItemIsMovable, False)

	def mousePressEvent(self, ev):
		if self.mode == MODE_MOVE:
			# call directly QGraphicsItem to bypass QGraphicsProxyWidget
			return QGraphicsItem.mousePressEvent(self, ev)
		self.origin = ev.pos()

	def mouseMoveEvent(self, ev):
		if self.mode == MODE_MOVE:
			return QGraphicsItem.mouseMoveEvent(self, ev)

		center = self.transform().map(self.boundingRect().center())
		origToCenter = self.origin - center
		originScale = vectorLength(origToCenter)
		origAngle = math.atan2(origToCenter.y(), origToCenter.x())

		newPt = self.transform().map(ev.pos())
		newToCenter = newPt - center
		newScale = vectorLength(newToCenter)
		newAngle = math.atan2(newToCenter.y(), newToCenter.x())

		# build transform
		t = QTransform()
		t.translate(center.x(), center.y())
		if self.mode == MODE_ROT:
			self._angle = math.degrees(newAngle - origAngle)
		t.rotate(self._angle)

		if self.mode == MODE_ZOOM:
			self._scale = newScale / originScale
		t.scale(self._scale, self._scale)
		t.translate(-center.x(), -center.y())
		self.setTransform(t)


class Image(ItemMixin, QGraphicsPixmapItem):
	def __init__(self, path):
		super().__init__()

		pix = QPixmap(path)
		QPixmapCache.insert(path, pix)

		self.setTransformationMode(Qt.SmoothTransformation)

		self.setPixmap(pix)


class Scene(QGraphicsScene):
	def __init__(self, *args):
		super().__init__(*args)
		self.mode = MODE_MOVE

	def addItem(self, item):
		super().addItem(item)
		if isinstance(item, ItemMixin):
			item.setMode(self.mode)

	def _applyMode(self):
		for item in self.items():
			if isinstance(item, ItemMixin):
				item.setMode(self.mode)

	def setMoveMode(self):
		self.mode = MODE_MOVE
		self._applyMode()

	def setZoomMode(self):
		self.mode = MODE_ZOOM
		self._applyMode()

	def setRotMode(self):
		self.mode = MODE_ROT
		self._applyMode()


class Canvas(QGraphicsView):
	def __init__(self, *args):
		super().__init__(*args)
		self.setScene(Scene(self))

	def addItem(self, item):
		self.scene().addItem(item)

	def keyPressEvent(self, ev):
		if ev.key() == Qt.Key_F1:
			self.scene().setMoveMode()
		elif ev.key() == Qt.Key_F2:
			self.scene().setZoomMode()
		elif ev.key() == Qt.Key_F3:
			self.scene().setRotMode()
		return super().keyPressEvent(ev)
