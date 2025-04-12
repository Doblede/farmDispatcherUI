'''
@author: David De Juan
'''
from PySide import QtCore
from PySide import QtGui
from PySide import QtUiTools
import sys, os, copy
import model, databox, tree_view, tree_graphic_view, node_item
from libs import config_logic, types, export_data, ui_utils, export_statistics
import config_win, create_stack_win
from random import randint
import json
            

class DispatcherUI(QtGui.QWidget):

    def __init__(self, parent=None):
        super(DispatcherUI, self).__init__(parent)
        loader = QtUiTools.QUiLoader()
        uiFile = QtCore.QFile('./gui/main_win.ui')
        uiFile.open(QtCore.QFile.ReadOnly)
        self.main_window = loader.load(uiFile)
        self.main_window.setWindowTitle("Farm Dispatcher")
        self.main_window.show()
        self.initializeWindow()


    ############
    # UI UTILS #
    ############     
    def clearViews(self, breakdown=True, stack=True, render=True, tree=True, properties=True, search=False):
        #Depending on the flags, it cleans the specific views
        if breakdown:
            self.breakdown_root_node.deleteAllChildren()
            self.model_breakdown.refreshView()
        if stack:
            #load stacks from selected pref
            trees_dict = self.config.getPrefTrees(self.main_window.prefs_combo.currentText())
            self.loadStacks(trees_dict)
        if render:
            #load renders from selected pref
            render_dict = self.config.getPrefRender(self.main_window.prefs_combo.currentText())
            self.loadRenders(render_dict)
        if tree:
            #Clear tree view
            self.stack_selected_label.setText('')
            self.tree_combo_box.clear()
            self.tree_scene.clear()
        if properties:
            #Clear the nodes panel
            ui_utils.clearLayout(self.nodep_layout)
        if search:
            seq = self.main_window.input_sequence.setText('')
            shot = self.main_window.input_shot.setText('')
                

    ####################
    # RIGHT CLICK MENU #
    ####################
    def rightClickMenuStack(self, pos):
        if self.stack_view.selectedIndexes():
            node = self.stack_model.getNode(self.stack_view.indexAt(pos))
            index =  self.stack_model.parent(self.stack_view.currentIndex()) 

            menu = QtGui.QMenu()
            menu.addAction(QtGui.QAction('Remove', menu))
            itemMenu = menu.exec_(QtGui.QCursor.pos())
            if itemMenu != None:
                if itemMenu.text() == 'Remove':
                    self.removeItem(node, index, self.stack_model, 'stack')
        else:
            menu = QtGui.QMenu()
            menu.addAction(QtGui.QAction('Create new Stack', menu))
            itemMenu = menu.exec_(QtGui.QCursor.pos())
            if itemMenu != None:
                if itemMenu.text() == 'Create new Stack':
                    self.createNewStackNode()
                    
                    
    def rightClickMenuRender(self, pos):
        if self.render_view.selectedIndexes():
            node = self.stack_model.getNode(self.render_view.indexAt(pos))
            index =  self.stack_model.parent(self.render_view.currentIndex()) 

            menu = QtGui.QMenu()
            menu.addAction(QtGui.QAction('Remove', menu))
            itemMenu = menu.exec_(QtGui.QCursor.pos())
            if itemMenu != None:
                if itemMenu.text() == 'Remove':
                    self.removeItem(node, index, self.render_model, 'render')
        else:
            menu = QtGui.QMenu()
            menu.addAction(QtGui.QAction('Create new Render', menu))
            itemMenu = menu.exec_(QtGui.QCursor.pos())
            if itemMenu != None:
                if itemMenu.text() == 'Create new Render':
                    self.createNewRenderNode()


    def removeItem(self, node, index, model, type_model):
        if node._type=='char':
            path = node.getPath()
            root = self.model_breakdown.getRootNode()
            if type_model == 'stack':
                if path:
                    root.getChildFromPath(path).updateProperty('isInStack', '')
            elif type_model == 'render':
                to_remove = None
                for n in root.getChildFromPath(path).getProperty('isInRender'):
                    if n.name()==node.parent().name():
                        to_remove = node.parent()
                if to_remove:
                    root.getChildFromPath(path).getProperty('isInRender').remove(to_remove)
            parent = node.parent()
            parent.removeChild(node.row())
            #Remove empty groups
            '''
            if not parent.getChildren():
                parent_of_parent = parent.parent()
                parent_of_parent.removeChild(parent.row())
            '''
            model.refreshView()
        else:
            root = self.model_breakdown.getRootNode()
            children = node.getChildren()
            if children:
                #make a copy because we are deleting the original
                #and if not the loop will end before
                children_copy = list(children)
                for c in children_copy:
                    path = c.getPath()
                    if type_model == 'stack':
                        root.getChildFromPath(path).updateProperty('isInStack', '')
                    elif type_model == 'render':
                        to_remove = None
                        for n in root.getChildFromPath(path).getProperty('isInRender'):
                            if n.name()==node.name():
                                to_remove = node
                        if to_remove:
                            root.getChildFromPath(path).getProperty('isInRender').remove(to_remove)
                    parent = c.parent()
                    parent.removeChild(c.row())
            parent = node.parent()
            parent.removeChild(node.row())
            model.refreshView()
            self.clearViews(breakdown=False, stack=False, render=False, tree=True, properties=True)
             
             
    def createNewStackNode(self):
        posible_trees = self.loadPosibleTrees()
        accepted, stack_name, stack_type = create_stack_win.CreateStackUI.getStackProperties(posible_trees)
        if accepted:
            stack_root = self.stack_model.getRootNode()
            stack_new_node = databox.Node(stack_name, stack_root, self.types.node_type_stack)
            stack_new_node.addProperty(self.types.json_tree_key, stack_type)
            #Load the tree nodes
            tree_nodes = self.createTreeStructure(stack_new_node)
            stack_new_node.addProperty(self.types.tree_nodes_key, tree_nodes)
            self.stack_model.refreshView()
            
            
    def createNewRenderNode(self):
        render_root = self.render_model.getRootNode()
        dict = {'nodeType' : 'render'}
        parent_node = self.convertJsonNodeToDataboxNode("Render Scene %02d"%render_root.childCount(), dict)
        parent_node.setType(self.types.node_type_render)
        render_root.addChild(parent_node)
        self.render_model.refreshView()
            
          
    ################
    # CREATE NODES #
    ################
    def createDefaultBreakdownNode(self):
        self.breakdown_root_node = databox.Node(self.types.root_name_shot)
        return self.breakdown_root_node
    
    
    def createDefaultStackNode(self):
        stack_root_node = databox.Node(self.types.root_name_stacks, type=self.types.node_type_stack)
        #databox.Node("Stack 01", stack_root_node, "stack")
        return stack_root_node
    
    
    def createDefaultRenderNode(self):
        self.render_root_node = databox.Node(self.types.root_name_renders, type=self.types.node_type_render)
        #databox.Node("Default", self.render_root_node, self.types.node_type_render)
        return self.render_root_node
        
        
    def createDefaultTreeNode(self):
        #TODO:
        #This will be removed when the graphic tree is developed
        tree_root_node = databox.Node("Tree")
        return tree_root_node
    

    #################################
    # CREATE DEFAULT VIEWS / PANELS #
    #################################
    def createBreakdownView(self):
        #BREAKDOWN VIEW
        self.breakdown_view = tree_view.TreeView()
        self.model_breakdown = model.Model(self.createDefaultBreakdownNode(), header = "Breakdown", parent = self.breakdown_view)
        self.model_breakdown.addColumn('Stack', 'isInStack')
        self.model_breakdown.addColumn('Render', 'isInRender')
        
        #For draging several rows we have to use QtGui.QAbstractItemView.ExtendedSelection
        #Usin QtGui.QAbstractItemView.Multiselection doesn't work
        self.breakdown_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.breakdown_view.setModel(self.model_breakdown)
        self.breakdown_view.setDragDropMode(QtGui.QAbstractItemView.DragOnly)
        #very important, for deleting the source
        #other options in https://srinikom.github.io/pyside-docs/PySide/QtCore/Qt.html
        self.breakdown_view.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.breakdown_view.setColumnWidth(0, 250)
        return self.breakdown_view
        
        
    def createStackView(self):
        #STACK VIEW
        self.stack_view = tree_view.TreeView()
        self.connect(self.stack_view, QtCore.SIGNAL("clicked(QModelIndex)"),self.clickedStackCallback)
        self.connect(self.stack_view, QtCore.SIGNAL("deselected()"),self.stackDeselectedCallback)
        self.stack_model = model.Model(self.createDefaultStackNode(), header = "Scene", parent = self.stack_view)
        self.stack_view.setModel(self.stack_model)
        self.stack_view.setDragDropMode(QtGui.QAbstractItemView.DropOnly)
        #Menu
        self.stack_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.stack_view.customContextMenuRequested.connect(self.rightClickMenuStack)  
        return self.stack_view
        

    def createRenderView(self):
        #RENDER VIEW
        self.render_view = tree_view.TreeView()
        self.connect(self.render_view, QtCore.SIGNAL("clicked(QModelIndex)"),self.clickedRenderNodeCallback)
        self.connect(self.render_view, QtCore.SIGNAL("deselected()"),self.stackDeselectedCallback)
        self.render_model = model.Model(self.createDefaultRenderNode(), header = "Renders", parent = self.render_view)
        self.render_view.setModel(self.render_model)
        self.render_view.setDragDropMode(QtGui.QAbstractItemView.DropOnly)
        #Menu
        self.render_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.render_view.customContextMenuRequested.connect(self.rightClickMenuRender)  
        return self.render_view


    def createTreeView(self):
        tree_layout = QtGui.QVBoxLayout()
        self.tree_combo_box = QtGui.QComboBox()
        self.tree_combo_box.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContents)
        self.tree_combo_box.activated.connect(self.stackTypeChangedCallback)
        stack_selected_title_label = QtGui.QLabel('Stack selected:')
        font = stack_selected_title_label.font()
        font.setPointSize(12)
        font.setBold(True)
        stack_selected_title_label.setFont(font)
        
        self.stack_selected_label = QtGui.QLabel('')
        self.stack_selected_label.setFont(font)
        type_stack_label = QtGui.QLabel('Type of stack:')
        upper_layout = QtGui.QHBoxLayout()
        upper_layout.addWidget(stack_selected_title_label)
        upper_layout.addWidget(self.stack_selected_label)
        upper_layout.addStretch(1)
        upper_layout.addWidget(type_stack_label)
        upper_layout.addWidget(self.tree_combo_box)
        tree_layout.addLayout(upper_layout)
        #Graphic tree
        self.tree_scene=QtGui.QGraphicsScene(self)
        self.connect(self.tree_scene, QtCore.SIGNAL("selectionChanged()"),self.clickedNodeCallback)
        self.view = tree_graphic_view.TreeGraphicView(self.tree_scene, self)
        self.view.setSceneRect(-1000, -1000, 2000, 2000)
        tree_layout.addWidget(self.view)
        tree_widget = QtGui.QWidget()
        tree_widget.setLayout(tree_layout)
        return tree_widget
    
    
    def createNodePropertiesPanel(self):
        properties_gbox = QtGui.QGroupBox("Node Properties")
        self.nodep_layout = QtGui.QVBoxLayout()
        properties_gbox.setLayout(self.nodep_layout)
        #self.nodep_view = tree_view.TreeView()
        return properties_gbox
    
    
    def createPropertyWidget(self, parent_widget, value_dict):
        #When a node is selected this is called and it creates a property widget
        if value_dict["attrType"] == "int":
            spin_box = QtGui.QSpinBox()
            spin_box.setRange(0,1000000)
            spin_box.setValue(value_dict["value"])
            self.main_window.connect(spin_box, QtCore.SIGNAL("valueChanged(QString)"), lambda: self.propertyEditCallback(parent_widget))
            return spin_box
        elif value_dict["attrType"] == "float":
            spin_box = QtGui.QDoubleSpinBox()
            spin_box.setRange(0, 10)
            spin_box.setSingleStep(0.01)
            spin_box.setValue(value_dict["value"])
            self.main_window.connect(spin_box, QtCore.SIGNAL("valueChanged(QString)"), lambda: self.propertyEditCallback(parent_widget))
            return spin_box
        elif value_dict["attrType"] == "bool":
            check_box = QtGui.QCheckBox()
            check_box.setChecked(value_dict["value"])
            self.main_window.connect(check_box, QtCore.SIGNAL("clicked(bool)"), lambda: self.propertyEditCallback(parent_widget))
            return check_box
        elif value_dict["attrType"] == "list":
            combo_box = QtGui.QComboBox()
            combo_box.addItems(value_dict["options"])
            index = combo_box.findText(value_dict["value"])
            combo_box.setCurrentIndex(index);
            combo_box.activated.connect(lambda: self.propertyEditCallback(parent_widget))
            return combo_box
        elif value_dict["attrType"] == "hair_component_list":
            v_layout = QtGui.QVBoxLayout()
            stack = self.stack_model.getNode(self.stack_view.currentIndex()) 
            if stack.getType() == self.types.node_type_char:
                #the hs and components have been loaded previously
                component_list = value_dict["options"]
                if component_list:
                    for component in component_list:
                        check_box = QtGui.QCheckBox(component)
                        if component in value_dict["value"]:
                            check_box.setChecked(True)
                        else:
                            check_box.setChecked(False)
                        self.main_window.connect(check_box, QtCore.SIGNAL("clicked(bool)"), lambda: self.propertyEditCallback(parent_widget))
                        v_layout.addWidget(check_box)
            widget = QtGui.QWidget()
            widget.setLayout(v_layout)
            return widget
        elif value_dict["attrType"] == "path":
            path_layout = QtGui.QGridLayout()
            line_edit = QtGui.QLineEdit()
            if not value_dict["enable"]:
                line_edit.setDisabled(True)
            line_edit.setText(value_dict["value"])
            path_layout.addWidget(line_edit, 0, 0)
            refresh_button = QtGui.QPushButton('Refresh', self)
            path_layout.addWidget(refresh_button, 0, 1)
            path_widget = QtGui.QWidget()
            path_widget.setLayout(path_layout)
            self.main_window.connect(refresh_button, QtCore.SIGNAL("clicked(bool)"), lambda: self.propertyEditCallback(parent_widget))
            return path_widget
        else:
            line_edit = QtGui.QLineEdit()
            line_edit.setText(value_dict["value"])
            self.main_window.connect(line_edit, QtCore.SIGNAL("textChanged(QString)"), lambda: self.propertyEditCallback(parent_widget))
            return line_edit
        

    def getStackByName(self, stack_name):
        for stack in self.stack_model.getRootNode().getChildren():
            if stack.name()==stack_name:
                return stack
        
        
    def overrideLabel(self, label):
        pal = QtGui.QPalette(label.palette())
        pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(QtCore.Qt.blue))
        label.setPalette(pal)


    #############
    # CALLBACKS #
    #############
    def clickedStackCallback(self, index):
        node_char = None
        node = index.internalPointer()
        if node.getType() == self.types.node_type_char:
            node_char = node
            node = node_char.parent()
        if node.getType() == self.types.node_type_stack:
            #Redraw the tree for the stack index.internalPointer()
            self.redrawTree(node, node_char)
            #Clear the nodes panel
            ui_utils.clearLayout(self.nodep_layout)
            #Update selected label
            self.stack_selected_label.setText(node.name())
            pal = QtGui.QPalette(self.stack_selected_label.palette())
            pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(QtCore.Qt.black))
            self.stack_selected_label.setPalette(pal)
            
            #Update the possible trees combo box
            posible_trees = self.loadPosibleTrees()
            self.tree_combo_box.clear() 
            self.tree_combo_box.addItems(posible_trees)
            #Select the correspondent tree type
            tree_json_active = node.getProperty(self.types.json_tree_key)
            index = self.tree_combo_box.findText(tree_json_active)
            self.tree_combo_box.setCurrentIndex(index)
        if node_char:
            #a char is selected, we check if it has overrides
            #Update selected label
            self.stack_selected_label.setText(node.name()+' - '+node_char.name())
            pal = QtGui.QPalette(self.stack_selected_label.palette())
            pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(QtCore.Qt.blue))
            self.stack_selected_label.setPalette(pal)


    def showSubmitRenderProperties(self, render_propeties):
        #Display the properties in the nodes panel
        vbox = QtGui.QGridLayout()
        rest_pos = 2 #This is for counting the number of no special properties
        for key, value in render_propeties.iteritems():
            #Special properties
            #We want the special properties first
            if key == 'preset':
                pos = 0
            elif key == 'AASamples':
                pos = 1
            elif key == 'DiffSamples':
                pos = 2
            elif key == 'GlossSamples':
                pos = 3
            elif key == 'RefrSamples':
                pos = 4 
            elif key == 'SSSSamples':
                pos = 5 
            elif key == 'motionBlur':
                pos = 6 
            grid_layout = QtGui.QGridLayout()
            label = QtGui.QLabel(key)
            grid_layout.addWidget(label, 0, 0)
            grid_layout.addWidget(self.createPropertyWidget(grid_layout, value), 0, 1)
            vbox.addLayout(grid_layout, pos, 0)
        self.nodep_layout.addLayout(vbox)
        self.nodep_layout.addStretch(1)  



    def recursiveSetFrameRange(self, node, char_node):
        if node:
            for c in node:
                if 'startFrame' in c.getProperty('attributeList').keys() and 'endFrame' in c.getProperty('attributeList').keys():
                    #we make frames override for that node in that character
                    char_node.addProperty(c.name(), {'attributeList': {'startFrame' : {'attrType': 'int', 'value': self.start_frame}, 'endFrame': {'attrType': 'int', 'value': self.end_frame}}})
                    self.recursiveSetFrameRange(c.getChildren(), char_node)
                                    
                                    


    def propertyEditCallback(self, parent_widget):
        #Update the value of the attribute
        if self.tree_scene.selectedItems():    
            items = self.tree_scene.selectedItems()
            node = items[0].getNode()
            stack =  self.stack_model.getNode(self.stack_view.currentIndex()) 
            label = parent_widget.itemAtPosition(0,0).widget()
            property = label.text()
            if stack.getType() == self.types.node_type_char:
                #If the stack selected is a char, we load the overrides
                self.overrideLabel(label)
                att_list = None
                if stack.getProperty(node.name()) and 'attributeList' in stack.getProperty(node.name()).keys():
                    #get the attributes overrides for the char 
                    att_list = stack.getProperty(node.name())['attributeList']
                    if property not in att_list.keys():
                        #if the property didn't have override, we add the property
                        att_list.update({property: copy.deepcopy(node.getProperty('attributeList'))[property]})
                else:
                    #if no char overrides, we create the first override
                    att_list = {property: copy.deepcopy(node.getProperty('attributeList'))[property]}
            else:
                #If not we load the node selected properties
                att_list = copy.deepcopy(node.getProperty('attributeList'))
            #save the properties in the node
            if att_list[property]["attrType"] == "int":
                att_list[property]['value'] = int(parent_widget.itemAtPosition(0,1).widget().text())
            elif att_list[property]["attrType"] == "float":
                att_list[property]['value'] = float(parent_widget.itemAtPosition(0,1).widget().text().replace(',','.'))
            elif att_list[property]["attrType"] == "bool":
                att_list[property]['value'] = bool(parent_widget.itemAtPosition(0,1).widget().isChecked())
            elif att_list[property]["attrType"] == "list":
                att_list[property]['value'] = parent_widget.itemAtPosition(0,1).widget().currentText()
            elif att_list[property]["attrType"] == "hair_component_list":
                widget = parent_widget.itemAtPosition(0,1).widget()
                layout = widget.layout()
                att_list[property]['value'] = []
                for i in range(0, layout.count()):
                    w = layout.itemAt(i).widget()
                    if w.isChecked():
                        att_list[property]['value'].append(w.text()) 
            elif att_list[property]["attrType"] == "path":
                #the user has added a work path
                path = parent_widget.itemAtPosition(0,1).widget().layout().itemAtPosition(0,0).widget().text()
                if path.startswith('S:'):
                    path = path[3:]
                elif '\\' in path:
                    path = path.replace('\\', '/')
                #this is in else because setText sends a signal of edited field too
                try:
                    file_type = 'the_correct_filetype'
                except:
                    file_type = ''
                if node.getProperty('attributeList')['path']['fileType'] == file_type:
                    seq = path_values['[seqName]']
                    shot = path_values['[shotNum]']
                    self.start_frame = 101
                    self.end_frame = 120
                    alias = path_values['[alias]']
                    self.main_window.input_sequence.setText(seq)
                    self.main_window.input_shot.setText(shot)
                    
                    parent = self.getStackByName(self.stack_selected_label.text().split(' - ')[0])
                    
                    found=False
                    children = parent.getChildren()
                    for c in children:
                        if c.name()==alias:
                            found=True
                            char_node = c
                    if not found:
                        if parent.getType() == self.types.node_type_stack and parent.name() != self.types.root_name_stacks:
                            char_node = databox.Node(alias, parent, self.types.node_type_char)
                            #mod
                            #short_name, hair_style = self.findCharBreakdown(seq, shot, alias)
                            short_name = ''
                            hair_style = ''
                            #end mod                            
                            char_node.addProperty('isInRender', [])
                            char_node.addProperty('isInStack', '')
                            char_node.addProperty('shortName', short_name)
                            if hair_style:
                                char_node.addProperty('hairStyle', hair_style)
                                #char_node.addProperty('hairComponents', self.getHairComponents(seq, shot, char_node))
                            
                            if 'startFrame' in node.getProperty('attributeList').keys() and 'endFrame' in node.getProperty('attributeList').keys():
                                #start_f_d = copy.deepcopy(node.getProperty('attributeList')['startFrame'])
                                #end_f_d = copy.deepcopy(node.getProperty('attributeList')['endFrame'])
                                #we make frames override for that node in that character
                                char_node.addProperty(node.name(), {'attributeList': {'startFrame' : {'attrType': 'int', 'value': self.start_frame}, 'endFrame': {'attrType': 'int', 'value': self.end_frame}}})
                                #Set the frame range for the following nodes in the graph
                                self.recursiveSetFrameRange(node.getChildren(), char_node)
                                #Change the frame range of the renders
                                for render_n in self.render_root_node.getChildren():
                                    render_n.getProperty('attributeList')['startFrame']['value'] = self.start_frame
                                    render_n.getProperty('attributeList')['endFrame']['value'] = self.end_frame
                                    
                        else:
                            char_node = stack
                            att_list[property]['value'] = path
                    
                        self.loadShotInfo(False)
                    if not char_node.getProperty(node.name()):
                        char_node.addProperty(node.name(), {'attributeList': {}})
                    #we save the value in the new char node
                    proper = att_list[property]
                    proper['value'] = path
                    char_node.getProperty(node.name())['attributeList'].update({'path': proper})
                    self.stack_model.refreshView()
            else:
                att_list[property]['value'] = parent_widget.itemAtPosition(0,1).widget().text()
            if stack.getType() == self.types.node_type_char:
                #If the stack selected is a char, we save the overrides
                dict = {'attributeList': att_list}
                stack.updateProperty(node.name(), dict)
            else:
                if not att_list[property]["attrType"] == "path":
                    #save the properties in the node
                    node.updateProperty('attributeList', att_list)
            if property == 'enable':
                items[0].setEnable(bool(parent_widget.itemAtPosition(0,1).widget().isChecked()))
        elif self.render_model.getNode(self.render_view.currentIndex()):
            #If the changes are in a render node
            render_node = self.render_model.getNode(self.render_view.currentIndex())
            att_list = render_node.getProperty('attributeList')
            submit_render = render_node.getProperty('submitRender')
            property = parent_widget.itemAtPosition(0,0).widget().text()
            #save the properties in the node
            if property in att_list.keys():
                if att_list[property]["attrType"] == "int": 
                    att_list[property]['value'] = int(parent_widget.itemAtPosition(0,1).widget().text())
                elif att_list[property]["attrType"] == "float":
                    att_list[property]['value'] = float(parent_widget.itemAtPosition(0,1).widget().text().replace(',','.'))
                elif att_list[property]["attrType"] == "bool":
                    att_list[property]['value'] = bool(parent_widget.itemAtPosition(0,1).widget().isChecked())
                    if property == 'submitRender':
                        #Show the rest properties
                        if att_list[property]['value']:
                            self.showSubmitRenderProperties(render_node.getProperty('submitRender'))
                        else:
                            self.displayProperties(render_node)
                elif att_list[property]["attrType"] == "list":
                    att_list[property]['value'] = parent_widget.itemAtPosition(0,1).widget().currentText()
                elif att_list[property]["attrType"] == "hair_component_list":
                    widget = parent_widget.itemAtPosition(0,1).widget()
                    layout = widget.layout()
                    att_list[property]['value'] = []
                    for i in range(0, layout.count()):
                        w = layout.itemAt(i).widget()
                        if w.isChecked():
                            att_list[property]['value'].append(w.text()) 
                else:
                    att_list[property]['value'] = parent_widget.itemAtPosition(0,1).widget().text()
            if property in submit_render.keys():
                if submit_render[property]["attrType"] == "int":
                    submit_render[property]['value'] = int(parent_widget.itemAtPosition(0,1).widget().text())
                elif submit_render[property]["attrType"] == "float":
                    submit_render[property]['value'] = float(parent_widget.itemAtPosition(0,1).widget().text().replace(',','.'))
                elif submit_render[property]["attrType"] == "bool":
                    submit_render[property]['value'] = bool(parent_widget.itemAtPosition(0,1).widget().isChecked())
                elif submit_render[property]["attrType"] == "list":
                    submit_render[property]['value'] = parent_widget.itemAtPosition(0,1).widget().currentText()
                elif submit_render[property]["attrType"] == "hair_component_list":
                    widget = parent_widget.itemAtPosition(0,1).widget()
                    layout = widget.layout()
                    submit_render[property]['value'] = []
                    for i in range(0, layout.count()):
                        w = layout.itemAt(i).widget()
                        if w.isChecked():
                            submit_render[property]['value'].append(w.text()) 
                else:
                    submit_render[property]['value'] = parent_widget.itemAtPosition(0,1).widget().text()


    def clickedRenderNodeCallback(self, index):
        #clean the tree and the properties panel
        self.stackDeselectedCallback()
        #If the render node doesn't have properties we load the default
        node = index.internalPointer()
        if not node.getProperty('nodeType'):
            dict = {'nodeType' : 'render'}
            new_node = self.convertJsonNodeToDataboxNode(node.name(), dict)
            node.setProperties(new_node.getProperties())
        #fulfill the properties panel
        self.clickedNodeCallback(index)
        #This shows the submit to render properties
        if node.getProperty('attributeList')['submitRender']['value'] and node.getType() != self.types.node_type_char:
            self.showSubmitRenderProperties(node.getProperty('submitRender'))


    def displayProperties(self, node):
        #Display the properties in the nodes panel
        if node.getType() != self.types.node_type_char:
            stack =  self.stack_model.getNode(self.stack_view.currentIndex()) 
            ui_utils.clearLayout(self.nodep_layout)
            vbox = QtGui.QGridLayout()
            rest_pos = 2 #This is for counting the number of no special properties
            for key, value in node.getProperties()['attributeList'].iteritems():
                #Special properties
                #We want the special properties first
                if key == 'enable':
                    pos = 0
                elif key == 'startFrame':
                    pos = 1
                elif key == 'endFrame':
                    pos = 2 
                else:
                    #we need to asignate a pos after 3 to the no special properties
                    rest_pos = rest_pos+1
                    pos = rest_pos
                    if key == 'path':
                        pass
                        #calculate_module.CalculateModule(self.main_window.project_combo.currentText(), self.main_window.input_sequence.text(), self.main_window.input_shot.text()).calculatePath(stack, node)                     
                grid_layout = QtGui.QGridLayout()
                label = QtGui.QLabel(key)
                grid_layout.addWidget(label, 0, 0)
                if stack.getType() == self.types.node_type_char:
                    #char override
                    #we save the name of the node in the char, and inside the attributeList with the changes
                    if node.name() in stack.getProperties().keys() and 'attributeList' in stack.getProperty(node.name()).keys() and key in stack.getProperty(node.name())['attributeList'].keys():
                        value = stack.getProperty(node.name())['attributeList'][key]
                        self.overrideLabel(label)
                    elif 'selectHairComponent' == key: #in node.getProperties()['attributeList'].keys():
                        if not stack.getProperty(node.name()) or 'attributeList' not in stack.getProperty(node.name()).keys() or 'selectHairComponent' not in stack.getProperty(node.name())['attributeList'].keys():
                            #if it has the attr selectHairComponent, we make the char override from the component list
                            component_list = stack.getProperty('hairComponents')
                            att_list = copy.deepcopy(node.getProperty('attributeList')['selectHairComponent'])
                            att_list['options'] = component_list
                            att_list['value'] = component_list
                            if node.name() in stack.getProperties().keys() and 'attributeList' in stack.getProperty(node.name()).keys():
                                stack.getProperty(node.name())['attributeList'].update({'selectHairComponent': att_list})
                            else:
                                if node.name() in stack.getProperties().keys():
                                    stack.getProperty(node.name()).update({'attributeList': {'selectHairComponent': att_list}})
                                else:
                                    stack.updateProperty(node.name(), {'attributeList': {'selectHairComponent': att_list}})
                            self.overrideLabel(label)
                        value = stack.getProperty(node.name())['attributeList']['selectHairComponent']
                    elif 'rigCharVar' == key:
                        att_list = copy.deepcopy(node.getProperty('attributeList')['rigCharVar'])
                        att_list['value'] = stack.getProperty('charVar')
                        if node.name() in stack.getProperties().keys() and  'attributeList' in stack.getProperty(node.name()).keys():
                            stack.getProperty(node.name())['attributeList'].update({'rigCharVar': att_list})
                        else:
                            if node.name() in stack.getProperties().keys():
                                stack.getProperty(node.name()).update({'attributeList': {'rigCharVar': att_list}})
                            else:
                                stack.updateProperty(node.name(), {'attributeList': {'rigCharVar': att_list}})
                        self.overrideLabel(label)
                        value = stack.getProperty(node.name())['attributeList']['rigCharVar']
                grid_layout.addWidget(self.createPropertyWidget(grid_layout, value), 0, 1)
                vbox.addLayout(grid_layout, pos, 0)
            self.nodep_layout.addLayout(vbox)
            self.nodep_layout.addStretch(1)


    def clickedNodeCallback(self, index=None):
        if index:
            node = index.internalPointer()
            self.displayProperties(node)
        elif self.tree_scene.selectedItems():
            if type(self.tree_scene.selectedItems()[0]).__name__ == 'NodeItem':
                node = self.tree_scene.selectedItems()[0].getNode()
                self.displayProperties(node)
        else:
            self.clearViews(breakdown=False, stack=False, render=False, tree=False, properties=True)


    def configPrefsChangedCallback(self):
        self.clearViews(breakdown=True, stack=True, render=True, tree=True, properties=True)


    def stackTypeChangedCallback(self):
        if self.stack_view.selectedIndexes():
            stack_node = self.stack_model.getNode(self.stack_view.currentIndex()) 
            stack_node.updateProperty(self.types.json_tree_key, self.tree_combo_box.currentText())
            #Load the tree nodes
            tree_nodes = self.createTreeStructure(stack_node)
            stack_node.updateProperty(self.types.tree_nodes_key, tree_nodes)
            #Redraw the tree for the updated stack node
            self.redrawTree(stack_node)
            #Clear the nodes panel
            ui_utils.clearLayout(self.nodep_layout)


    def stackDeselectedCallback(self):
        self.clearViews(breakdown=False, stack=False, render=False, tree=True, properties=True)


    def launchCallback(self):       
        project = self.main_window.project_combo.currentText()
        seq = self.main_window.input_sequence.text()
        shot = self.main_window.input_shot.text()
        stack_l = []
        for stack in self.stack_model.getRootNode().getChildren():
            stack_l.append(stack)
          
        render_l = []  
        for render in self.render_model.getRootNode().getChildren():
            render_l.append(render)
            
        try:
            export_data.exportData(self.config, project, seq, shot, stack_l, render_l)
            #Pack the info and send
            phrases = ["Wingardium leviosa! The magic is working now on the shot.", "Houston, we have sent a shot with no problem!!", "Yippee ki yay, shot launched!!",
                       "Hakuna matata. Now you can work on another shot!!", "Shot launched. I've got a good feeling about this my padawan.", "Great Scott!! Another shot launched!",
                       "Long life and prosperity to the shot!!", "They may take our lives, but they'll never take our shots!!", "Hasta la vista, baby.", "Just keep simming!!",
                       "May the Magic Button be with you.", "You have my Sword, and my Bow, and my Shot!!", "Shot sent, I'm the king of the world!", " I'm federal agent Jack Bauer. This is the longest sim of my life."]
            QtGui.QMessageBox.information(self, 'Launched!', phrases[randint(0,12)], buttons = QtGui.QMessageBox.Ok)
        except:
            QtGui.QMessageBox.warning(self, 'ERROR!!!', "Error! Something went wrong.", buttons = QtGui.QMessageBox.Ok)
            import traceback
            traceback.print_exc()

        
    ################
    # LOAD CONFIGS #
    ################
    def convertJsonNodeToDataboxNode(self, name, node):
        #Aux function, converts a node json to databox
        node_type = node['nodeType']
        node_name = self.config.getNodeByType(node_type)
        #Group
        if 'group' in node.keys():
            #If in the tree definitions exists use it
            group_property = node['group']
        else:
            group_property = self.config.getPropertyNode(node_name, 'group')
        #Pos
        if 'pos' in node.keys():
            #If in the tree definitions exists use it
            pos_property = node['pos']
        else:
            pos_property = self.config.getPropertyNode(node_name, 'pos')
        #Color
        if 'color' in node.keys():
            #If in the tree definitions exists use it
            color_property = node['color']
        else:
            color_property = self.config.getPropertyNode(node_name, 'color')
        #Icon
        if 'icon' in node.keys():
            #If in the tree definitions exists use it
            icon_property = node['icon']
        else:
            icon_property = self.config.getPropertyNode(node_name, 'icon')    
        #attributeList
        if 'attributeList' in node.keys():
            #If in the tree definitions exists use it
            node_properties = self.config.getPropertyNode(node_name, 'attributeList')
            attribute_list_property = {}
            for key, value in node_properties.iteritems():
                #for each attr in the attributeList of the node
                #we search it in the tree overrides
                if key in node['attributeList'].keys():
                    if 'list' in value['attrType']:
                        attribute_list_property.update({key: {'value' : node['attributeList'][key], 'attrType': value['attrType'], 'options': value['options']}})
                    elif 'path' in value['attrType']:
                        attribute_list_property.update({key: {'value' : node['attributeList'][key], 'attrType': value['attrType'], 'fileType': value['fileType'], 'description': value['description'], 'creator': value['creator'], 'enable': value['enable']}})
                    else:
                        attribute_list_property.update({key: {'value' : node['attributeList'][key], 'attrType': value['attrType']}})
                else:
                    if 'list' in value['attrType']:
                        attribute_list_property.update({key: {'value' : value['value'], 'attrType': value['attrType'], 'options': value['options']}})
                    elif 'path' in value['attrType']:
                        attribute_list_property.update({key: {'value' : value['value'], 'attrType': value['attrType'], 'fileType': value['fileType'], 'description': value['description'], 'creator': value['creator'], 'enable': value['enable']}})
                    else:
                        attribute_list_property.update({key: {'value' : value['value'], 'attrType': value['attrType']}})
                #If we have the frame range from the shot we make an override
                if key == 'startFrame' and self.start_frame:
                    attribute_list_property.update({key: {'value' : self.start_frame, 'attrType': value['attrType']}})
                elif key == 'endFrame' and self.end_frame:
                    attribute_list_property.update({key: {'value' : self.end_frame, 'attrType': value['attrType']}})
        else:
            attribute_list_property = self.config.getPropertyNode(node_name, 'attributeList')    
        new_json_node = databox.Node(name)
        new_json_node.addProperty('nodeType', node_type)
        new_json_node.addProperty('group', group_property)
        new_json_node.addProperty('pos', pos_property)
        new_json_node.addProperty('color', color_property)
        new_json_node.addProperty('icon', icon_property)
        new_json_node.addProperty('attributeList', attribute_list_property)
        #submitRender, only in the render node
        if node_type == "render":
            render_properties = self.config.getPropertyNode(node_name, 'submitRender')
            new_json_node.addProperty('submitRender', render_properties)
        return new_json_node
    
    
    def searchLatestTreeNode(self, nodes):
        #Aux function. 
        #It searches the node at the bottom of the tree.
        #It helps to create the tree structure from the bottom.
        found = False
        index = 0
        keys_l = nodes.keys()
        node_name = None
        while not found and index<len(keys_l):
            if not nodes[keys_l[index]]['output']:
                found = True
                #node_type = nodes[keys_l[index]]['nodeType']
                node_name = keys_l[index]
            else:
                index = index+1 
        return node_name, nodes[keys_l[index]]
    
    
    def createTreeStructure(self, tree_node):
        #Creates an structure for the tree (using data box children)
        nodes = self.config.getTreeNodes(tree_node.getProperty(self.types.json_tree_key))
        node_name, node = self.searchLatestTreeNode(nodes)
        if node_name:
            end = False
            child_node = self.convertJsonNodeToDataboxNode(node_name, node)
            if 'outarrow' in node.keys():
                child_node.addProperty('outarrow', node['outarrow'])
            while not end:
                end = True
                for n in nodes.keys():
                    if nodes[n]['output'] == node_name:
                        end = False
                        parent_node = self.convertJsonNodeToDataboxNode(n, nodes[n])
                        if 'outarrow' in nodes[n].keys():
                            parent_node.addProperty('outarrow', nodes[n]['outarrow'])
                        parent_node.addChild(child_node)
                        node_name = n
                        child_node = parent_node
                #print child_node.getProperty('icon')
        return child_node
    
    
    def loadStacks(self, trees_dict):
        #Loads in the stack view, the tree selected in the stack view
        #It loads the structure from the configs files
        #Change the stack model
        stack_root_node = self.createDefaultStackNode()
        for tree in trees_dict.keys():
            stack_new_node = databox.Node(tree, stack_root_node, self.types.node_type_stack)
            stack_new_node.addProperty(self.types.json_tree_key, trees_dict[tree])
            #Load the tree nodes
            tree_nodes = self.createTreeStructure(stack_new_node)
            stack_new_node.addProperty(self.types.tree_nodes_key, tree_nodes)
            #add attributes to stack_new_node
        self.stack_model.setRoot(stack_root_node)
        self.stack_model.refreshView()
        
        
    def loadRenders(self, render_dict):
        #Loads in the render view, the tree selected in the stack view
        #It loads the structure from the configs files
        #Change the stack model
        render_root_node = self.createDefaultRenderNode()
        for key, value in render_dict.iteritems():
            render_new_node = self.convertJsonNodeToDataboxNode(key, value)
            render_new_node.setType(self.types.node_type_render)
            render_root_node.addChild(render_new_node)
        self.render_model.setRoot(render_root_node)
        self.render_model.refreshView()
        

    def loadConfigPrefs(self):
        #Load the configuration preferences
        self.config = config_logic.ConfigLogic()
        self.main_window.prefs_combo.addItems(self.config.getPrefs())
        self.configPrefsChangedCallback()
        
        
    def loadPosibleTrees(self):
        #Load trees types
        trees_dict = self.config.getPrefTrees(self.main_window.prefs_combo.currentText())
        posible_trees = []
        for key, value in trees_dict.iteritems():
            posible_trees.append(value)
        return posible_trees

    '''
    def findCharBreakdown(self, seq, shot, alias):
        anim_blocks_dict = {}
        try:
            self.start_frame, self.end_frame = CurrentProject().getShot(seq, shot).getProductionRange()
            anim_blocks_l = ['main', 'extrasA', 'extrasB']
            for anim_block in anim_blocks_l:
                anim_blocks_dict.update({anim_block: []})
            char_breakdown = CurrentProject().getShot(seq, shot).getNewBreakdown()["Character"]
            for charb in char_breakdown:
                anim_blocks_dict[charb["animation_block"]].append(charb)
                for anim_block in anim_blocks_dict.keys():
                    for char in anim_blocks_dict[anim_block]:
                        if char['alias'] == alias:
                            hair_style = ''
                            if char['hair_style']:
                                hair_style = char['hair_style']['short_name']
                            return char['short_name'], hair_style
        except:
            pass
    '''
    

    #######################
    # LOAD SHOT BREAKDOWN #
    #######################
    def fillBreakdownModel(self, seq, shot, anim_blocks_dict, filter = [], clear=True):
        if clear:
            self.clearViews(breakdown=True, stack=True, render=True, tree=True, properties=True)
        #Fill the breakdown view, with the chars from the seq and shot.
        self.breakdown_root_node.deleteAllChildren()
        shot_node = databox.Node(seq+'.'+shot, self.breakdown_root_node, self.types.node_type_shot)
        for anim_block in anim_blocks_dict.keys():
            block = databox.Node(anim_block, shot_node, self.types.node_type_animblock)
            for char in anim_blocks_dict[anim_block]:
                if filter:
                    if char['alias'] not in filter:
                        continue    
                char_node = databox.Node(char['alias'], block, self.types.node_type_char)
                char_node.addProperty('isInRender', [])
                char_node.addProperty('isInStack', '')
                char_node.addProperty('shortName', char['short_name'])
                char_node.addProperty('charVar', char['variation'])
                if char['hair_style']:
                    char_node.addProperty('hairStyle', char['hair_style'])
                    char_node.addProperty('hairComponents', ['head', 'eyelashes', 'eyebrows'])
                    #char_node.addProperty('hairComponents', self.getHairComponents(seq, shot, char_node))
                else:
                    QtGui.QMessageBox.information(self, 'Warning!', char['short_name']+" doesn't have hairstyle assigned.", buttons = QtGui.QMessageBox.Ok)
                    char_node.setIcon("no_hairstyle.png")
                    char_node.setToolTip("No hairstyle in the breakdown")
                    #char_node.setIcon(self.reloadInterfaceIcons(None, "no_hairstyle.png",h=15))
                char_node.createPath()
                #Add all the chars to the default render
                for render in self.render_model.getRootNode().getChildren():
                    if render.name() == 'default':
                        char_node.addProperty('isInRender', [render])
                        render_char_node = databox.Node(char['alias'], render, self.types.node_type_char)
                        render_char_node.setPath(char_node.getPath())
        self.render_model.refreshView()
        self.model_breakdown.refreshView()
        
        
        
    def loadShotInfo(self, clear=True):
        #Searchs the shot and seq, and if this exists fill the breakdown view.
        seq = self.main_window.input_sequence.text()
        shot = self.main_window.input_shot.text()
        if seq and shot:
            #Anim blocks dict
            main_block = [{'alias': 'Marty', 'short_name': 'Marty', 'variation': 'original', 'hair_style': 'original'}, {'alias': 'Doc', 'short_name': 'Doc', 'variation': 'original', 'hair_style': 'original'}]
            extra_a_block = [{'alias': 'genericGirlA', 'short_name': 'genericGirlA', 'variation': 'original', 'hair_style': 'original'}, {'alias': 'genericBoyA', 'short_name': 'genericBoyA', 'variation': 'original', 'hair_style': 'original'}]
            extra_b_block = [{'alias': 'dogGenericA', 'short_name': 'dogGenericA', 'variation': 'original', 'hair_style': 'original'}, {'alias': 'genericGirlC', 'short_name': 'genericGirlC', 'variation': 'original', 'hair_style': 'original'}]
            anim_blocks_dict = {'main': main_block, 'extraA': extra_a_block, 'extraB': extra_b_block}
            #mod
            self.start_frame = 101
            self.end_frame = 120
            self.fillBreakdownModel(seq, shot, anim_blocks_dict, clear=clear)
            #print "The shot "+seq+"."+shot+" doesn't exist."

                
    ###############
    # REDRAW TREE #
    ###############
    def drawNode(self, node, node_char=None, node_list=None, node_item_parent=None):
        if node:
            pos = node.getProperty('pos')
            n_item = node_item.NodeItem(node.name(), node, node.getProperty('color'))
            node_list.append(n_item)
            if node_char:
                #char override, we check if a node has different enable property
                node_override = node_char.getProperty(node.name())
                if node_override and 'attributeList' in node_override.keys() and 'enable' in node_override['attributeList'].keys():
                    n_item.setEnable(node_override['attributeList']['enable']['value'])
                
            n_item.setPosition(pos[0], pos[1])
            self.tree_scene.addItem(n_item)
            for child_node in node.getChildren():
                node_list = self.drawNode(child_node, node_char, node_list, n_item)
            return node_list
    
    
    def redrawTree(self, tree_node, node_char=None):
        self.tree_scene.clear()
        tree_nodes_property = tree_node.getProperty(self.types.tree_nodes_key)
        node_list = self.drawNode(tree_nodes_property, node_char,[])
        self.drawArrows(node_list)
        
        
    def drawArrows(self, node_list):
        for draw_node in node_list:
            output_arrow = draw_node.getNode().getProperty('outarrow')
            if output_arrow:
                for oa in output_arrow:
                    for destination_node in node_list:
                        if oa == destination_node.getNode().name():
                            arrow = node_item.ArrowItem(destination_node, draw_node)
                            arrow.setColor(QtCore.Qt.black)
                            arrow.setZValue(-1000.0)
                            arrow.updatePosition()
                            self.tree_scene.addItem(arrow)
                            continue
        
            

    ###############
    # INIT WINDOW #
    ###############
    def initializeWindow(self, load_from_scene = False):
        if load_from_scene:
            export_statistics.exportStatistics().mbOpen('maya')
        else:
            export_statistics.exportStatistics().mbOpen('standalone')
        
        self.types = types.Types()
        
        if load_from_scene:
            self.main_window.load_scene_btn.setVisible(True)
        else:
            self.main_window.load_scene_btn.setVisible(False)
        
        #Get the repositories
        repos_list = ['tst','sw']
        self.main_window.project_combo.addItems(repos_list)
        self.main_window.project_combo.activated.connect(self.loadConfigPrefs)
         

        self.start_frame = None
        self.end_frame = None
         
        #Icons
        ui_utils.reloadInterfaceIcons(self.main_window.config_button, "config_icon.png")
        ui_utils.reloadInterfaceIcons(self.main_window.title_label, "magicButton_icon.png", h=80)
        
        #Signals
        self.connect(self.main_window.reset_btn, QtCore.SIGNAL('released()'), lambda: self.clearViews(breakdown=True, stack=True, render=True, tree=True, properties=True, search=True))
        self.connect(self.main_window.load_btn, QtCore.SIGNAL('released()'), self.loadShotInfo)
        self.connect(self.main_window.config_button, QtCore.SIGNAL('released()'), lambda: self.config_ui.initializeWindow())
        self.main_window.input_shot.returnPressed.connect(self.loadShotInfo)
        self.main_window.input_sequence.returnPressed.connect(self.loadShotInfo)
        self.main_window.prefs_combo.activated.connect(self.configPrefsChangedCallback)
        self.connect(self.main_window.launch_btn, QtCore.SIGNAL('released()'), self.launchCallback)
        
        #Drag and Drop Splitter - Horizontal
        self.dd_splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.dd_splitter.addWidget(self.createBreakdownView())
        self.dd_splitter.addWidget(self.createStackView())
        self.dd_splitter.addWidget(self.createRenderView())
        self.dd_splitter.setSizes([150, 150, 150])
        #self.dd_layout.addWidget(self.dd_splitter)
        
        #Node Editor Spliter - Horizontal
        self.node_splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.node_splitter.addWidget(self.createTreeView())
        self.node_splitter.addWidget(self.createNodePropertiesPanel())
        self.node_splitter.setSizes([200, 200])
        
        #Main Splitter - Vertical
        self.main_splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.main_splitter.addWidget(self.dd_splitter)
        self.main_splitter.addWidget(self.node_splitter)
        self.main_splitter.setSizes([120, 300])
        
        self.main_window.main_layout.addWidget(self.main_splitter)
        
        self.loadConfigPrefs()
        self.config_ui = config_win.ConfigUI(self.config)

        


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    testApp = DispatcherUI()
    app.installEventFilter(testApp)
    app.exec_()