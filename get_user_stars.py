
from argparse import ArgumentParser
from http.client import HTTPSConnection
from logging.handlers import TimedRotatingFileHandler
from logging import StreamHandler
import logging
import urllib
import socket
import shlex
import json
import time
import sys
import os

USER = "mpenning"
PER_PAGE = 15

def initialize_py_logging():
    # ref -> https://stackoverflow.com/a/46098711/667301

    # Python logging deep dive ->
    #     https://coralogix.com/blog/python-logging-best-practices-tips/

    # Techniques in this method require python >= 3.3
    py_version = tuple(sys.version_info)
    assert py_version[0]==3 and py_version[1]>=3

    logging.root.handlers = []     # Zero-out any other logging configuration
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)s [%(module)s.%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            TimedRotatingFileHandler('debug.log', when='D', backupCount=5),
            StreamHandler(stream=sys.stdout)
        ]
    )

    return logging.getLogger(__name__)

class TTable(object):

    def __init__(self, table_data=(), table_headers=None, per_page=PER_PAGE):
        # Based on https://stackoverflow.com/a/70937740/667301
        assert isinstance(table_headers, (list, tuple,))

        global PER_PAGE
        PER_PAGE = per_page

        self.table_data = table_data
        self.table_headers = table_headers # This should be a list of dict keys
        self.col_widths = []
        self.per_page = per_page

        assert self.check_valid_table_data() is True

    def check_valid_table_data(self):
        """The type of the table_data variable must be a list or tuple.  Look inside self.table_data and check all entry value types."""

        if isinstance(self.table_data, (list, tuple,)):

            # Check inside self.table_data and ensure all values are good...
            for data_entry in self.table_data:
                assert isinstance(data_entry, dict)

                # Ensure all values are the correct type...
                for field_name in self.table_headers:
                    data_value = data_entry.get(field_name, None)
                    assert isinstance(data_value, (str, float, int, bool))

            return True

        else:
            print("TTable.check_valid_table_data(): table_data='{}'".format(self.table_data))
            raise ValueError("    The table_data dicts must be in a list, but type: {0} was found".format(type(self.table_data)))

    def initialize_column_widths(self):
        # get max col width for each field in header
        col_widths = []
        for field_name in self.table_headers:
            field_name_len = 0
            for data_entry in self.table_data:
                this_entry_len = len(str(data_entry[field_name]))
                if this_entry_len > field_name_len:
                    field_name_len = this_entry_len
            col_widths.append(field_name_len + 1)
        return col_widths


    # Based on https://stackoverflow.com/a/70937740/667301
    def render(self):
        """
        Render the data table to STDOUT as a multi-line string.
        """

        self.col_widths = self.initialize_column_widths()

        # default numeric header if table_headers was missing
        if self.table_headers is None:
            # Use column numbers...
            header_widths = range(1, len(self.col_widths)+1)
        else:
            header_widths = map(lambda x: len(str(x)), self.table_headers)

        # correct column width if table_headers are longer
        self.col_widths = [max(c,h) for c,h in zip(self.col_widths, header_widths)]

        # FIXME This should probably be called in user code...
        self.print_table()

    def print_table(self):

        table_text = ""

        # create separator line
        header_line = '+%s+' % '+'.join('-'*(w+2) for w in self.col_widths)
        #line = '-' * (sum(col_widths)+(len(col_widths)-1)*3+4)

        header_fmt_str = '| {0} |'.format(' | '.join(f'{{:<{ii}}}' for ii in self.col_widths))

        # render the top table_header names...
        print(header_line)
        print(header_fmt_str.format(*self.table_headers))
        print(header_line)

        # print all table data
        for data_entry in self.table_data:
            table_line = self.build_table_line(data_entry)
            print(table_line)

        # render the bottom table line...
        print(header_line)


    def build_table_line(self, data_entry=None):
        """Extract values to build a table line string from the data_entry dict"""

        # Initialize the table_line variable for each entry...
        table_line = '|'

        for idx, field_name in enumerate(self.table_headers):

            field_value = data_entry.get(field_name, None)
            # Ensure that this field_data is a supported type...
            assert isinstance(field_value, (str, float, int, bool))

            # Left-justify strings, right-justify all others...
            if isinstance(field_value, str):
                # append a properly-formatted table cell, per field...
                table_line += ' {{:<{0}}} |'.format(self.col_widths[idx]).format(field_value)
            else:
                # append a properly-formatted table cell, per field...
                table_line += ' {{:>{0}}} |'.format(self.col_widths[idx]).format(field_value)

        return table_line

def parse_args(input_str=""):
    """Parse CLI arguments, or parse args from the input_str variable"""

    ## input_str is useful if you don't want to parse args from the shell
    if input_str != "":
        # Example: parse_args("create -f this.txt -b")
        sys.argv = [input_str]  # sys.argv[0] is always the whole list of args
        sys.argv.extend(shlex.split(input_str))  # shlex adds the rest of argv

    parser = ArgumentParser(
        prog=os.path.basename(__file__),
        description="Help string placeholder",
        add_help=True,
    )

    ## Create a master subparser for all commands
    commands = parser.add_subparsers(help="commands", dest="command")

    ### Create a create command and its required and *optional* arguments...
    create = commands.add_parser("create", help="Create a foo")
    ## Make a required argument
    create_required = create.add_argument_group("required")
    create_required.add_argument(
        "-f", "--file", required=True, type=FileType("w"), help="Foo file name"
    )  # Write mode
    ## Make mutually exclusive optional arguments
    create_optional = create.add_argument_group("optional")
    ## NOTE: Mutually exclusive args *must* be optional
    create_exclusive = create_optional.add_mutually_exclusive_group()
    create_exclusive.add_argument(
        "-b",
        "--bar",
        action="store_true",
        default=False,
        required=False,
        help="bar a created foo",
    )
    create_exclusive.add_argument(
        "-z",
        "--baz",
        action="store_true",
        default=False,
        required=False,
        help="baz a created foo",
    )

    ### Create an append command and its arguments...
    append = commands.add_parser("append", help="Append a foo")
    append_required = append.add_argument_group("required arguments")
    append_required.add_argument(
        "-f",
        "--file",
        help="Foo file name",
        action="store",
        type=FileType("a"),
        required=True,
    )  # Append mode...

    ### Create an secure command and its arguments...
    secure = commands.add_parser("secure", help="Secure a foo")
    secure_required = secure.add_argument_group("required arguments")
    secure_required.add_argument(
        "-f",
        "--file",
        help="Foo file name",
        action="store",
        type=FileType("r"),
        required=True,
    )  # Read-only mode
    ## Multiple choices for secure 'level'
    secure_required.add_argument(
        "-l",
        "--level",
        help="Foo file security level",
        action="store",
        type=str,
        required=True,
        choices=["public", "private"],
    )

    ## Create an upload command, and its arguments...
    upload = commands.add_parser("upload", help="Upload a foo")
    upload.add_argument(
        "-f",
        "--file",
        required=True,
        default="",
        type=FileType("r"),
        help="foo file name",
    )  # Read-only mode

    return parser.parse_args()

def mktable(data, header=None):
    assert isinstance(header, (list, tuple,))

    try:
        assert isinstance(data, (list, tuple,))
    except AssertionError:
        print("mktable FATAL: data='{}'".format(data))
        print(data)
        raise ValueError("    The table data must be in a list or tuple, but type: {0} was submitted".format(type(data)))

    # e
    for entry in data:
        for field in header:
            assert entry[field] is not None
            assert isinstance(entry.get(field, None), (str, float, int, bool))

    # get max col width for each field in header
    col_widths = []
    for header_name in header:
        header_name_len = 0
        for entry in data:
            this_entry_len = len(str(entry[header_name]))
            if this_entry_len > header_name_len:
                header_name_len = this_entry_len
        col_widths.append(header_name_len + 1)

    # default numeric header if missing
    if not header:
        header = range(1, len(col_widths)+1)

    header_widths = map(lambda x: len(str(x)), header)

    # correct column width if headers are longer
    col_widths = [max(c,h) for c,h in zip(col_widths, header_widths)]

    # create separator line
    line = '+%s+' % '+'.join('-'*(w+2) for w in col_widths)
    #line = '-' * (sum(col_widths)+(len(col_widths)-1)*3+4)

    header_fmt_str = '| {0} |'.format(' | '.join(f'{{:<{ii}}}' for ii in col_widths))

    # table header line...
    print(line)
    print(header_fmt_str.format(*header))
    print(line)

    # print all table data
    for entry in data:
        assert isinstance(entry, dict)
        for field in header:
            entry_line = '|'
            for idx, field in enumerate(header):
                # append a properly-formatted table cell, per field...
                field_data = entry.get(field, None)
                # Ensure that this dict entry has a key named field...
                assert field_data is not None
                # Ensure that this field_data is a supported type...
                assert isinstance(field_data, (str, float, int, bool))
                # Left-justify strings, right-justify all others...
                if isinstance(field_data, str):
                    entry_line += ' {{:<{0}}} |'.format(col_widths[idx]).format(field_data)
                else:
                    entry_line += ' {{:>{0}}} |'.format(col_widths[idx]).format(field_data)
        print(entry_line)

    # table footer line...
    print(line)

if __name__=="__main__":
    # Read a github users' stars as json and print to STDOUT
    #
    # This script is intentionally rate-limited to comply with
    # github's un-authenticated rate-limits.  A future improvement
    # will be scraping user stars via github API token.

    all_stars = []
    finished = False
    json_page = 1
    github_http_host = "api.github.com"

    log = initialize_py_logging()
    log.info("Making HTTPSConnection() to {}".format(github_http_host))

    while not finished:
        params = {"per_page": PER_PAGE, "page": json_page,}
        url = '/users/{0}/starred?{1}'.format("mpenning", urllib.parse.urlencode(params))
        headers = {'Content-type': 'application/json',
                   'User-Agent': 'python-http.client.HTTPSConnection',
        }
        try:
            conn = HTTPSConnection(host='api.github.com', timeout=10)
            conn.request(method='GET', url=url, headers=headers)

        except socket.gaierror:
            logging.critical("socket.gaierror while connecting to https://{}".format(github_http_host))

        except:
            pass

        # rr is a list of dicts...
        rr = json.loads(conn.getresponse().read().decode('UTF-8'))

        if isinstance(rr, dict):
            error = rr.get('message', None)
            if 'Server Error' in error:
                raise ValueError("Github responded: '{}'".format(rr['message']))

            elif error is not None:
                raise ValueError("Hit Github REST rate-limit: '{}'".format(rr['message']))

        assert isinstance(rr, (list, tuple))
        table = TTable(rr, ['full_name', 'stargazers_count'], per_page=15)
        table.render()

        print(json_page)
        json_page += 1

        all_stars.extend(rr)
        time.sleep(10)

