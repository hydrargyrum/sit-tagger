
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os
import taglib

class TagEditor(QListWidget):
	def __init__(self, tagger):
		super(TagEditor, self).__init__()
		
		self.setContextMenuPolicy(Qt.ActionsContextMenu)
		act = QAction('&Create tag', self)
		act.triggered.connect(self._createTag)
		self.addAction(act)
		
		self.itemChanged.connect(self._tagStateChanged)
		
		self.tagger = tagger
		#~ self.root = root
	
	def _createTag(self):
		r = QInputDialog.getText(self, 'Enter a tag name', 'New tag')
		t = str(r[0])
		if not r[1]:
			return
		self.tagger.create_tag(t)
		self.setFile(self.path)
	
	def setFile(self, path):
		self.path = path
		self.clear()
		ftags = self.tagger.get_tags(self.path)
		for t in sorted(self.tagger.all_tags()):
			item = QListWidgetItem(t)
			item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
			if t in ftags:
				item.setCheckState(Qt.Checked)
			else:
				item.setCheckState(Qt.Unchecked)
			self.addItem(item)
	
	@pyqtSlot(QListWidgetItem)
	def _tagStateChanged(self, item):
		if item.checkState() == Qt.Unchecked:
			self.tagger.del_tags(self.path, [str(item.text())])
		else:
			self.tagger.add_tags(self.path, [str(item.text())])
		self.tagger.sync()


class TagChooser(QListWidget):
	changed = pyqtSignal()
	
	def __init__(self, tagger):
		super(TagChooser,self).__init__()
		self.tagger = tagger
		
		self.itemChanged.connect(self.changed)
		for t in sorted(self.tagger.all_tags()):
			item = QListWidgetItem(t)
			item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
			item.setCheckState(Qt.Unchecked)
			self.addItem(item)
	
	def selectedTags(self):
		tags = []
		for i in xrange(self.count()):
			item = self.item(i)
			if item.checkState() == Qt.Checked:
				tags.append(str(item.text()))
		return tags
	
	def matchingFiles(self):
		tags = self.selectedTags()
		
		if not tags:
			return []
		res = set(self.tagger.get_files(tags[0]))
		for t in tags[1:]:
			res &= set(self.tagger.get_files(t))
		res = list(res)
		res.sort()
		return res
