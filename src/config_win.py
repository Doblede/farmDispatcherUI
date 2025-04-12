'''
@author: David De Juan
'''

from PySide import QtCore
from PySide import QtGui
from PySide import QtUiTools
import os
from libs import config_logic



class ConfigUI(QtGui.QMainWindow):

    def __init__(self, config, parent=None):
        super(ConfigUI, self).__init__(parent)
        
        self.config = config
        loader = QtUiTools.QUiLoader()
        
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', 'gui'))
        uiFile = QtCore.QFile(os.path.join(path, 'directories_settings_ui.ui'))
        uiFile.open(QtCore.QFile.ReadOnly)
        self.main_window = loader.load(uiFile)

        
    def initializeWindow(self):
        #Icons
        self.reloadInterfaceIcons(self.main_window.def_dir_btn, "folder_icon.png")
        self.reloadInterfaceIcons(self.main_window.def_trees_btn, "folder_icon.png")
        self.reloadInterfaceIcons(self.main_window.def_nodes_btn, "folder_icon.png")
        
        #Set current paths
        self.main_window.def_dir_path.setText(self.config.getPrefsPath())
        self.main_window.def_trees_path.setText(self.config.getTreesPath())
        self.main_window.def_nodes_path.setText(self.config.getNodesPath())
        
        #Signals
        self.main_window.connect(self.main_window.def_dir_btn, QtCore.SIGNAL('released()'), lambda: self.selectDirectory(self.main_window.def_dir_path))
        self.main_window.connect(self.main_window.def_trees_btn, QtCore.SIGNAL('released()'), lambda: self.selectDirectory(self.main_window.def_trees_path))
        self.main_window.connect(self.main_window.def_nodes_btn, QtCore.SIGNAL('released()'), lambda: self.selectDirectory(self.main_window.def_nodes_path))
        self.main_window.connect(self.main_window.save_btn, QtCore.SIGNAL('released()'), self.saveConfig)
        self.main_window.connect(self.main_window.reset_btn, QtCore.SIGNAL('released()'), self.resetConfig)
        self.main_window.connect(self.main_window.cancel_btn, QtCore.SIGNAL('released()'), lambda: self.main_window.close())
        
        self.main_window.connect(self.main_window.pre_btn, QtCore.SIGNAL('released()'), lambda: self.selectFarm(self.main_window.pre_btn))
        self.main_window.connect(self.main_window.dev_btn, QtCore.SIGNAL('released()'), lambda: self.selectFarm(self.main_window.dev_btn))
        self.main_window.connect(self.main_window.prod_btn, QtCore.SIGNAL('released()'), lambda: self.selectFarm(self.main_window.prod_btn))
        self.main_window.connect(self.main_window.none_btn, QtCore.SIGNAL('released()'), lambda: self.selectFarm(self.main_window.none_btn))
        
        #Show window
        self.main_window.show()
        
        
    def selectFarm(self, btn):
        farm = btn.text()
        self.config.setFarmRenderIndex(farm)
        
        
    def selectDirectory(self, path_qline):
        path = path_qline.text()
        if not os.path.exists(path):
            os.makedirs(path)
        dialog = QtGui.QFileDialog()
        #dialog.setFileMode(QtGui.QFileDialog.AnyFile)
        #dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
        directory = dialog.getExistingDirectory(self, 'Choose Directory', path)
        if directory==None or directory=="":
            directory = path        
        path_qline.setText(directory)


    def saveConfig(self):
        self.config.setPrefsPath(self.main_window.def_dir_path.text())
        self.config.setTreesPath(self.main_window.def_trees_path.text())
        self.config.setNodesPath(self.main_window.def_nodes_path.text())
        self.main_window.close()
        
        
    def resetConfig(self):
        self.config = config_logic.ConfigLogic()
        self.main_window.def_dir_path.setText(self.config.getPrefsPath())
        self.main_window.def_trees_path.setText(self.config.getTreesPath())
        self.main_window.def_nodes_path.setText(self.config.getNodesPath())
        
        
    def reloadInterfaceIcons(self, widget, iconPath, w=None, h=None):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', 'icons'))
        pixmap = QtGui.QPixmap(os.path.join(path, iconPath))
        if w:
            pixmap = pixmap.scaledToWidth(w, mode = QtCore.Qt.SmoothTransformation)
        if h:
            pixmap = pixmap.scaledToHeight(h, mode = QtCore.Qt.SmoothTransformation)
        if 'QPushButton' in type(widget).__name__:
            tool_icon = QtGui.QIcon()
            tool_icon.addPixmap(pixmap)
            widget.setIcon(tool_icon)
        elif 'QLabel' in type(widget).__name__:
            widget.setPixmap(pixmap)