'''
@author: David De Juan
'''
from PySide import QtGui, QtCore
import copy

class TreeGraphicView(QtGui.QGraphicsView):
    def __init__(self, scene=None, parent=None):
        QtGui.QGraphicsView.__init__(self, scene, parent)
        self._parent = parent
        self._scene = scene
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setRenderHint(QtGui.QPainter.TextAntialiasing)
        self.setSceneRect(QtCore.QRectF(20, 20, 200, 200))
        
        # Used for panning
        self.mouse_press_pos = QtCore.QPointF()
        self.scroll_bar_values_on_mouse_press = QtCore.QPointF()
        self.alt = False
        self.panning = False
        
        #self.scrollHorizontalBar().hide() 
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        
    def contextMenuEvent(self, event):
        selected_l = self._scene.selectedItems()
        stack =  self._parent.stack_model.getNode(self._parent.stack_view.currentIndex()) 
        
        if selected_l:
            menu = QtGui.QMenu()
            menu.addAction(QtGui.QAction('Toggle enable', menu))
            itemMenu = menu.exec_(QtGui.QCursor.pos())
            if itemMenu and itemMenu.text() == 'Toggle enable':
                for sl in selected_l:
                    if type(sl).__name__ == 'NodeItem':
                        sel = sl.getNode()
                        if stack.getType() == self._parent.types.node_type_char:
                            #If the stack selected is a char, we load the overrides
                            #self._parent.overrideLabel(label)
                            att_list = None
                            if stack.getProperty(sel.name()) and 'attributeList' in stack.getProperty(sel.name()).keys():
                                #get the attributes overrides for the char 
                                att_list = stack.getProperty(sel.name())['attributeList']
                                if 'enable' not in att_list.keys():
                                    #if the property didn't have override, we add the property
                                    att_list.update({'enable': copy.deepcopy(sel.getProperty('attributeList'))['enable']})
                            else:
                                #if no char overrides, we create the first override
                                att_list = {'enable': copy.deepcopy(sel.getProperty('attributeList'))['enable']}
                        else:
                            #If not we load the node selected properties
                            att_list = copy.deepcopy(sel.getProperty('attributeList'))
                        if att_list and 'enable' in att_list.keys():
                            att_list['enable']['value'] = not att_list['enable']['value']
                        #We change the property value
                        if stack.getType() == self._parent.types.node_type_char:
                            #If the stack selected is a char, we save the overrides
                            dict = {'attributeList': att_list}
                            stack.updateProperty(sel.name(), dict)
                            sl.setEnable(bool(att_list['enable']['value']))
                        else:
                            #save the properties in the node
                            sel.updateProperty('attributeList', att_list)
                            sl.setEnable(bool(att_list['enable']['value']))
                        #Refresh the display properties
                        self._parent.displayProperties(sel)
                    

        
    def wheelEvent(self, event):
        factor = 1.41 ** (-event.delta() / 240.0)
        self.scale(factor, factor)
        

    # Commenting out the following mouse events will make the node movable and obviously disable panning
    def mouseMoveEvent(self, event):
        if self.panning and not self.mouse_press_pos.isNull():
            self.horizontalScrollBar().setValue(self.scroll_bar_values_on_mouse_press.x() - event.pos().x() + self.mouse_press_pos.x())
            self.verticalScrollBar().setValue(self.scroll_bar_values_on_mouse_press.y() - event.pos().y() + self.mouse_press_pos.y())
            self.horizontalScrollBar().update()
            self.verticalScrollBar().update()
            event.accept()
        else:
            QtGui.QGraphicsView.mouseMoveEvent(self, event)
        
        
    def mousePressEvent(self, event):
        # Panning
        if event.button() == QtCore.Qt.MidButton and self.alt and not self.panning:
            self.mouse_press_pos = QtCore.QPointF(event.pos())
            self.scroll_bar_values_on_mouse_press.setX(self.horizontalScrollBar().value())
            self.scroll_bar_values_on_mouse_press.setY(self.verticalScrollBar().value())
            self.panning = True
            event.accept()
        else:
            QtGui.QGraphicsView.mousePressEvent(self, event)
            
        
    def mouseReleaseEvent(self, event):
        if self.panning:
            self.mouse_press_pos = QtCore.QPointF()
            self.panning = False
            event.accept()
        else:
            QtGui.QGraphicsView.mouseReleaseEvent(self, event)
    
    
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Alt:
            self.alt = True
            event.accept()
            
            
    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Alt:
            self.alt = False
            event.accept()