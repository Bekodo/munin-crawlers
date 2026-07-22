#!/usr/bin/python3

import json
import re
import sys
import os
import datetime

from crawler_agents import LIST_USERAGENTS, BOT_STRINGS

LOG_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"
WINDOW_MINUTES = 5
MIN_CRAWLER_VALUE = 10
INVALID_FIELD_CHARS = re.compile(r'[^A-Za-z0-9_]')


def field_id(name):
    # Los nombres de campo de munin solo admiten [a-zA-Z0-9_], a diferencia de .label
    sanitized = INVALID_FIELD_CHARS.sub('_', name)
    if not sanitized or not (sanitized[0].isalpha() or sanitized[0] == '_'):
        sanitized = f'f_{sanitized}'
    return sanitized

class Monitor:
    def __init__(self):
        self.file_name = os.environ.get('file_name')
        self.environment = os.environ.get('environment')
        self.useragents = {}
        self.limitloglines = 25000
        self.listuseragents = LIST_USERAGENTS
        self.botstrings = BOT_STRINGS

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

    def __tail_lines(self, file_obj, num_lines):
        chunk_size = 65536
        file_obj.seek(0, os.SEEK_END)
        position = file_obj.tell()
        blocks = []
        newline_count = 0

        while position > 0 and newline_count <= num_lines:
            read_size = min(chunk_size, position)
            position -= read_size
            file_obj.seek(position)
            chunk = file_obj.read(read_size)
            blocks.append(chunk)
            newline_count += chunk.count(b'\n')

        data = b''.join(reversed(blocks))
        return data.splitlines()[-num_lines:]

    def __check_if_string_in_file(self):
        useragents_count = {'others': 0, 'Total': 0}

        try:
            with open(self.file_name, 'rb') as read_obj:
                # Leer solo las últimas limitloglines líneas, sin cargar el archivo entero
                raw_lines = self.__tail_lines(read_obj, self.limitloglines)
        except FileNotFoundError:
            print(f"File {self.file_name} not found.")
            return
        except Exception as e:
            print(f"Error reading file {self.file_name}: {e}")
            return

        lines = (raw_line.decode('utf-8', errors='replace') for raw_line in raw_lines)

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

        for field in list(useragents_count):
            if field not in ('others', 'Total') and 0 < useragents_count[field] <= MIN_CRAWLER_VALUE:
                useragents_count['others'] += useragents_count[field]
                useragents_count[field] = 0

        self.useragents = sorted(
            ((field, value) for field, value in useragents_count.items() if value > 0 or field in ('others', 'Total')),
            key=lambda item: item[1],
            reverse=True,
        )

    def printValue(self):
        self.__check_if_string_in_file()
        for field, value in self.useragents:
            print(f"{field_id(field)}.value {value}")

    def __ordered_fields(self):
        crawler_fields = [field for field, _ in self.useragents if field not in ('others', 'Total')]
        return ['others'] + crawler_fields + ['Total']

    def __setconfOrder(self):
        return "graph_order " + " ".join(field_id(field) for field in self.__ordered_fields()) + "\n"

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
        for field in self.__ordered_fields():
            fid = field_id(field)
            config += f"{fid}.label {field}\n"
            if field == 'others':
                config += f"{fid}.draw AREA\n"
            elif field == 'Total':
                config += (
                    f"{fid}.draw LINE1\n"
                    f"{fid}.colour 454545\n"
                )
            else:
                config += f"{fid}.draw STACK\n"
            config += f"{fid}.type GAUGE\n"
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