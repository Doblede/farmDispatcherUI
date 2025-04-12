'''
@author: David De Juan
'''
import getpass
import json
import time
import datetime


class exportStatistics():
    
    def __init__(self):
        self.user = None
    
    def getLogFile(self):
        return r"config\statistics\statistics.json"
    
    def getUser(self):
        if not self.user:
            self.user = getpass.getuser().lower()
        return self.user
    
    
    def ensureUserExistsInJson(self):
        json_data=open(self.getLogFile()).read()
        statistics = json.loads(json_data)
        if self.getUser() not in statistics.keys():
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H:%M:%S')
            statistics.update({self.getUser(): {"open_standalone": 0, "cloth": {"times": 0, "shots":[]}, "hair": {"times": 0, "shots":[]}, "render": {"times": 0, "shots":[]}, "open_in_maya": 0, "last_date": st}})
            json_file_o = open(self.getLogFile(), "w")
            json.dump(statistics, json_file_o, sort_keys=True, indent=4, separators=(',', ': '))
            json_file_o.close()
            
    
    def mbOpen(self, via):
        self.ensureUserExistsInJson() 
        json_data=open(self.getLogFile()).read()
        statistics = json.loads(json_data)
        if self.getUser() in statistics.keys():
            #the user is in the statistics
            if via == 'standalone':
                statistics[self.getUser()]['open_standalone'] = statistics[self.getUser()]['open_standalone']+1
            elif via == 'maya':
                statistics[self.getUser()]['open_in_maya'] = statistics[self.getUser()]['open_in_maya']+1
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H:%M:%S')
            statistics[self.getUser()]["last_date"] = st
            #write de json
            json_file_o = open(self.getLogFile(), "w")
            json.dump(statistics, json_file_o, sort_keys=True, indent=4, separators=(',', ': '))
            json_file_o.close()
            
            
    def launch(self, type, shot):
        #type can be: 'cloth', 'hair', 'render'
        self.ensureUserExistsInJson() 
        json_data=open(self.getLogFile()).read()
        statistics = json.loads(json_data)
        if self.getUser() in statistics.keys():
            #the user is in the statistics
            statistics[self.getUser()][type]['times'] = statistics[self.getUser()][type]['times']+1
            if shot not in statistics[self.getUser()][type]['shots']:
                statistics[self.getUser()][type]['shots'].append(shot)
            #write de json
            json_file_o = open(self.getLogFile(), "w")
            json.dump(statistics, json_file_o, sort_keys=True, indent=4, separators=(',', ': '))
            json_file_o.close()