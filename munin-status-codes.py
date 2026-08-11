#!/usr/bin/python3

import json
import re
import sys
import os
import datetime

from http_status_codes import STATUS_LABELS

LOG_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"
WINDOW_MINUTES = 5
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
        self.statuscodes = []
        self.limitloglines = 25000
        self.statuslabels = STATUS_LABELS

        if self.environment == 'dev':
            # Forzar la fecha específica para pruebas
            fixed_time_str = "10/Mar/2025:18:19:47 +0000"
            now_ref = datetime.datetime.strptime(fixed_time_str, LOG_TIME_FORMAT)
        else:
            now_ref = datetime.datetime.now(datetime.timezone.utc)

        self.window_start = now_ref - datetime.timedelta(minutes=WINDOW_MINUTES)

    def __classify_status(self, status):
        status = str(status).strip()
        if status in self.statuslabels:
            return status
        return 'others'

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
        status_count = {'others': 0, 'Total': 0}

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

            status_count['Total'] += 1
            status = data_json.get('status', '')
            classified_status = self.__classify_status(status)
            status_count[classified_status] = status_count.get(classified_status, 0) + 1

        self.statuscodes = sorted(
            ((field, value) for field, value in status_count.items() if value > 0 or field in ('others', 'Total')),
            key=lambda item: item[1],
            reverse=True,
        )

    def printValue(self):
        self.__check_if_string_in_file()
        for field, value in self.statuscodes:
            print(f"{field_id(field)}.value {value}")

    def __ordered_fields(self):
        status_fields = [field for field, _ in self.statuscodes if field not in ('others', 'Total')]
        return ['others'] + status_fields + ['Total']

    def __setconfOrder(self):
        return "graph_order " + " ".join(field_id(field) for field in self.__ordered_fields()) + "\n"

    def __label_for(self, field):
        if field in ('others', 'Total'):
            return field
        description = self.statuslabels.get(field, '')
        return f"{field} {description}".strip()

    def printConf(self):
        self.__check_if_string_in_file()
        config = (
            "graph_title HTTP Status Codes\n"
            "graph_args --base 1000 -r --lower-limit 0\n"
            "graph_vlabel number of Requests\n"
            "graph_period second\n"
            "graph_category system\n"
        )
        config += self.__setconfOrder()
        for field in self.__ordered_fields():
            fid = field_id(field)
            config += f"{fid}.label {self.__label_for(field)}\n"
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
    StatusCodes = Monitor()
    if len(sys.argv) < 2:
        StatusCodes.printValue()
    elif sys.argv[1] == "config":
        print(StatusCodes.printConf())
    else:
        print("Wrong Args")
        sys.exit(1)
