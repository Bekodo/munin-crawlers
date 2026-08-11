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

# 200 is never stacked — the gap between the Total line and the top of the
# stack below is exactly the 200 traffic. Every other known code gets a
# fixed shade from its range's palette (darkest first), so colours stay
# stable across polls regardless of which codes show up in a given window.
RANGE_PALETTES = {
    '2': ['1B5E20', '2E7D32', '388E3C', '43A047', '4CAF50', '66BB6A', '81C784', 'A5D6A7', 'C8E6C9'],  # green
    '3': ['0D47A1', '1565C0', '1976D2', '1E88E5', '2196F3', '42A5F5', '64B5F6', '90CAF9', 'BBDEFB'],  # blue
    '4': ['4A148C', '6A1B9A', '7B1FA2', '8E24AA', '9C27B0', 'AB47BC', 'BA68C8', 'CE93D8', 'E1BEE7'],  # purple
    '5': ['B71C1C', 'C62828', 'D32F2F', 'E53935', 'F44336', 'EF5350', 'E57373', 'EF9A9A', 'FFCDD2'],  # red
}


def _build_code_colours(labels):
    colours = {}
    for range_digit, palette in RANGE_PALETTES.items():
        codes_in_range = sorted(code for code in labels if code.startswith(range_digit) and code != '200')
        for shade, code in zip(palette, codes_in_range):
            colours[code] = shade
    return colours


CODE_COLOURS = _build_code_colours(STATUS_LABELS)
# 200 gets its own field too (so it has a real legend row with Cur/Min/Avg/Max),
# drawn as a LINE with low alpha (~19% opacity) instead of a full colour — the
# alpha channel affects the legend swatch too (confirmed against a real
# munin-node run), so alpha 00 left the legend entry with no colour at all.
# This keeps the line faint on the graph while still giving the legend a
# visibly green swatch. Bump the last byte (00-ff) to taste.
CODE_COLOURS['200'] = '4CAF5030'


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
        if status not in self.statuslabels:
            return None
        return status

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
        status_count = {'Total': 0}

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
            if classified_status:
                status_count[classified_status] = status_count.get(classified_status, 0) + 1

        self.statuscodes = sorted(
            ((field, value) for field, value in status_count.items() if value > 0 or field == 'Total'),
            key=lambda item: item[1],
            reverse=True,
        )

    def printValue(self):
        self.__check_if_string_in_file()
        for field, value in self.statuscodes:
            print(f"{field_id(field)}.value {value}")

    def __ordered_fields(self):
        # Stack from 2xx up to 5xx (bottom to top). 200 is not part of that
        # stack — it's an invisible LINE — so it's placed after it, and
        # Total always last so its LINE1 paints on top of everything.
        fields_present = [field for field, _ in self.statuscodes if field != 'Total']
        error_fields = sorted((field for field in fields_present if field != '200'), key=lambda code: int(code))
        ordered = error_fields
        if '200' in fields_present:
            ordered = ordered + ['200']
        return ordered + ['Total']

    def __setconfOrder(self):
        return "graph_order " + " ".join(field_id(field) for field in self.__ordered_fields()) + "\n"

    def __label_for(self, field):
        if field == 'Total':
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
        ordered = self.__ordered_fields()
        config += self.__setconfOrder()
        for field in ordered:
            fid = field_id(field)
            config += f"{fid}.label {self.__label_for(field)}\n"
            if field == 'Total':
                config += (
                    f"{fid}.draw LINE1\n"
                    f"{fid}.colour 454545\n"
                )
            elif field == '200':
                # Not part of the stack: a faint low-alpha line, mainly for
                # its legend row — the 200 traffic itself is still visually
                # the gap between the top of the error stack and Total.
                config += (
                    f"{fid}.draw LINE1\n"
                    f"{fid}.colour {CODE_COLOURS[field]}\n"
                )
            else:
                # The first stacked series must be an AREA to give the stack
                # a base; every series after it stacks on top via STACK.
                draw = 'AREA' if field == ordered[0] else 'STACK'
                config += (
                    f"{fid}.draw {draw}\n"
                    f"{fid}.colour {CODE_COLOURS[field]}\n"
                )
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
