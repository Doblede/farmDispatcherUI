'''
@author: David De Juan
'''
from PySide import QtGui, QtCore
import math


class NodeItem(QtGui.QGraphicsEllipseItem):
    def __init__(self, name='', node=None, color = [(23, 144, 246, 255),(15, 111, 193, 255)], parent=None):
        QtGui.QGraphicsEllipseItem.__init__(self, parent)
        self._color = color
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        # set move restriction rect for the item
        #self.move_restrict_rect = QtCore.QRectF(20, 20, 200, 200)
        # set item's rectangle
        font = QtGui.QFont("SansSerif", 10)
        font.setStyleHint(QtGui.QFont.Helvetica)
        font.setStretch(100)

        
        self.x_len = len(name)*6.5
        self.setRect(QtCore.QRectF(0, 0, self.x_len, 50))
        self._pos = self.pos()
        self.node = node
        
        '''
        gradient = QtGui.QRadialGradient(50, 50, 50, 50, 50)
        gradient.setColorAt(0, QtGui.QColor.fromRgb(self._color[0][0],self._color[0][1],self._color[0][2],self._color[0][3]))
        gradient.setColorAt(1, QtGui.QColor.fromRgb(self._color[1][0],self._color[1][1],self._color[1][2],self._color[1][3]))
        brush = QtGui.QBrush(gradient)
        self.setBrush(brush)
        '''
        brush = QtGui.QBrush()
        brush.setStyle(QtCore.Qt.SolidPattern)
        brush.setColor(QtGui.QColor.fromRgb(self._color[0][0],self._color[0][1],self._color[0][2],self._color[0][3]))
        self.setBrush(brush)
            
        if node and not node.getProperty('attributeList')['enable']['value']:
            brush = QtGui.QBrush()
            brush.setStyle(QtCore.Qt.HorPattern)
            self.setBrush(brush)

        #self.setBrush(QtGui.QBrush(QtCore.Qt.red, style = QtCore.Qt.HorPattern))
        self.displayText = QtGui.QGraphicsTextItem(name, self)
        self.displayText.setFont(font)
        self.displayText.setDefaultTextColor(QtGui.QColor(QtCore.Qt.black))
        #self.displayText.setPos(self.sceneBoundingRect().center().x()/2, self.sceneBoundingRect().center().y()/2)
        self.displayText.setPos((self.x_len/2)-(self.displayText.boundingRect().width()/2), self.sceneBoundingRect().center().y()/2)
        '''
        pLineEdit = QtGui.QLabel(name)
        pMyProxy = QtGui.QGraphicsProxyWidget(self)
        #pMyProxy.setPos(self.pos())
        pMyProxy.setWidget(pLineEdit)
        '''
        
        
    def setPosition(self, x, y):
        self.setPos(x-(self.x_len/2), y)
        
        
        
    def getNode(self):
        return self.node
    
    '''
    def doPython (self):
        print "self.node",self.node
        pathParent = self.node.parent().getProperty ("attributeList")['path']["value"];
        self.node.getProperty ("attributeList")['path']["value"] = pathParent
        print "path",pystr
        try :
            exec (pystr)
        except :
            print "oups"
    '''
        
    def setColor(self, color):
        self._color = color
        
    
    def setEnable(self, enable):
        if enable:
            brush = QtGui.QBrush()
            brush.setStyle(QtCore.Qt.SolidPattern)
            brush.setColor(QtGui.QColor.fromRgb(self._color[0][0],self._color[0][1],self._color[0][2],self._color[0][3]))
            self.setBrush(brush)
            '''
            gradient = QtGui.QRadialGradient(50, 50, 50, 50, 50)
            gradient.setColorAt(0, QtGui.QColor.fromRgb(self._color[0][0],self._color[0][1],self._color[0][2],self._color[0][3]))
            gradient.setColorAt(1, QtGui.QColor.fromRgb(self._color[1][0],self._color[1][1],self._color[1][2],self._color[1][3]))
            brush = QtGui.QBrush(gradient)
            self.setBrush(brush)
            '''
        else:
            brush = QtGui.QBrush()
            brush.setStyle(QtCore.Qt.HorPattern)
            #brush.setColor(QtGui.QColor.fromRgb(self._color[0][0],self._color[0][1],self._color[0][2],self._color[0][3]))
            self.setBrush(brush)
            '''
            gradient = QtGui.QRadialGradient(50, 50, 50, 50, 50)
            gradient.setColorAt(0, QtGui.QColor.fromRgb(self._color[0][0],self._color[0][1],self._color[0][2],self._color[0][3]))
            gradient.setColorAt(1, QtGui.QColor.fromRgb(self._color[1][0],self._color[1][1],self._color[1][2],self._color[1][3]))
            brush = QtGui.QBrush(gradient)
            brush.setStyle(QtCore.Qt.HorPattern)
            '''
            self.setBrush(brush)
            
            
            
            
            
            
class ArrowItem(QtGui.QGraphicsLineItem):
    def __init__(self, start_item, end_item, parent=None, scene=None):
        super(ArrowItem, self).__init__(parent, scene)

        self.arrow_head = QtGui.QPolygonF()
        self.start_item = start_item
        self.end_item = end_item
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.my_color = QtCore.Qt.black
        self.setPen(QtGui.QPen(self.my_color, 2, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))


    def setColor(self, color):
        self.my_color = color


    def startItem(self):
        return self.start_item


    def endItem(self):
        return self.end_item


    def boundingRect(self):
        extra = (self.pen().width() + 20) / 2.0
        p1 = self.line().p1()
        p2 = self.line().p2()
        return QtCore.QRectF(p1, QtCore.QSizeF(p2.x() - p1.x(), p2.y() - p1.y())).normalized().adjusted(-extra, -extra, extra, extra)


    def shape(self):
        path = super(ArrowItem, self).shape()
        path.addPolygon(self.arrow_head)
        return path


    def updatePosition(self):
        line = QtCore.QLineF(self.mapFromItem(self.start_item, 0, 0), self.mapFromItem(self.end_item, 0, 0))
        self.setLine(line)


    def paint(self, painter, option, widget=None):
        if (self.start_item.collidesWithItem(self.end_item)):
            return

        self.pen().setColor(self.my_color)
        arrow_size = 5.0
        painter.setPen(self.pen())
        painter.setBrush(self.my_color)

        h = QtCore.QPointF(0, self.end_item.boundingRect().height())
        w_start = QtCore.QPointF(self.start_item.boundingRect().width()/2, 0)
        w_end = QtCore.QPointF(self.end_item.boundingRect().width()/2, 0)
        self.setLine(QtCore.QLineF(self.start_item.pos()+w_start, self.end_item.pos()+w_end+h))
        line = self.line()

        angle = math.acos(line.dx() / line.length())
        if line.dy() >= 0:
            angle = (math.pi * 2.0) - angle

        arrowP1 = line.p1() + QtCore.QPointF(math.sin(angle + math.pi / 3.0) * arrow_size, math.cos(angle + math.pi / 3) * arrow_size)
        arrowP2 = line.p1() + QtCore.QPointF(math.sin(angle + math.pi - math.pi / 3.0) * arrow_size, math.cos(angle + math.pi - math.pi / 3.0) * arrow_size)

        self.arrow_head.clear()
        for point in [line.p1(), arrowP1, arrowP2]:
            self.arrow_head.append(point)

        painter.drawLine(line)
        painter.drawPolygon(self.arrow_head)
        '''
        if self.isSelected():
            #esto es para seleccionar la flecha
            painter.setPen(QtGui.QPen(self.my_color, 1, QtCore.Qt.DashLine))
            myLine = QtCore.QLineF(line)
            myLine.translate(0, 4.0)
            painter.drawLine(myLine)
            myLine.translate(0,-8.0)
            painter.drawLine(myLine)
        '''