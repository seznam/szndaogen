import pprint
from example_dao.managers.view_example_auto_group_list_manager import ViewExampleAutoGroupListManager
from szndaogen.config import Config
from szndaogen.tools.log import Logger, StdOutLogger
from szndaogen.tools.auto_group import auto_group_list

if __name__ == '__main__':
    Config.MANAGER_AUTO_MAP_MODEL_ATTRIBUTES = True
    Config.MYSQL_HOST = "localhost"
    Config.MYSQL_DATABASE = "classicmodels"
    Config.MYSQL_USER = "root"
    Config.MYSQL_PASSWORD = ""

    Logger.set_external_logger(logger_instance=StdOutLogger())

    manager = ViewExampleAutoGroupListManager()
    result = manager.select_all(condition="o.`officeCode` = 1")
    list_of_dicts_results = manager.models_into_dicts(result)
    print(list_of_dicts_results)
    pprint.pprint(
        auto_group_list(list_of_dicts_results)
    )
