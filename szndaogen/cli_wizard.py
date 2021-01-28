import os
import stat
import sys

DEFAULT_MYSQL_PORT = 3306


def _exit(msg):
    print(msg)
    sys.exit(1)


def _save_configuration(_options, _output_path: str):
    file_content = f"#!/usr/bin/env bash\nszndaogen -a {_options.db_host} -r {_options.db_port} -d {_options.db_name} -u {_options.db_user} -p {_options.db_pass} {_output_path}\n"  # noqa
    file_name = f"szndaogen-{_options.db_host}-{_options.db_name}.sh"
    with open(file_name, "w+") as file:
        file.write(f"{file_content}\n")

        st = os.stat(file_name)
        os.chmod(file_name, st.st_mode | stat.S_IEXEC)

        print(f"\nShortcut script '{file_name}' created in current working directory.")
        print(f"File contents: {file_content}")


def wizard(options) -> tuple:
    continue_ = input("\nRequired parameters are not satisfied. Would you like to run setup wizard? [Y/n] ")
    if not(continue_ == "" or continue_.lower() == "y"):
        sys.exit(0)

    host = input("MySQL host address: ")
    if not host:
        _exit("No MySQL host provided. Exiting.")

    port = input("MySQL port (default 3306): ")
    if not port:
        port = DEFAULT_MYSQL_PORT

    db = input("MySQL database name: ")
    if not db:
        _exit("No MySQL DB name provided. Exiting.")

    user = input("MySQL username: ")
    if not user:
        _exit("No MySQL username provided. Exiting.")

    pw = input("MySQL password: ")

    output_path = input("Output path where all models and managers will be generated (default \"./data_access\"): ")
    if not output_path:
        output_path = "./data_access"

    options.db_host = host
    options.db_port = int(port)
    options.db_name = db
    options.db_user = user
    options.db_pass = pw

    arguments = [output_path]

    save_to_file = input("Before you proceed, would you like to save this configuration as a bash script in CWD for future use? [Y/n]")  # noqa
    if save_to_file == "" or save_to_file.lower() == "y":
        _save_configuration(options, output_path)

    return options, arguments
