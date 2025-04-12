'''
@author: David De Juan
'''

class Node(object):
    
    sep = "/"
    
    def __init__(self, name, parent=None, type=None, dragged=False):
        
        self._name = name
        self._children = []
        self._parent = parent
        self._type = type
        self._path = None
        self._icon = None
        self._tooltip = None
        self._properties = {}
        
        if parent is not None:
            parent.addChild(self)


    def getToolTip(self):
        return self._tooltip
        
    def setToolTip(self, tooltip):
        self._tooltip = tooltip
    
    def getIcon(self):
        return self._icon
    
    
    def setIcon(self, icon):
        self._icon = icon
        

    def addProperty(self, key, value):
        self._properties.update({key: value})
        
        
    def getProperties(self):
        return self._properties
    
    
    def setProperties(self, properties):
        self._properties = properties
    
    
    def getProperty(self, key):
        if key in self._properties.keys():
            return self._properties[key]
        else:
            return None
            
    def updateProperty(self, key, new_value):
        if key in self._properties.keys():
            self._properties[key] = new_value
        else:
            self._properties.update({key: new_value})
    
    
    def deleteAllChildren(self):
        self._children = []
        

    def getType(self):
        return self._type

            
    def setType(self, type):
        self._type = type
            
            
    def typeInfo(self):
        return "NODE"


    def createPath(self):
        path = self._name
        parent = self._parent
        while parent:
            path = parent.name()+"/"+path
            parent = parent._parent
        self._path = path
        return path
    

    def setPath(self, path):
        self._path = path


    def getPath(self):
        return self._path


    def setParent(self, parent):
        if parent != None:
            self._parent = parent
            self._parent.addChild(self)
        else:
            self._parent = None
        
        
    def addChild(self, child):
        self._children.append(child)
        self._children= sorted(self._children, key=lambda kv: kv._name)
        child._parent = self


    def getChildren(self):
        return self._children
        
        
    def insertChild(self, position, child):
        if (position < 0) or (position > len(self._children)):
            return False
        self._children.insert(position, child)
        self._children= sorted(self._children, key=lambda kv: kv._name)
        child._parent = self
        return True

        
    def removeChild(self, position):
        if (position < 0) or (position > len(self._children)):
            return False
        child = self._children.pop(position)
        child._parent = None
        return True


    def name(self):
        return self._name

        
    def setName(self, name):
        self._name = name

        
    def getChildByRow(self, row):
        if (row < len(self._children)) and (row >= 0):
            return self._children[row]
        else:
            return None
    

    def getChildByName(self,name):
        for c in self._children:
            if c._name == name:
                return c
        return None


    def getChildFromPath (self, path):
        child_list = path.split(self.sep)
        if child_list[0] == self.name():
            index = 1
        else:
            index = 0
        child = self.getChildByName(child_list[index])
        for elem in child_list[index+1:]:
            if child:
                child = child.getChildByName(elem)
        return child
    
    
    def childCount(self):
        return len(self._children)

    
    def parent(self):
        return self._parent
    
    
    def row(self):
        if self._parent is not None:
            return self._parent._children.index(self)
        else:
            return 0


    def log(self, tabLevel=-1):
        output     = ""
        tabLevel += 1
        for i in range(tabLevel):
            output += "\t"
        output += "|------" + self._name + "\n"
        for child in self._children:
            output += child.log(tabLevel)
        tabLevel -= 1
        output += "\n"
        return output

        
    def __repr__(self):
        return self.log()