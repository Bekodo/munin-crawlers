#!/usr/bin/python3

import json
import sys
import os
import datetime

LOG_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"
WINDOW_MINUTES = 5

class Monitor:
    def __init__(self):
        self.file_name = os.environ.get('file_name')
        self.environment = os.environ.get('environment')
        self.useragents = {}
        self.limitloglines = 25000
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
            # Forzar la fecha específica para pruebas
            fixed_time_str = "10/Mar/2025:18:19:47 +0000"
            now_ref = datetime.datetime.strptime(fixed_time_str, LOG_TIME_FORMAT)
        else:
            now_ref = datetime.datetime.now(datetime.timezone.utc)

        self.window_start = now_ref - datetime.timedelta(minutes=WINDOW_MINUTES)

    def __classify_user_agent(self, useragent):
        useragent_lower = useragent.lower()
        for value in self.listuseragents:
            if value.lower() in useragent_lower:
                return value
        for bot in self.botstrings:
            if bot in useragent_lower:
                return 'others'
        return None

    def __parse_log_time(self, raw_time):
        try:
            return datetime.datetime.strptime(raw_time.strip('[]'), LOG_TIME_FORMAT)
        except (ValueError, TypeError):
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
            try:
                data_json = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_time = self.__parse_log_time(data_json.get('time', ''))
            if event_time is None or event_time < self.window_start:
                continue

            useragents_count['Total'] += 1
            user_agent = data_json.get('userAgent', '')
            classified_user_agent = self.__classify_user_agent(user_agent)
            if classified_user_agent:
                useragents_count[classified_user_agent] = useragents_count.get(classified_user_agent, 0) + 1

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
        sys.exit(1)