'''
@author: David De Juan
'''
from PySide import QtGui, QtCore
from libs import types


class TreeView(QtGui.QTreeView):
    
    def __init__(self, parent=None, model = None):
        QtGui.QTreeView.__init__(self)
        self.types = types.Types()
        if model:
            self.setModel(model)  
            self.internal_model = model


    def setModel(self, model):
        self.internal_model = model
        QtGui.QTreeView.setModel(self, model)
        
        
    def getModel(self):
        return self.internal_model
    
        
    def mousePressEvent(self, event):
        index = self.indexAt(event.pos());
        if not index.isValid():
            self.clearSelection()
            self.emit(QtCore.SIGNAL("deselected()"))
        QtGui.QTreeView.mousePressEvent(self,event)


    def dropEvent(self, event):
        """On drop, get the target and the dragged item(s)"""      
        if (event.mimeData().hasFormat("application/x-tech.artists.org")):
            source_widget = event.source()
            for index in source_widget.selectedIndexes():
                if index.column() == 0:
                    source_node = source_widget.getModel().getNode(index)
                    dest_node = self.internal_model.getNode(self.indexAt(event.pos()))                    
                    if self.dropIndicatorPosition()==0: #0 means onItem. The item will be dropped on the index
                        if dest_node.name() != self.types.root_name_renders and dest_node.name() != self.types.root_name_stacks:
                            if dest_node.getType()==self.types.node_type_stack:
                                #Stack
                                if source_node.getType() and source_node.getType() == self.types.node_type_char and not source_node.getProperty('isInStack'):
                                    source_node.updateProperty('isInStack', dest_node)
                                if source_node.getType() and source_node.getType() == self.types.node_type_animblock:
                                    for c in source_node._children:
                                        if not c.getProperty('isInStack'):
                                            c.updateProperty('isInStack', dest_node)
                                if source_node.getType() and source_node.getType() == self.types.node_type_shot:
                                    for anim in source_node._children:
                                        for c in anim._children:
                                            if not c.getProperty('isInStack'):
                                                c.updateProperty('isInStack', dest_node)
                                                
                            elif dest_node.getType()==self.types.node_type_render:
                                #Render
                                if source_node.getType() and source_node.getType() == self.types.node_type_char:
                                    found = False
                                    if source_node.getProperty('isInRender'):
                                        for ns in source_node.getProperty('isInRender'):
                                            if dest_node.name() == ns.name():
                                                found = True
                                    if not found:
                                        source_node.getProperty('isInRender').append(dest_node)
                                if source_node.getType() and source_node.getType() == self.types.node_type_animblock:
                                    for c in source_node._children:
                                        found = False
                                        if c.getProperty('isInRender'):
                                            for ns in c.getProperty('isInRender'):
                                                if dest_node.name() == ns.name():
                                                    found = True
                                        if not found:
                                            c.getProperty('isInRender').append(dest_node)
                                if source_node.getType() and source_node.getType() == self.types.node_type_shot:
                                    for anim in source_node._children:
                                        for c in anim._children:
                                            found = False
                                            if c.getProperty('isInRender'):
                                                for ns in c.getProperty('isInRender'):
                                                    if dest_node.name() == ns.name():
                                                        found = True
                                            if not found:
                                                c.getProperty('isInRender').append(dest_node)
        QtGui.QTreeView.dropEvent(self, event)