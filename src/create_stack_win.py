'''
@author: David De Juan
'''
from PySide import QtCore
from PySide import QtGui
from PySide import QtUiTools
import os

class CreateStackUI(QtGui.QDialog):

    def __init__(self, items=[], parent=None):
        QtGui.QDialog.__init__(self, parent)
        loader = QtUiTools.QUiLoader()
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', 'gui'))
        uiFile = QtCore.QFile(os.path.join(path, 'create_stack_win.ui'))
        uiFile.open(QtCore.QFile.ReadOnly)
        self.ui = loader.load(uiFile)
        uiFile.close()
        self.ui.setWindowTitle("Create a new Stack")
        self.ui.setFixedSize(300, 130)
        self.ui.stack_combo.addItems(items)


    @staticmethod
    def getStackProperties(items=[], parent=None):
        #Dialog stuff
        dialog = CreateStackUI(items, parent).ui
        result = dialog.exec_()

        accepted = False
        stack_name = ""
        stack_type = ""
        if result == QtGui.QDialog.Accepted:
            accepted = True
            stack_name = dialog.stack_name_line.text()
            stack_type = dialog.stack_combo.currentText()
        return (accepted, stack_name, stack_type)