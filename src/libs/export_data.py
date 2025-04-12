'''
@author: David De Juan
'''
import os
import json, copy
import types
import time
import datetime
from libs import export_statistics

'''
#Proceso de output
job_fields = {"[showName]": rep_short, "[fileType]": "cfxrender", "[shotName]": seq_name + shot_num,
                  "[description]": anim_block}
process_name = getJobName("cfxOutputSceneHair", job_fields)
'''

def getJobName(jobtype, fields):
    job_name = "EsteEsElJobName"
    return job_name


def applyPropertyOverrides(original_node, override_node):
    copy_from_node = copy.deepcopy(original_node)
    for key in copy_from_node.keys():
        if key in override_node.keys():
            copy_from_node[key] = override_node[key]
    return copy_from_node


def exportData(config, project, seq, shot, stack_l, render_l):
    
    start = time.clock()
    char_list = exportChars(project, seq, shot, stack_l)
    elapsed = time.clock()
    elapsed = elapsed - start
    print ("-- Time spent in export chars is: ", elapsed)


    start = time.clock()
    render_scene_list = exportRenders(project, seq, shot, render_l, char_list)
    elapsed = time.clock()
    elapsed = elapsed - start
    print ("-- Time spent in export renders is: ", elapsed)
    
    final_dict = {}
    final_dict.update({"chars": char_list})
    final_dict.update({"output_scene": render_scene_list})
    final_dict.update({"sequence": seq})
    final_dict.update({"shot": shot})
    final_dict.update({"queue_server": config.getQueueServer()}) #"queue_server": 'test' | 'visdev' | 'prod',
    #final_dict.update({"farm_render": config.getFarmRender()}) #"farm_render": 'DEV' | 'PREPROD' | 'PROD',
    final_dict.update({"repository": 'Amusement Park (amp)'})
    
    '''
    directory = r'Y:\\'+project+'\\seqs\\'+seq+'\\shots\\'+shot+'\\cfx\\magic_button'
    if not os.path.exists(directory):
        os.makedirs(directory)
    '''
    start = time.clock()
    
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M-%S')
    
    fileDir = os.path.dirname(os.path.realpath('__file__'))
    file_s = fileDir + r"\publish\magic_button_"+st+".json"
    #&file_s = r'Y:\\'+project+'\\seqs\\'+seq+'\\shots\\'+shot+'\\cfx\\magic_button\\magic_button_'+st+'.json'
    json_file_o = open(file_s, "w")
    json.dump(final_dict, json_file_o, sort_keys=True, indent=4, separators=(',', ': '))
    json_file_o.close()
    elapsed = time.clock()
    elapsed = elapsed - start
    print ("-- Time spent in writing the json is: ", elapsed)
    

    

             
def exportChars(project, seq, shot, stack_l):
    char_list = []
    hair_dict = {}
    cloth_dict = {}
    for stack_node in stack_l:
        tps = types.Types()
        for char in stack_node.getChildren():
            '''
            error_l = pre_checks.runPreCheks(project, seq, shot, char.name())
            if error_l:
                QtGui.QMessageBox.information(None, 'Error!', ' '.join(error_l), buttons = QtGui.QMessageBox.Ok)
            '''
            short_name, char_var, hairstyle = getCharInfoFromBreakdown(seq, shot, char.name())
            
            tree_nodes = stack_node.getProperty(tps.tree_nodes_key)
            hair_dict = {}
            cloth_dict = {}
            tree_node = tree_nodes
            while tree_node:
                cloth_node = {}
                hair_node = {}
                #CLOTH
                if tree_node.getProperty('group') == 'cloth':
                    if char.getProperty(tree_node.name()) and 'attributeList' in char.getProperty(tree_node.name()).keys():
                        attr_list = applyPropertyOverrides(tree_node.getProperty('attributeList'), char.getProperty(tree_node.name())['attributeList'])
                    else:
                        attr_list = tree_node.getProperty('attributeList')
                    if attr_list['enable']['value']:
                        for att in attr_list.keys():
                            #For each attribute
                            value = attr_list[att]
                            if value['attrType'] == 'bool':
                                #If the attributes is 'bool' type, we save it as string lowercase
                                cloth_node.update({att: bool(value['value'])})
                            elif value['attrType'] == 'path':
                                #If the attributes is 'path' type, we check it exist, if not we create it
                                if not value['value']:
                                    file_s = "EstoEsUnPath"
                                    cloth_node.update({att: file_s})
                                else:
                                    cloth_node.update({att: value['value'].replace('\\','/')})
                            else:
                                #If is another type, it is saved equal
                                cloth_node.update({att: value['value']})
                if cloth_node:
                    #We save the cloth node in the cloth dictionary
                    cloth_dict.update({tree_node.getProperty('nodeType'): cloth_node})
                    
                #HAIR
                if tree_node.getProperty('group') == 'hair':
                    if char.getProperty(tree_node.name()) and 'attributeList' in char.getProperty(tree_node.name()).keys():
                        attr_list = applyPropertyOverrides(tree_node.getProperty('attributeList'), char.getProperty(tree_node.name())['attributeList'])
                    else:
                        attr_list = tree_node.getProperty('attributeList')
                    if attr_list['enable']['value']:
                        for att in attr_list.keys():
                            #For each attribute
                            value = attr_list[att]
                            if value['attrType'] == 'hair_component_list':
                                #If the attributes is 'hair_component_list' type
                                hair_components_selected = value['value']
                                hair_components = value['options']
                                if hair_components_selected and len(hair_components_selected)==len(hair_components):
                                    #If all the components are selected, we don't save them because it will be via hairstyle
                                    hair_node.update({att: ''})
                                    hair_node.update({'hairstyle': char.getProperty('hairStyle')})
                                else:
                                    #Else we save the specific components
                                    hair_node.update({att: '|'.join(value['value'])})
                                    hair_node.update({'hairstyle': char.getProperty('hairStyle')})
                            elif value['attrType'] == 'bool':
                                #If the attributes is 'bool' type, we save it as string lowercase
                                hair_node.update({att: bool(value['value'])})
                            elif value['attrType'] == 'path':
                                #If the attributes is 'path' type, we check it exist, if not we create it
                                if not value['value']:
                                    #we have to create the path
                                    extra_d = {}
                                    extra_d["[showName]"] = project
                                    extra_d["[shotName]"] = seq + shot
                                    extra_d["[alias]"] = char.name()
                                    extra_d["[seqName]"] = seq
                                    extra_d["[shotNum]"] = shot
                                    extra_d["[cfxDescription]"] = value['description']
                                    file_s = "FilePath"
                                    hair_node.update({att: file_s})
                                else:
                                    hair_node.update({att: value['value'].replace('\\','/')})
                            else:
                                #If is another type, it is saved equal
                                hair_node.update({att: value['value']})    
                if hair_node:
                    #We save the hair node in the hair dictionary
                    hair_dict.update({tree_node.getProperty('nodeType'): hair_node})
                     
                #It continue with the next node in the tree
                tree_node = tree_node.getChildren()
                if tree_node:
                    tree_node = tree_node[0] 
            if cloth_dict:
                #cloth process name
                job_fields = {"[showName]": project, "[shotName]": seq + shot, "[alias]": char.name(), "[cfxDescription]": 'default'}
                process_name = getJobName("cfxCharCloth", job_fields)
                cloth_dict.update({'name': process_name})
            if hair_dict:
                #hair process name
                job_fields = {"[showName]": project, "[shotName]": seq + shot, "[alias]": char.name(), "[hairStyle]": hairstyle}
                process_name = getJobName("cfxCharHair", job_fields)
                hair_dict.update({'name': process_name})
                
            char_dict = {}
            char_dict.update({'alias': char.name()})
            char_dict.update({'hairstyle': char.getProperty('hairStyle')})
            char_dict.update({'shortName': short_name})
            char_dict.update({'rigCharVar': char_var})
            if cloth_dict:
                char_dict.update({'cloth': cloth_dict})
            if hair_dict:
                char_dict.update({'hair': hair_dict})
            char_list.append(char_dict)
    if cloth_dict:
        #cloth process name
        export_statistics.exportStatistics().launch('cloth', seq + shot)
    if hair_dict:
        #hair process name
        export_statistics.exportStatistics().launch('hair', seq + shot)
    return char_list

    
def getCharInfoFromBreakdown(seq, shot, alias):
    short_name = alias
    char_var = 'original'
    hairstyle = 'original'
    return short_name, char_var, hairstyle

    
    
def exportRenders(project, seq, shot, render_l, char_list):
    render_scene_l = []
    for render_node in render_l:
        attr_list = render_node.getProperty('attributeList')
        render_scene = {}
        if render_node.getChildren() and attr_list['enable']['value']:
            #char info
            render_scene['aliasCharList'] = []
            render_scene['hairstyleList'] = []
            render_scene['shortNameCharList'] = []
            render_scene['varCharList'] = []
            #elem info
            render_scene['aliasElemList'] = []
            render_scene['shortNameElemList'] = []
            render_scene['rigElemList'] = []
            render_scene['varElemList'] = []
            
            render_scene['charProcessList'] = []

            for char in render_node.getChildren():
                #Fulfill the char info
                short_name, char_var, hairstyle = getCharInfoFromBreakdown(seq, shot, char.name())
                render_scene['aliasCharList'].append(char.name())
                render_scene['shortNameCharList'].append(short_name)
                render_scene['varCharList'].append(char_var)
                render_scene['hairstyleList'].append(hairstyle)
                
                found = False
                index = 0
                char_process_l = []
                while not found and index<len(char_list):
                    if char.name() == char_list[index]['alias']:
                        found = True
                        if 'cloth' in char_list[index].keys() and 'name' in char_list[index]['cloth'].keys():
                            char_process_l.append(char_list[index]['cloth']['name'])
                        if 'hair' in char_list[index].keys() and 'name' in char_list[index]['hair'].keys():
                            char_process_l.append(char_list[index]['hair']['name'])
                    index = index+1
                    render_scene['charProcessList'] = render_scene['charProcessList']+char_process_l

            for att in attr_list.keys():
                #For each attribute
                value = attr_list[att]
                if value['attrType'] == 'bool':
                    #If the attributes is 'bool' type, we save it as string lowercase
                    render_scene.update({att: bool(value['value'])})
                else:
                    #If is another type, it is saved equal
                    render_scene.update({att: value['value']})
                if att == 'description':
                    description = value['value']
            if render_scene:
                job_fields = {"[showName]": project, "[fileType]": "cfxrender", "[shotName]": seq + shot, "[description]": description} 
                process_name = getJobName("cfxOutputSceneHair", job_fields)
                render_scene.update({'name': process_name})
                #render file path
                extra_d = {}
                extra_d["[showName]"] = project
                extra_d["[shotName]"] = seq + shot
                extra_d["[seqName]"] = seq
                extra_d["[shotNum]"] = shot
                extra_d["[description]"] = description
                file_s = "FilePath"
                render_scene.update({'path': file_s})
                
                #convert list to Mel string list
                #char info
                render_scene['aliasCharList'] = '|'.join(render_scene['aliasCharList'])
                i = 0
                for h in render_scene['hairstyleList']:
                    if not h:
                        render_scene['hairstyleList'][i] = ''
                    i = i+1
                render_scene['hairstyleList'] = '|'.join(render_scene['hairstyleList'])
                render_scene['shortNameCharList'] = '|'.join(render_scene['shortNameCharList'])
                render_scene['varCharList'] = '|'.join(render_scene['varCharList'])
                #elem info
                render_scene['aliasElemList'] = '|'.join(render_scene['aliasElemList'])
                render_scene['shortNameElemList'] = '|'.join(render_scene['shortNameElemList'])
                render_scene['rigElemList'] = '|'.join(render_scene['rigElemList'])
                render_scene['varElemList'] = '|'.join(render_scene['varElemList'])          
                     
        if render_node.getChildren() and attr_list['enable']['value'] and attr_list['submitRender']['value'] and 'submitRender' in render_node.getProperties().keys():
            submit_render_list = render_node.getProperty('submitRender')
            for att in submit_render_list.keys():
                if submit_render_list[att]['attrType'] == 'bool':
                    #If the attributes is 'bool' type, we save it as string lowercase
                    render_scene.update({att: bool(submit_render_list[att]['value'])})
                else:
                    render_scene.update({att: submit_render_list[att]['value']})
        if render_scene:
            render_scene_l.append(render_scene)            
            
    if render_scene_l:
        export_statistics.exportStatistics().launch('render', seq + shot)
    return render_scene_l



