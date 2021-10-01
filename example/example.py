from example_dao.managers.employees_manager import EmployeesManager
from szndaogen.config import Config
from szndaogen.data_access.db import DBI
from szndaogen.tools.log import Logger, StdOutLogger


@DBI.transaction("dbi")
def update_employee_first_name(employee_id: int, new_first_name: str, dbi: DBI = None) -> int:
    manager = EmployeesManager(dbi=dbi)  # tell manager to work with passed DBI instance to keep transaction connection
    model_instance = manager.select_one(employee_id)
    model_instance.firstName = new_first_name
    return manager.update_one(model_instance, exclude_columns=["lastName"])


if __name__ == '__main__':
    Config.MANAGER_AUTO_MAP_MODEL_ATTRIBUTES = True  # if disabled, you can control attributes mapping by `map_model_attributes()` method on model instance if needed to better performance
    Config.MYSQL_HOST = "localhost"
    Config.MYSQL_DATABASE = "classicmodels"
    Config.MYSQL_USER = "root"
    Config.MYSQL_PASSWORD = ""

    Logger.set_external_logger(logger_instance=StdOutLogger())

    employee_manager = EmployeesManager()
    employee_result = employee_manager.select_all(order_by=(f"{EmployeesManager.MODEL_CLASS.Meta.employeeNumber} ASC",))

    for employee_model_instance in employee_result:
        print(f"{employee_model_instance.firstName} {employee_model_instance.lastName} - {employee_model_instance.employeeNumber}")

    # autocommit update
    employee_result = employee_manager.select_all("lastName=%s", ("Thompson",))
    if len(employee_result) == 1:
        employee_model_instance = employee_result[0]
        print(f"Trying to update record id: {employee_model_instance.employeeNumber} - {employee_model_instance.firstName} {employee_model_instance.lastName}")
        employee_model_instance.firstName = "New Leslie"
        employee_manager.update_one(employee_model_instance)

    employee_result = employee_manager.select_all("lastName=%s", ("Thompson",))
    employee_model_instance = employee_result[0]
    print(f"Updated record id: {employee_model_instance.employeeNumber} - {employee_model_instance.firstName} {employee_model_instance.lastName}")

    # transaction update
    update_employee_first_name(1166, "Leslie forever")

    # new item
    new_employee = employee_manager.create_model_instance()
    new_employee.employeeNumber = 9999
    new_employee.firstName = "John"
    new_employee.lastName = "Doe"
    new_employee.extension = "xxx"
    new_employee.email = "a@b.c"
    new_employee.officeCode = 4
    new_employee.jobTitle = "Incognito"
    new_employee.reportsTo = None
    employee_manager.insert_one(new_employee, exclude_none_values=True)

    # delete item
    employee_manager.delete_one(new_employee)
    # OR
    employee_manager.delete_all(f"{EmployeesManager.MODEL_CLASS.Meta.employeeNumber}=%s", (9999,))
    # OR simply
    employee_manager.delete_all("employeeNumber=%s", (9999,))
