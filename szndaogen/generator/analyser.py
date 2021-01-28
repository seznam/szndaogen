import os
import re
import sys

import sqlparse
from jinja2 import Template

from .datatypes import DATATYPES
from ..data_access.db import DBI
from ..tools.cli_colors import CMD, FG

class Analyser:
    def __init__(self, output_path: str, custom_templates_path: str = None):
        self.db = DBI()
        self.base_output_path = output_path
        self.models_output_path = os.path.join(self.base_output_path, "models")
        self.managers_output_path = os.path.join(self.base_output_path, "managers")

        self.template_path = custom_templates_path or os.path.join(os.path.dirname(__file__), os.path.dirname(__file__), "../templates/")
        self.model_template_path = os.path.join(self.template_path, "../templates/model.jinja")
        self.manager_template_path = os.path.join(self.template_path, "../templates/manager.jinja")
        self.manager_base_template_path = os.path.join(self.template_path, "../templates/manager_base.jinja")

        self.table_name: str = None
        self.table_type: str = None
        self.table_description: list = None
        self.attr_datatypes = None
        self.primary_keys: list = None
        self.model_imports: list = None
        self.model_convertors: dict = None
        self.enum_types: list = []
        self.view_statement: str = None
        self.view_statement_create: str = None
        self.where_base: str = None
        self.order_by_default: str = None

        self.model_j_template: Template = self._get_j_template_instance(self.model_template_path)
        self.manager_j_template: Template = self._get_j_template_instance(self.manager_template_path)
        self.manager_base_j_template: Template = self._get_j_template_instance(self.manager_base_template_path)

    def run(self):
        print(f"{FG.green}Starting Database Access Object Generator{CMD.reset}")
        table_list = self._list_tables()
        for table in table_list:
            try:
                self.table_name = table[0]
                self.table_type = table[1]
                self._describe_table()
                self._analyze_datatypes()
                if self.table_type == "VIEW":
                    self._parse_view_sql_statement()
                else:
                    self.view_statement = None
                    self.view_statement_create = None
                self._process_model_template()
                self._process_manager_template()
                self._process_manager_base_template()
            except Exception as ex:
                print(f"{FG.red}Error while processing table '{table}'{CMD.reset}: {ex.__str__()}", file=sys.stderr)
        print(f"{FG.green}DONE{CMD.reset}")

    def _list_tables(self):
        return self.db.fetch_all("SHOW FULL tables", dictionary_output=False)

    def _describe_table(self):
        self.table_description = self.db.fetch_all("SHOW FULL COLUMNS FROM `{}`".format(self.table_name))
        self.primary_keys = [item["Field"] for item in self.table_description if item["Key"] == "PRI"]

    def _parse_view_sql_statement(self):
        self.view_statement = None
        self.view_statement_create = None
        view_statement_info = self.db.fetch_one("SHOW CREATE TABLE `{}`".format(self.table_name))
        view_statement_create = view_statement_info["Create View"]
        found = re.findall(r"SECURITY DEFINER VIEW (`[^`]+`) AS (\(?.*\)?$)", view_statement_create)
        self.view_statement_create = sqlparse.format(
            view_statement_create, keyword_case="upper", indent_columns=True, wrap_after=2048
        )
        if found:
            _, view_statement = found[0]
            view_statement = view_statement[1:-1] if view_statement.startswith("(") else view_statement

            view_statement = sqlparse.format(
                view_statement, keyword_case="upper", indent_columns=True, wrap_after=32768
            )

            where_base = "1"
            where_regex = r"\nWHERE ([^\n]*)(\n|$)?"
            search_where = re.search(where_regex, view_statement)
            if search_where:
                where_base = search_where.groups()[0]
                view_statement = re.sub(where_regex, "\n", view_statement)

            order_by_default = ""
            order_by_regex = r"\nORDER BY ([^\n]*)(\n|$)?"
            search_order_by = re.search(order_by_regex, view_statement)
            if search_order_by:
                order_by_default = search_order_by.groups()[0]
                view_statement = re.sub(order_by_regex, "\n", view_statement)

            self.where_base = where_base
            self.order_by_default = order_by_default

            view_statement = sqlparse.format(view_statement, keyword_case="upper", indent_columns=True)

            search_group_by = re.search(r"\nGROUP BY", view_statement)
            if search_group_by:
                found_on_index = search_group_by.start()
                view_statement_parts = (view_statement[:found_on_index], view_statement[found_on_index:])
                view_statement_template = f"{view_statement_parts[0]} \n{{WHERE}} {view_statement_parts[1]} \n{{ORDER_BY}} \n{{LIMIT}} \n{{OFFSET}}"  # noqa
            else:
                view_statement_template = f"{view_statement}\n{{WHERE}} \n{{ORDER_BY}} \n{{LIMIT}} \n{{OFFSET}}"

            self.view_statement = view_statement_template

    def _process_model_template(self):
        model_name = self._get_model_name(self.table_name)
        model_filename = "{}_model.py".format(self.table_name.lower())

        output = self.model_j_template.render(
            modelName=model_name,
            tableName=self.table_name,
            tableType=self.table_type,
            tableDescription=self.table_description,
            modelImports=self.model_imports,
            modelConvertors=self.model_convertors,
            primaryKeys=self.primary_keys,
            enumTypes=self.enum_types,
            dataTypes=self.attr_datatypes,
            viewStatement=self.view_statement,
            viewStatementCreate=self.view_statement_create,
            whereBase=self.where_base,
            orderByDefault=self.order_by_default,
        )

        if self.base_output_path:
            self._create_module(self.base_output_path)
            self._create_module(self.models_output_path)
            file_path = os.path.join(self.models_output_path, model_filename)
            print(f"{CMD.bold}Writing model{CMD.reset} `{model_name}` into `{file_path}`")
            with open(file_path, "w") as f:
                f.write(output)
        else:
            print(f"**** MODEL: {model_name} --> {model_filename} ****\n{output}")

    def _process_manager_base_template(self):
        manager_name = self._get_model_name(self.table_name)
        manager_filename = "{}_manager_base.py".format(self.table_name.lower())

        output = self.manager_base_j_template.render(
            modelName=manager_name,
            tableName=self.table_name,
            tableType=self.table_type,
            primaryKeys=self.primary_keys,
            dataTypes=self.attr_datatypes,
        )

        if self.managers_output_path:
            self._create_module(os.path.join(self.managers_output_path, "base"))
            file_path = os.path.join(self.managers_output_path, "base", manager_filename)
            print(f"{CMD.bold}Writing base manager{CMD.reset} `{manager_name}` into `{file_path}`")
            with open(file_path, "w") as f:
                f.write(output)
        else:
            print(f"**** BASE MANAGER: {manager_name} --> {manager_filename} ****\n{output}")

    def _process_manager_template(self):
        manager_name = self._get_model_name(self.table_name)
        manager_filename = "{}_manager.py".format(self.table_name.lower())

        output = self.manager_j_template.render(modelName=manager_name, tableName=self.table_name)
        if self.base_output_path:
            self._create_module(self.base_output_path)
            self._create_module(self.managers_output_path)
            file_path = os.path.join(self.managers_output_path, manager_filename)
            if os.path.exists(file_path):
                print(f"Skipping manager `{manager_name}` exists `{file_path}`")
            else:
                print(f"{CMD.bold}Writing manager{CMD.reset} `{manager_name}` into `{file_path}`")
                with open(file_path, "w") as f:
                    f.write(output)
        else:
            print(f"**** MANAGER: {manager_name} --> {manager_filename} ****\n{output}")

    def _analyze_datatypes(self):
        self.model_imports = []
        self.model_convertors = {}
        self.enum_types = []
        self.attr_datatypes = {}
        for item in self.table_description:
            attr_name = item["Field"]
            model_datatype = None
            db_datatype, db_datatype_size = self._get_db_datatype(item["Type"])
            model_datatype_info = DATATYPES.get(
                db_datatype, DATATYPES["__default__"]
            )
            if db_datatype not in DATATYPES:
                print(f"{FG.orange}WARNING:{CMD.reset} Unknown datatype '{item['Type']}' found in table '{self.table_name}' attribute '{item['Field']}'. "
                      f"It will converted into string by default. Best way is to add it into DATATYPES dict.")
            if model_datatype_info:
                model_datatype = model_datatype_info[0]
                if model_datatype_info[1]:
                    self.model_imports.append(model_datatype_info[1])
                if model_datatype_info[2]:
                    self.model_convertors[attr_name] = model_datatype_info[2]
                # process ENUMs
                if db_datatype == "enum":
                    enums_str = db_datatype_size.replace("'", '"').replace(',"', ', "')
                    self.enum_types.append({"Field": attr_name, "Options": enums_str})
            item["ModelType"] = model_datatype
            item["ModelDefaultValue"] = self._wrap_word(item["Default"], model_datatype_info[3], model_datatype_info[4])
            self.attr_datatypes[attr_name] = model_datatype
        self.model_imports = list(set(self.model_imports))
        self.model_imports.sort()

    @staticmethod
    def _get_j_template_instance(template_path: str) -> Template:
        with open(template_path, "r") as f:
            template = f.read()
        j_template = Template(template)
        return j_template

    @staticmethod
    def _get_model_name(table_name: str) -> str:
        spl = table_name.lower().split("_")
        spl = map(str.capitalize, spl)
        return "".join(spl)

    @staticmethod
    def _get_db_datatype(db_datatype) -> (str, str):
        found = re.findall(r"(^[a-zA-Z0-9_]+)(\([^)]*\))?", db_datatype)
        _db_datatype = found[0][0] if found else None
        _db_datatype_size = found[0][1][1:-1] if found and len(found[0][1]) > 2 else None
        return _db_datatype, _db_datatype_size

    @staticmethod
    def _wrap_word(word: str, left_wrapper: str, right_wrapper: str) -> str:
        return "{}{}{}".format(left_wrapper or "", word, right_wrapper or "") if word else None

    @staticmethod
    def _create_module(module_path: str):
        try:
            os.makedirs(module_path)
            init_file = os.path.join(module_path, "__init__.py")
            open(init_file, "a").close()
        except Exception as ex:
            #print(f"_create_module exception: {ex}")
            pass
