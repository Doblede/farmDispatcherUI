'''
@author: David De Juan
'''
import os
import json
                
class ConfigLogic():
    
    def __init__(self):
        #Render farm
        self.queue_server = ['test', 'visdev', 'prod', 'none']
        self.farm_render = ['DEV', 'PREPROD', 'PROD', 'NONE']
        self.index = 2
        
        fileDir = os.path.dirname(os.path.realpath('__file__'))
        #Config files path
        self.prefs_path = fileDir + r"\config\preferences"
        if os.path.isdir(self.prefs_path):
            self.prefs_files = []
            for file in os.listdir(self.prefs_path):
                if os.path.isfile(os.path.join(self.prefs_path, file)):
                    self.prefs_files.append(file)
        else:
            self.prefs_files = []
        self.pref_content = {} 
        self.trees_path = fileDir + r"\config\stacks"
        if os.path.isdir(self.trees_path):
            self.trees_files = []
            for file in os.listdir(self.trees_path):
                if os.path.isfile(os.path.join(self.trees_path, file)):
                    self.trees_files.append(file)
        else:
            self.trees_files = []
        self.tree_content = {} 
        
        self.nodes_path = fileDir + r"\config\nodes"
        if os.path.isdir(self.nodes_path):
            self.nodes_files = []
            for file in os.listdir(self.nodes_path):
                if os.path.isfile(os.path.join(self.nodes_path, file)):
                    self.nodes_files.append(file)
        else:
            self.nodes_files = []
        self.node_content = {} 
        
        
    def getQueueServer(self):
        return self.queue_server[self.index]
        
        
    def getFarmRender(self):
        return self.farm_render[self.index]
    
    
    def setFarmRenderIndex(self, farm):
        self.index = self.farm_render.index(farm)

        
    def getPrefsPath(self):
        return self.prefs_path
        
        
    def getTreesPath(self):
        return self.trees_path
    
    
    def getNodesPath(self):
        return self.nodes_path
    
    
    def setPrefsPath(self, prefs_path):
        self.prefs_path = prefs_path
        
        
    def setTreesPath(self, trees_path):
        self.trees_path = trees_path
    
    
    def setNodesPath(self, nodes_path):
        self.nodes_path = nodes_path
    
        
    def getPrefs(self):
        prefs_names = [p.replace('.json', '') for p in self.prefs_files]
        return prefs_names


    def loadPrefContent(self, pref):
        if os.path.isdir(self.prefs_path):
            found = False
            index = 0
            while not found and index<len(self.prefs_files):
                if pref in self.prefs_files[index]:
                    found = True
                else:
                    index = index+1
            json_data=open(self.prefs_path+'\\'+self.prefs_files[index]).read()
            self.pref_content = json.loads(json_data)


    def getPrefContent(self, pref):
        self.loadPrefContent(pref)
        return self.pref_content
    

    def getPrefTrees(self, pref):
        self.loadPrefContent(pref)
        return self.pref_content['trees']
    
    
    def getPrefRender(self, pref):
        self.loadPrefContent(pref)
        return self.pref_content['render']
    
    
    def loadTreeContent(self, tree):
        if os.path.isdir(self.trees_path):
            found = False
            index = 0
            while not found and index<len(self.trees_files):
                if tree in self.trees_files[index]:
                    found = True
                else:
                    index = index+1
            json_data=open(self.trees_path+'\\'+self.trees_files[index]).read()
            self.tree_content = json.loads(json_data)
        
        
    def getTreeNodes(self, tree):
        self.loadTreeContent(tree)
        return self.tree_content['nodes']
    
    
    def getExistingNodes(self):
        nodes_names = [p.replace('.json', '') for p in self.nodes_files]
        return nodes_names
    
    
    def getNodeByType(self, type):
        if os.path.isdir(self.nodes_path):
            found = False
            index = 0
            while not found and index<len(self.nodes_files):
                try:
                    json_data=open(self.nodes_path+'\\'+self.nodes_files[index]).read()
                    node_content = json.loads(json_data)
                    if type == node_content['nodeType']:
                        found = True
                    else:
                        index = index+1
                except:
                    print "Error in file:"+self.nodes_path+'\\'+self.nodes_files[index]
                    index = index+1
                
            return self.nodes_files[index].replace('.json', '')
        
    
    
    def getPropertyNode(self, node, property):
        if os.path.isdir(self.nodes_path):
            found = False
            index = 0
            while not found and index<len(self.nodes_files):
                if node == self.nodes_files[index].replace('.json', ''):
                    found = True
                else:
                    index = index+1
            json_data=open(self.nodes_path+'\\'+self.nodes_files[index]).read()
            node_content = json.loads(json_data)
            return node_content[property]