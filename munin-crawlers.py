#!/usr/bin/python3

import json, sys, os
import datetime

class Monitor(object):
    file_name = ''
    periods = []
    useragents = {}
    limitloglines = 25000

    def __init__(self):
        self.file_name = os.environ.get('file_name')
        for i in range(1,6):
            time = datetime.datetime.now() - datetime.timedelta(minutes=i)
            self.periods.append(time.strftime("[%d/%b/%Y:%H:%M:"))

    def __classifie_user_agent(self,useragent):
        if 'Googlebot'.lower() in useragent.lower():
            return 'Googlebot'
        if 'AhrefsBot'.lower() in useragent.lower():
            return 'AhrefsBot'
        if 'SemrushBot'.lower() in useragent.lower():
            return 'SemrushBot'
        if 'bingbot'.lower() in useragent.lower():
            return 'bingbot'
        if 'aspiegel'.lower() in useragent.lower():
            return 'aspiegel'
        if 'Applebot'.lower() in useragent.lower():
            return 'Applebot'
        else:
            return 'others'

    def __check_if_string_in_file(self):
        useragents_desordered = {}
        with open(self.file_name, 'r') as read_obj:
            for line in (read_obj.readlines() [-self.limitloglines:]):
                if any(time in line for time in self.periods):
                    line = line.replace("\r","")
                    line = line.replace("\t","")
                    line = line.replace("\n","")
                    line = line.replace("\\","")
                    try:
                        data_json = json.loads(line)
                        useragents_desordered[All] += 1
                        if 'bot' in data_json['userAgent'].lower():
                            UserAgent = self.__classifie_user_agent(data_json['userAgent'])
                            if UserAgent in useragents_desordered:
                                useragents_desordered[UserAgent] += 1
                            else:
                                useragents_desordered[UserAgent] = 1
                    except:
                        pass
        if not 'others' in useragents_desordered:
            useragents_desordered['others']=0
        self.useragents = sorted(useragents_desordered.items(), key=lambda x: x[1], reverse=True)

    def printValue(self):
        self.__check_if_string_in_file(self.file_name)
        for key in self.useragents:
            if key:
                print("{}.value {}".format(key[0],key[1]))

    def __setconfOrder(self):
        order = "graph_order others"
        for item in self.useragents:
            if (str(item[0]) != 'others'):
                order += " " + str(item[0])
        order += "\n"
        return order

    def printConf(self):
        self.__check_if_string_in_file(self.file_name)
        config = "graph_title " + " Crawlers\n"\
        "graph_args --base 1000 -r --lower-limit 0\n"\
        "graph_vlabel number of Crawlers Request\n"\
        "graph_period second\n"\
        "graph_category " + "system\n"
        config += self.__setconfOrder()
        for item in self.useragents:
            config += item[0]+".label " + item[0] + "\n"
            if (item[0] == 'All'):
                config += item[0]+".draw " + "LINE1" + "\n"
            if (item[0] == 'others'):
                config += item[0]+".draw " + "AREA" + "\n"
            else:
                config += item[0]+".draw " + "STACK" + "\n"
            config += item[0]+".type " + "GAUGE" + "\n"
        return config[:-1]

if __name__ == '__main__':
    UserAgents = Monitor()
    if len(sys.argv) < 2:
        UserAgents.printValue()
    elif sys.argv[1] == "config":
        print(UserAgents.printConf())
    else:
        print("Wrong Args")
