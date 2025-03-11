#!/usr/bin/python2

import json
import sys
import os
import datetime

class Monitor:
    def __init__(self):
        self.file_name = os.environ.get('file_name')
        self.environment = os.environ.get('environment')
        self.periods = []
        self.useragents = {}
        self.limitloglines = 5000
        self.listuseragents = {
            'Googlebot',
            'AhrefsBot',
            'SemrushBot',
            'bingbot',
            'aspiegel',
            'Applebot',
            'AMPHTML',
            'mj12bot',
            'Twitterbot',
            'BLEXBot',
            'DotBot',
            'GPTBot',
            'Amazonbot',
            'Siteimprove',
            'SeekportBot',
            'yandex',
            'ClaudeBot',
            'facebookexternalhit',
            'UptimeRobot',
            'GoogleOther',
            'AwarioBot',
            'Yeti',
            'meta'
        }
        self.botstrings = {'bot', 'craw'}

        if self.environment == 'dev':
            fixed_time_str = "10/Mar/2025:18:19:47"
            fixed_time = datetime.datetime.strptime(fixed_time_str, "%d/%b/%Y:%H:%M:%S")
            
            for i in range(1, 6):
                time = fixed_time - datetime.timedelta(minutes=i)
                self.periods.append(time.strftime("[%d/%b/%Y:%H:%M:"))
        else:        
            for i in range(1,6):
                time = datetime.datetime.now() - datetime.timedelta(minutes=i)
                self.periods.append(time.strftime("[%d/%b/%Y:%H:%M:"))

    def __classify_user_agent(self, useragent):
        useragent_lower = useragent.lower()
        for value in self.listuseragents:
            if value.lower() in useragent_lower:
                return value
        for bot in self.botstrings:
            if bot in useragent_lower:
                return 'others'
        return None

    def __check_if_string_in_file(self):
        useragents_count = {'others': 0, 'Total': 0}

        try:
            with open(self.file_name, 'r') as read_obj:
                lines = read_obj.readlines()[-self.limitloglines:]
        except FileNotFoundError:
            print "File %s not found." % self.file_name
            return
        except Exception as e:
            print "Error reading file %s: %s" % (self.file_name, str(e))
            return

        for line in lines:
            if any(time in line for time in self.periods):
                try:
                    data_json = json.loads(line)
                    useragents_count['Total'] += 1
                    user_agent = data_json.get('userAgent', '')
                    classified_user_agent = self.__classify_user_agent(user_agent)
                    if classified_user_agent:
                        useragents_count[classified_user_agent] = useragents_count.get(classified_user_agent, 0) + 1
                except ValueError:
                    continue

        self.useragents = sorted(useragents_count.items(), key=lambda x: x[1], reverse=True)

    def printValue(self):
        self.__check_if_string_in_file()
        for key, value in self.useragents:
            print "%s.value %d" % (key, value)

    def __setconfOrder(self):
        order = "graph_order others"
        for item in self.useragents:
            if item[0] not in ('others', 'Total'):
                order += " %s" % item[0]
        order += "\n"
        return order

    def printConf(self):
        self.__check_if_string_in_file()
        config = (
            "graph_title Total Request\n"
            "graph_args --base 1000 -r --lower-limit 0\n"
            "graph_vlabel number of Request\n"
            "graph_period second\n"
            "graph_category system\n"
        )
        config += self.__setconfOrder()
        for item in self.useragents:
            config += "%s.label %s\n" % (item[0], item[0])
            if item[0] == 'others':
                config += "%s.draw AREA\n" % item[0]
            elif item[0] == 'Total':
                config += (
                    "%s.draw LINE1\n"
                    "%s.colour 454545\n" % (item[0], item[0])
                )
            else:
                config += "%s.draw STACK\n" % item[0]
            config += "%s.type GAUGE\n" % item[0]
        return config.strip()

if __name__ == '__main__':
    UserAgents = Monitor()
    if len(sys.argv) < 2:
        UserAgents.printValue()
    elif sys.argv[1] == "config":
        print UserAgents.printConf()
    else:
        print "Wrong Args"
        sys.exit(1)