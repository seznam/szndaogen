import os

from optparse import OptionParser

from szndaogen.cli_wizard import wizard
from szndaogen.config import Config
from szndaogen.generator.analyser import Analyser
from szndaogen.tools.log import Logger, BaseLogger
from szndaogen.tools.setuptools import get_file_content


def get_cmd_options() -> tuple:
    version = get_file_content(os.path.join(os.path.dirname(__file__), "VERSION"))
    parser = OptionParser()
    parser.usage = (
        f"SZN DAOGen v{version} - Database Access Object Generator by Seznam.cz\n"
        "%prog [options] output_path\n"
        "    example: %prog -a localhost -d my_database -u root -p pass /path/to/data_access\n"
        "    example: %prog -a localhost -d my_database -u root -p pass ./data_access\n"
    )

    parser.add_option("-a", "--host-address", dest="db_host", type="string", help="MySQL database host. (required)")
    parser.add_option("-r", "--port", dest="db_port", type="int", help="MySQL database port.", default=3306)
    parser.add_option("-d", "--database", dest="db_name", type="string", help="MySQL database name. (required)")
    parser.add_option(
        "-u", "--user", dest="db_user", type="string", help="User name for MySQL DB authentication. (required)"
    )
    parser.add_option("-p", "--password", dest="db_pass", type="string", help="Password for MySQL DB authentication.")
    parser.add_option("-t", "--templates-path", dest="templates_path", type="string", help="Path to custom templates of Models (model.jinja), "
                                                                                           "DataManagers (manager.jinja) and DataManagerBases (manager_base.jinja).")

    options, arguments = parser.parse_args()

    if not options.db_host or not options.db_name or not options.db_user:
        parser.print_help()
        options, arguments = wizard(options)

    if len(arguments) < 1:
        print("Warning: Missing output path parameters. Models and Managers will be generated into std-out.")

    return options, arguments


def main():
    _options, _arguments = get_cmd_options()
    output_path = None if len(_arguments) < 1 else _arguments[0]

    Config.MYSQL_HOST = _options.db_host
    Config.MYSQL_PORT = _options.db_port
    Config.MYSQL_DATABASE = _options.db_name
    Config.MYSQL_USER = _options.db_user
    Config.MYSQL_PASSWORD = _options.db_pass
    Logger.set_external_logger(logger_instance=BaseLogger())

    app = Analyser(output_path, custom_templates_path=_options.templates_path)
    app.run()


if __name__ == "__main__":
    main()
