'''
@author: David De Juan
'''
class Types():
    
    def __init__(self):
        self.node_type_char = 'char'
        self.node_type_animblock = 'animblock'
        self.node_type_shot = 'shot'
        self.node_type_stack = 'stack'
        self.node_type_render = 'render'
        
        self.root_name_shot = 'Shot'
        self.root_name_stacks = 'Stacks'
        self.root_name_renders = 'Renders'
        
        self.hairstyle_ft = 'cfxhs'
        self.extension_hairstyle_file = 'json'
        
        #This key save the json name
        self.json_tree_key = 'jsontree'
        
        #This key save the databox tree nodes
        self.tree_nodes_key = 'treenodes'