'''
@author: David De Juan
'''
from PySide import QtGui, QtCore
import databox
import sys
from libs import types, ui_utils


class Model(QtCore.QAbstractItemModel):
    
    def __init__(self, root, header = "", parent = None):
        QtCore.QAbstractItemModel.__init__(self, parent)
        self._root_node = root
        self._parent = parent
        self._header = [header]
        self.types = types.Types()
        self._columns_number = 1
        self._columns_list = ["Name"]
        
        
    def getRootNode(self):
        return self._root_node
    
    
    def setRoot(self, root, create_upper_node = False):
        if create_upper_node:
            new_root = databox.Node("root")
            new_root.addChild(root)
            self._root_node = new_root
        else:
            self._root_node = root
        
        
    def refreshView(self, expand_all=False):
        if "Tree" in type(self._parent).__name__:
            #All the expanded nodes are stored
            nodestate = list ()
            expanded = list ()
            for index in self.persistentIndexList():
                if expand_all or self._parent.isExpanded(index):
                    node = index.internalPointer ()
                    expanded.append(node)
                    nodestate.append([index.data(QtCore.Qt.DisplayRole),node.name()])
        self.reset()
        if "Tree" in type(self._parent).__name__:
            #The nodes that were expanded are expanded
            for item, name in nodestate :
                items = self.match (self.index(0, 0, QtCore.QModelIndex()),QtCore.Qt.DisplayRole,item,hits = -1, flags = QtCore.Qt.MatchRecursive)
                for i in items :
                    if name == i.internalPointer().name():
                        self._parent.setExpanded(i,True)


        
    def rowCount(self, parent):
        if not parent.isValid():
            parentNode = self._root_node
        else:
            parentNode = parent.internalPointer()
        return parentNode.childCount()

        
    def addColumn(self, column_name, attribute):
        self._header.append(column_name)
        self._columns_list.append(attribute)
        self._columns_number = self._columns_number+1
        
        
    def columnCount(self, parent):
        return self._columns_number
        
        
    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            return self._header[section]



    def data(self, index, role):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                if node.getIcon():
                    return ui_utils.reloadInterfaceIcons(None, node.getIcon(),h=15)
        if role == QtCore.Qt.ToolTipRole:
            if index.column() == 0:
                return node.getToolTip()
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if index.column() == 0:
                return node.name()
            else:
                if node.getType() == self.types.node_type_char:
                    attr= self._columns_list[index.column()]
                    property = node.getProperty(attr)
                    if property:
                        if type(property).__name__ == 'list':
                            renders = ''
                            for p in property:
                                if renders:
                                    renders = renders+', '+p.name()
                                else:
                                    renders = p.name()
                            return renders
                        else:
                            return property.name()
                    else:
                        return 'None'
                    
        if role == QtCore.Qt.FontRole:
            if index.column() == 0:
                if node.getType() == self.types.node_type_animblock:
                    boldFont = QtGui.QFont()
                    boldFont.setBold(True)
                    boldFont.setPixelSize(13)
                    return boldFont  
                
                if node.getType() == self.types.node_type_shot:
                    boldFont = QtGui.QFont()
                    boldFont.setBold(True)
                    boldFont.setPixelSize(15)
                    return boldFont 

        if role == QtCore.Qt.TextColorRole:
            if index.column() == 0:
                if node.getProperty('isInStack') and self._root_node.name() == self.types.root_name_shot:
                    return QtGui.QBrush(QtCore.Qt.blue)
                if node.getType() == self.types.node_type_render and not node.getProperty('attributeList')['enable']['value']:
                    return QtGui.QBrush(QtCore.Qt.red)
 

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if index.isValid():
            if role == QtCore.Qt.EditRole:
                node = index.internalPointer()
                node.setName(value)
                return True
        return False


    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        node = self.getNode(index)
        parentNode = node.parent()
        if not parentNode or parentNode == self._root_node:
            return QtCore.QModelIndex()
        return self.createIndex(parentNode.row(), 0, parentNode)

        
        
    def index(self, row, column, parent):
        parentNode = self.getNode(parent)
        childItem = parentNode.getChildByRow(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QtCore.QModelIndex()
        
        
    def getNode(self, index):
        if index.isValid():
            node = index.internalPointer()
            if node:
                return node
        return self._root_node
        
        
    def flags(self, index):
        '''Valid items are selectable, editable, and drag and drop enabled. Invalid indices (open space in the view)
        are also drop enabled, so you can drop items onto the top level.
        '''
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled
         
        else:
            node = index.internalPointer()
            if node.getType() and (node.getType() == self.types.node_type_stack or node.getType() == self.types.node_type_render):
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsDragEnabled |\
                       QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
            else:
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsDragEnabled |\
                       QtCore.Qt.ItemIsSelectable
                       
        
    def supportedDropActions( self ):
        '''Items can be moved and copied (but we only provide an interface for moving items in this example.'''
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction
        
        
    def mimeTypes(self):
        '''
        types = QtCore.QStringList( 'application/x-pynode-item-instance' )
        return types
        '''
        return [ "application/x-tech.artists.org" ]
     

        
    def nodeFromIndex( self, index ):
        '''Returns the TreeItem instance from a QModelIndex.'''
        return index.internalPointer() if index.isValid() else self._root_node
        
        
    def mimeData(self, indexes):
        mimedata = QtCore.QMimeData()
        encodedData = QtCore.QByteArray()
        stream = QtCore.QDataStream(encodedData, QtCore.QIODevice.WriteOnly)
        
        for index in indexes:
            if not index.isValid():
                continue
            elif index.column() == 0:
                node = index.internalPointer()           
                
                if node._type and node._type == self.types.node_type_char:
                    node.createPath()
                    stream.writeQVariant(node)
    
                if node._type and node._type == self.types.node_type_animblock:
                    for c in node._children:
                        c.createPath()
                        stream.writeQVariant(c)
    
                if node._type and node._type == self.types.node_type_shot:
                    for anim in node._children:
                        for c in anim._children:
                            c.createPath()
                            stream.writeQVariant(c)
            
        mimedata.setData("application/x-tech.artists.org", encodedData)
        return mimedata


    def dropMimeData(self, data, action, row, column, parent):
        if action == QtCore.Qt.MoveAction:
            # Where are we inserting?
            begin_row = 0
            if row != -1:
                #print "ROW IS NOT -1, meaning inserting inbetween, above or below an existing node"
                begin_row = row
                return False
            elif parent.isValid():
                #print "PARENT IS VALID, inserting ONTO something since row was not -1, begin_row becomes 0 because we want to insert it at the begining of this parents children"
                begin_row = 0
            else:
                #print "PARENT IS INVALID, inserting to root, can change to 0 if you want it to appear at the top"
                begin_row = self.rowCount(QtCore.QModelIndex())
                return False

            # create a read only stream to read back packed data from our QMimeData
            encodedData = data.data("application/x-tech.artists.org")
            stream = QtCore.QDataStream(encodedData, QtCore.QIODevice.ReadOnly)

            # decode all our data back into drop_list
            drop_list = []
            while not stream.atEnd():
                node = stream.readQVariant()  # extract
                # add the python object that was wrapped up by a QVariant back in our mimeData method
                drop_list.append(node) 

            # This will insert new items, so you have to either update the values after the insertion or write your own method to receive our decoded drop_list objects.
            parent_node = self.nodeFromIndex(parent)

            if parent_node.name() == self.types.root_name_stacks and drop_list:
                number_inserts = 0
                for drop in drop_list:
                    if not drop.getProperty('isInStack'):
                        number_inserts = number_inserts+1
                if number_inserts:
                    #We create a new stack child
                    row = parent_node.childCount()+1
                    parent_node = databox.Node("Stack %02d" % (row), parent_node, self.types.node_type_stack)
                    begin_row = 0
                    '''
                    index = self.index(row-1, 0, QtCore.QModelIndex())
                    self._parent.setCurrentIndex(index)
                    '''
            elif parent_node.name() == self.types.root_name_renders and drop_list:
                #We create a new render child
                row = parent_node.childCount()+1
                parent_node = databox.Node("Render Scene %02d" % (row), parent_node, self.types.node_type_render)
                begin_row = 0
            elif  parent_node.getType() == self.types.node_type_char and drop_list:
                return False
            for drop in drop_list:
                # If you don't have your own insertion method and stick with the insertRows above, this is where you would update the values using our drop_list.
                if self._root_node.name() == self.types.root_name_stacks:
                    #Stacks
                    if not drop.getProperty('isInStack'):
                        parent_node.insertChild(begin_row, drop)
                        begin_row+=1
                elif self._root_node.name() == self.types.root_name_renders:
                    #Renders
                    found = False
                    if drop.getProperty('isInRender'):
                        for ns in drop.getProperty('isInRender'):
                            if parent_node.name() == ns.name():
                                found = True
                    if not found:
                        parent_node.insertChild(begin_row, drop)
                        begin_row+=1
                else:
                    parent_node.insertChild(begin_row, drop)
                    begin_row+=1
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"), parent, parent)
        self.refreshView()
        return True
        
        
        
    def setData(self, index, value, role = QtCore.Qt.EditRole):
        if role == QtCore.Qt.EditRole:
            node = index.internalPointer()
            node.setName(value)
            self.dataChanged.emit(index, index)
        return True


    #=====================================================#
    #INSERTING & REMOVING
    #=====================================================#
    def insertRows(self, position, rows, parent=QtCore.QModelIndex()):
        parentNode = self.getNode(parent)
        self.beginInsertRows(parent, position, position + rows - 1)
        for row in range(rows):
            childCount = parentNode.childCount()
            childNode = databox.Node("untitled" + str(childCount))
            success = parentNode.insertChild(position, childNode)
        self.endInsertRows()
        return success

        
    def removeRow(self, position, parent_index):
        return self.removeRows(position, 1, parent_index)
        

    def removeRows(self, position, row, parent_index=QtCore.QModelIndex()):
        '''
        parent_node = self.nodeFromIndex(parent_index)
        for pos in range(row):
            node = parent_node.getChildByRow(pos+position)
            if node.getType() and node.getType() == self.types.node_type_char and not node.isDragged():
                #node.setDragged(True)
                pass
    
            if node.getType() and node.getType() == self.types.node_type_animblock:
                for c in node._children:
                    if not c.isDragged():
                        #c.setDragged(True)
                        pass
    
            if node.getType() and node.getType() == self.types.node_type_shot:
                for anim in node._children:
                    for c in anim._children:
                        if not c.isDragged():
                            #c.setDragged(True)
                            pass
        '''
        return True


    def removeRow(self, position, parent_index):
        return self.removeRows(position, 1, parent_index)
        