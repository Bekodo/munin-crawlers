#!/usr/bin/python3

import json
import sys
import os
import datetime

class Monitor:
    def __init__(self):
        self.file_name = os.environ.get('file_name')
        self.periods = []
        self.useragents = {}
        self.limitloglines = 5000
        self.listuseragents = [
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
            'AwarioBot'
        ]
        self.botstrings = ['bot', 'craw']
        
        for i in range(1,6):
            time = datetime.datetime.now() - datetime.timedelta(minutes=i)
            self.periods.append(time.strftime("[%d/%b/%Y:%H:%M:"))

    def __classify_user_agent(self, useragent):
        for value in self.listuseragents:
            if value.lower() in useragent.lower():
                return value
        for bot in self.botstrings:
            if bot in useragent:
                return 'others'
        return None

    def __check_if_string_in_file(self):
        useragents_count = {'others': 0, 'Total': 0}

        try:
            with open(self.file_name, 'r') as read_obj:
                # Leer las últimas limitloglines líneas del archivo
                lines = read_obj.readlines()[-self.limitloglines:]
        except FileNotFoundError:
            print(f"File {self.file_name} not found.")
            return
        except Exception as e:
            print(f"Error reading file {self.file_name}: {e}")
            return

        for line in lines:
            if any(time in line for time in self.periods):
                try:
                    data_json = json.loads(line)
                    useragents_count['Total'] += 1
                    user_agent = data_json.get('userAgent', '').lower()
                    classified_user_agent = self.__classify_user_agent(user_agent)
                    if classified_user_agent:
                        useragents_count[classified_user_agent] = useragents_count.get(classified_user_agent, 0) + 1
                except json.JSONDecodeError:
                    continue

        self.useragents = sorted(useragents_count.items(), key=lambda x: x[1], reverse=True)

    def printValue(self):
        self.__check_if_string_in_file()
        for key, value in self.useragents:
            print(f"{key}.value {value}")

    def __setconfOrder(self):
        order = "graph_order others"
        for item in self.useragents:
            if item[0] not in ('others', 'Total'):
                order += f" {item[0]}"
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
            config += f"{item[0]}.label {item[0]}\n"
            if item[0] == 'others':
                config += f"{item[0]}.draw AREA\n"
            elif item[0] == 'Total':
                config += (
                    f"{item[0]}.draw LINE1\n"
                    f"{item[0]}.colour 454545\n"
                )
            else:
                config += f"{item[0]}.draw STACK\n"
            config += f"{item[0]}.type GAUGE\n"
        return config.strip()

if __name__ == '__main__':
    UserAgents = Monitor()
    if len(sys.argv) < 2:
        UserAgents.printValue()
    elif sys.argv[1] == "config":
        print(UserAgents.printConf())
    else:
        print("Wrong Args")
