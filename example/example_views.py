from example_dao.managers.view_ordes_to_be_processed_manager import ViewOrdesToBeProcessedManager
from szndaogen.config import Config
from szndaogen.tools.log import Logger, StdOutLogger


if __name__ == '__main__':
    Config.MANAGER_AUTO_MAP_MODEL_ATTRIBUTES = True
    Config.MYSQL_HOST = "localhost"
    Config.MYSQL_DATABASE = "classicmodels"
    Config.MYSQL_USER = "root"
    Config.MYSQL_PASSWORD = ""

    Logger.set_external_logger(logger_instance=StdOutLogger())

    manager = ViewOrdesToBeProcessedManager()
    results = manager.select_all(order_by=("`od`.`quantityOrdered` DESC",), limit=10)

    print("Top 10 ordered quauntities waiting for processing")
    for item in results:
        print(f"{item.orderNumber} - {item.productCode}: {item.productName}, {item.quantityOrdered}/{item.quantityInStock}")
