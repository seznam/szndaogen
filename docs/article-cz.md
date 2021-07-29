# Generátor DAO vrstvy pro Python

Jednoduchý objektový přístup do databáze při vytváření backendových či jiných komponent potřeboval už snad každý z nás. Určitě jste se
setkali s nejruznějšími možnými přístupy jak získat data z SQL databáze a to od přímého přístupu do databáze přes SQL příkazy
až po zabalení jednotlivých tabulek do objektů nejrůznějšího typu. Ať už jste si oblíbili přítup jakýkoliv existuje zde ještě možnost, se kterou
jste se možná ještě nesetkali a pokud ano, není moc obvyklá v Pythonových frameworcích. Jde o automatické generování datové
přístupové vrstvy k tabulkálkám definovaným na SQL databázi. V tomto případě MySQL databázi.

Před nedávnem jsme potřebovali napsat restové API pro přístup k datům uloženým v relační databázi. Kostru projektu pro výdejové rest API jsme měli
hotovou, ale byla napsána pro práci s dokumentovou databází. Mohli jsme se určitě rozhodnout pro, mnoha týmy ze začátku oblíbenou
a po delší době práce nenáviděnou, knihovnu `SQLAlchemy`. `SQLAlchemy` je totiž skvělá varianta pro případy, kdy k datům z tabulek přistupujete
standartním způsobem, problémy začínají, když potřebujete dělat složitější agregační funkce případně sofistikovaněji pracovat s projekcí
jednotlivých sloupců. Tomu všemu jsme se chtěli vyhnout. Navíc pro práci s datovou vrstvou pomocí SQL Alchemy je potřeba definovat modely
pro jednotlivé tabulky a její atributy (sloupečky), každou změnu, kterou uděláte na DB musíte hned promítnout i do definice modelu. Ale tohle všechno určite
znáte a není potřeba se o tom dalekosáhle rozepisovat. Popíšu, co napadlo nás a jakým směrem jsme se vydali.

Napsali jsme si jednoduchý analyzátor existujících definic tabulek a views na MySQL databázi. Po analýze databázové struktury se vygenerují
`Modely` obsahující definici jednotlivých atributů tabulek a views. Ke každému modelu se zároveň vygeneruje příslušný `DataManager` sloužící pro
přístup k datům pomocí několika předdefinovaných metod. Pro generování `Model`ů a `DataManager`ů používáme Jinja2 šablonovací systém. Formát `Model`ů
a `DataManager`ů je psán s ohledem na možnost automatického generování `TypeHint`ů a komentářů k jednotlivým atributům tabulek a views. `Modely` obsahují
pouze definice struktury tabulky a několik základních metod jakou jsou:
- `map_model_attributes` - nastaví atributy třídy na základě hodnot získaných z databáze do té doby uložených pouze ve slovníku `model_data`. K automatickému provolání této metody při
získání dat z DB může zajistit nastavení `Config.MANAGER_AUTO_MAP_MODEL_ATTRIBUTES`, pak `DataManager` vždy po načtení dat tuto medotu provolá. Jinak by byly atributy třídy stále
nastaveny na `default`hodnotu. Toto chování je záměrné kvůli lepšímu výkonu. Ne vždy totiž potřebujeme mít atributy třídy namapované hodnotami z DB.
- `clone` - vytvoří kopii modelu.
- `Meta` - není funkce, ale subclass, která obsahuje statické meta informace o tabulce pro kterou je model vytvořen.

Pro vyvolání přístupo do databáze jak již bylo výše zmíněno slouží tzv. `DataManager`y, ke každému modelu je vytvořen jeden `DataManagerBase` a `DataManager`.
`DataManagerBase` podobně jako `Model` jsou kdykoliv je potřeba přegenerovány (přepsány) novou datovou strukturou, pokud spustíte znovu analyzátor s generátorem. `DataManager`
je vytvořen jenom v případě, že před tím neexistoval a slouží primárně k tomu, abyste si do nej mohli dopisovat vlastní nástavby funkcionality nebo přetěžovali existující funkce.
`DataManager`y pro views obsahují tyto základní metody:
- `select_one` - vybere jeden záznam z tabulky nebo view na základě jednoznačného klíče (i složeného) identifikátoru nebo na základě definované podmínky.
- `select_all` - vybere všechny záznamy z tabulky nebo view vyhovojící definované podmínce.
- `create_model_instance` - pro vytvoření nové prázdné instance `Modelu` náležící k příslušnému `DataManageru`.
Jedná se pouze o pomocnou metodu. Model lze vytvořit samozřejmě i ručně z definice příslušné třídy `Model`u.
- `models_into_dicts` - statická metoda, které umožní jednoduchý převod pole modelů na pole slovníků.

`DataManager`y pro tabulky navíc obsahují metody pro vytváření, úpravy či mazání záznamů v tabulce:
- `update_one` - Upraví jeden záznam na základě jedinečného klíče (i složeného).
- `insert_one` - Vloží jeden nový záznam s daty definovanými v `Model`u.
- `insert_one_bulk` - Vloží jeden nový záznam definovaný v `Model`u z obsáhlejší dávky. Velikost dávky je defaultně `bulk_insert_buffer_size = 50`.
- `insert_bulk_flush` - Jelikož je málo pravděpodobné, že dávka pro `bulk_insert` bude přesně o velikosti 50, je potřeba na konci plnícho cyklu vyprázdnit zásobník se zvývajícímí připravenými inserty.
- `delete_one` - Smaže jeden záznam na základě jedinečného klíče (i složeného).
- `delete_all` - Smaže všechny záznamy z tabulky vyhovojící definované podmínce.

Možná se pozastavujete nad tím, že tady tak často zminujeme práci s `view`. Vždyť je přeci známo, že views mají výkonové problémy, chovají se jako `temporary tables` a 
neaplikují se na performance vylepšení definována na tabulkách ve formě indexů. Za chvíli si ukážeme jak analyzátor definuje třídu `Model`u. Modely totiž obsahuji `SQL_STATEMENT`
jak pro tabulky, tak pro views. Tímto "kouzlem" obcházíme výkonové nedostatky databázovývh views. Definovaná Views se totiž ve skutečnosti nespouštějí na straně databáze. Jejich
předpis se pouze využije k definování modelu a uložené SQL se pak na straně Python MySQL klienta pošle databázovému serveru. Tím pádem se na něj aplikují všechny definované výkonostní
optimalizace.

Zde je ukázka jednoho vygenerovaného view:
```python
import typing
from szndaogen.data_access.model_base import ModelBase


class ViewOrdersToBeProcessedModel(ModelBase):
    class Meta:
        TABLE_NAME: str = "view_orders_to_be_processed"
        TABLE_TYPE: str = "VIEW"
        # fmt: off
        SQL_STATEMENT: str = """SELECT """ \
                             """  `o`.`orderNumber` AS `orderNumber`, """ \
                             """  `od`.`productCode` AS `productCode`, """ \
                             """  `od`.`quantityOrdered` AS `quantityOrdered`, """ \
                             """  `p`.`productName` AS `productName`, """ \
                             """  `p`.`quantityInStock` AS `quantityInStock`, """ \
                             """  if((`p`.`quantityInStock` > `od`.`quantityOrdered`),'enough', 'to_stock_needed') AS `productInStockStatus` """ \
                             """FROM ((`orders` `o` """ \
                             """       LEFT JOIN `orderdetails` `od` on((`od`.`orderNumber` = `o`.`orderNumber`))) """ \
                             """      LEFT JOIN `products` `p` on(`p`.`productName`)) """ \
                             """{WHERE}  """ \
                             """{ORDER_BY}  """ \
                             """{LIMIT}  """ \
                             """{OFFSET} """
        # fmt: on

        SQL_STATEMENT_WHERE_BASE: str = "(`o`.`status` = 'In Process')"
        SQL_STATEMENT_ORDER_BY_DEFAULT: str = ""

        PRIMARY_KEYS: typing.List = []
        ATTRIBUTE_LIST: typing.List = ["orderNumber", "productCode", "quantityOrdered", "productName", "quantityInStock", "productInStockStatus", ]
        ATTRIBUTE_TYPES: typing.Dict = {
            "orderNumber": int,
            "productCode": str,
            "quantityOrdered": int,
            "productName": str,
            "quantityInStock": int,
            "productInStockStatus": str,
        }
        MODEL_DATA_CONVERTOR: typing.Dict = {
        }

    def __init__(self, init_data: typing.Dict = {}):
        self.orderNumber: int = None
        """Type: int(11), Can be NULL: NO"""
        self.productCode: str = None
        """Type: varchar(15), Can be NULL: YES"""
        self.quantityOrdered: int = None
        """Type: int(11), Can be NULL: YES"""
        self.productName: str = None
        """Type: varchar(70), Can be NULL: YES"""
        self.quantityInStock: int = None
        """Type: smallint(6), Can be NULL: YES"""
        self.productInStockStatus: str = None
        """Type: varchar(15), Can be NULL: NO"""
        super().__init__(init_data)

```

To by možná na úvod už stačilo. Nyní múžeme přejít k praktickým ukázkám využití knihovny `SZN DAOGen`

# Použití v praxi

Instalace knihovny je velmi jednoduchá, je instalovatelná ze standartního PYPI repozitáře:
```bash
pip3 install szndaogen
```

Pokud chcete pracovat ve virtualenv prostředí založte si jej např. takto:
```bash
virtualenv -p /usr/bin/python3.8 ~/.virtualenvs/szndaogen
source ~/.virtualenvs/szndaogen/bin/activate
```

Použití samotného příkazu pro generování nám napoví vypsaný help.
```
szndaogen --help

Usage of SZN DAOGen v2.3.0 - Database Access Object Generator by Seznam.cz
szndaogen [options] output_path
    example: szndaogen -a localhost -d my_database -u root -p pass /path/to/data_access
    example: szndaogen -a localhost -d my_database -u root -p pass ./data_access


Options:
  -h, --help            show this help message and exit
  -a DB_HOST, --host-address=DB_HOST
                        MySQL database host. (required)
  -r DB_PORT, --port=DB_PORT
                        MySQL database port.
  -d DB_NAME, --database=DB_NAME
                        MySQL database name. (required)
  -u DB_USER, --user=DB_USER
                        User name for MySQL DB authentication. (required)
  -p DB_PASS, --password=DB_PASS
                        Password for MySQL DB authentication.
  -t TEMPLATES_PATH, --templates-path=TEMPLATES_PATH
                        Path to custom templates of Models (model.jinja),
                        DataManagers (manager.jinja) and DataManagerBases
                        (manager_base.jinja).
```

Pro praktickou ukázku jak SZN DAOGen funguje si stáhneme cvičnou databázi z webu [MySQLTutorial.org](https://www.mysqltutorial.org/mysql-sample-database.aspx/).
Zazipovaná databáze je k dispozici [zde](https://sp.mysqltutorial.org/wp-content/uploads/2018/03/mysqlsampledatabase.zip).

Po rozzipování souboru provedeme import databáze
```bash
mysql < mysqlsampledatabase.sql
```

Vytvořte si adresář `example` nebo využijte stejně pojmenovaný adresář v rámci vyklonovaného repozitáře se `szndaogen`em na [GitHubu](https://github.com/seznam/szndaogen)

Nyní už nic nebrání tomu, abychom si vygenerovali `Modely` a `DataManagery` na základě naší existující databáze. Stačí pouze napsat příkaz:
```bash
szndaogen
```
Tím se spustí jednoduchý průvodce, která se Vás zeptá na několik základních informaci o konfiguraci připojení k DB atp. (pokud průvodce využít nechcete, můžete vše nastavit sami pomocí přepínačů)
```
Required parameters are not satisfied. Would you like to run setup wizard? [Y/n] y
MySQL host address: localhost
MySQL port (default 3306): 3306
MySQL database name: classicmodels
MySQL username: mysql-user
MySQL password: mysql-user-password
Output path where all models and managers will be generated (default "./data_access"): ./example_dao
Before you proceed, would you like to save this configuration as a bash script in CWD for future use? [Y/n] y

Shortcut script 'szndaogen-localhost-classicmodels.sh' created in current working directory.
Writing model `Customers` into `example_dao/models/customers_model.py`
Writing manager `Customers` into `example_dao/managers/customers_manager.py`
Writing manager `Customers` into `example_dao/managers/base/customers_manager_base.py`
Writing model `Employees` into `example_dao/models/employees_model.py`
Writing manager `Employees` into `example_dao/managers/employees_manager.py`
Writing manager `Employees` into `example_dao/managers/base/employees_manager_base.py`
Writing model `Offices` into `example_dao/models/offices_model.py`
Writing manager `Offices` into `example_dao/managers/offices_manager.py`
Writing manager `Offices` into `example_dao/managers/base/offices_manager_base.py`
Writing model `Orderdetails` into `example_dao/models/orderdetails_model.py`
Writing manager `Orderdetails` into `example_dao/managers/orderdetails_manager.py`
Writing manager `Orderdetails` into `example_dao/managers/base/orderdetails_manager_base.py`
Writing model `Orders` into `example_dao/models/orders_model.py`
Writing manager `Orders` into `example_dao/managers/orders_manager.py`
Writing manager `Orders` into `example_dao/managers/base/orders_manager_base.py`
Writing model `Payments` into `example_dao/models/payments_model.py`
Writing manager `Payments` into `example_dao/managers/payments_manager.py`
Writing manager `Payments` into `example_dao/managers/base/payments_manager_base.py`
Writing model `Productlines` into `example_dao/models/productlines_model.py`
Writing manager `Productlines` into `example_dao/managers/productlines_manager.py`
Writing manager `Productlines` into `example_dao/managers/base/productlines_manager_base.py`
Writing model `Products` into `example_dao/models/products_model.py`
Writing manager `Products` into `example_dao/managers/products_manager.py`
Writing manager `Products` into `example_dao/managers/base/products_manager_base.py`
```

Nyní by měl Váš adresář vypadat nějak takto:
```
tree .

├── szndaogen-localhost-classicmodels.sh
├── example_dao
│   ├── __init__.py
│   ├── managers
│   │   ├── base
│   │   │   ├── __init__.py
│   │   │   ├── customers_manager_base.py
│   │   │   ├── employees_manager_base.py
│   │   │   ├── offices_manager_base.py
│   │   │   ├── orderdetails_manager_base.py
│   │   │   ├── orders_manager_base.py
│   │   │   ├── payments_manager_base.py
│   │   │   ├── productlines_manager_base.py
│   │   │   └── products_manager_base.py
│   │   ├── __init__.py
│   │   ├── customers_manager.py
│   │   ├── employees_manager.py
│   │   ├── offices_manager.py
│   │   ├── orderdetails_manager.py
│   │   ├── orders_manager.py
│   │   ├── payments_manager.py
│   │   ├── productlines_manager.py
│   │   └── products_manager.py
│   └── models
│       ├── __init__.py
│       ├── customers_model.py
│       ├── employees_model.py
│       ├── offices_model.py
│       ├── orderdetails_model.py
│       ├── orders_model.py
│       ├── payments_model.py
│       ├── productlines_model.py
│       └── products_model.py
└── requirements.txt
```

Ukázka vygenerované třídy `Model`u SZN DAOGenem, která vypadá podobně jako výše zmíněné `view`.
```python
# !!! DO NOT MODIFY !!!
# Automatically generated Model class
# Generated by "szndaogen" tool


import typing
from szndaogen.data_access.model_base import ModelBase


class EmployeesModel(ModelBase):
    class Meta:
        TABLE_NAME: str = "employees"
        TABLE_TYPE: str = "BASE TABLE"
        # fmt: off
        SQL_STATEMENT: str = "SELECT {PROJECTION} FROM `employees` {WHERE} {ORDER_BY} {LIMIT} {OFFSET}"
        # fmt: on

        SQL_STATEMENT_WHERE_BASE: str = "1"
        SQL_STATEMENT_ORDER_BY_DEFAULT: str = ""

        PRIMARY_KEYS: typing.List = ["employeeNumber", ]
        ATTRIBUTE_LIST: typing.List = ["employeeNumber", "lastName", "firstName", "extension", "email", "officeCode", "reportsTo", "jobTitle", ]
        ATTRIBUTE_TYPES: typing.Dict = {
            "employeeNumber": int,
            "lastName": str,
            "firstName": str,
            "extension": str,
            "email": str,
            "officeCode": str,
            "reportsTo": int,
            "jobTitle": str,
        }
        MODEL_DATA_CONVERTOR: typing.Dict = {
        }

    def __init__(self, init_data: typing.Dict = {}):
        self.employeeNumber: int = None
        """Type: int(11), Can be NULL: NO, Key: PRI"""
        self.lastName: str = None
        """Type: varchar(50), Can be NULL: NO"""
        self.firstName: str = None
        """Type: varchar(50), Can be NULL: NO"""
        self.extension: str = None
        """Type: varchar(10), Can be NULL: NO"""
        self.email: str = None
        """Type: varchar(100), Can be NULL: NO"""
        self.officeCode: str = None
        """Type: varchar(10), Can be NULL: NO, Key: MUL"""
        self.reportsTo: int = None
        """Type: int(11), Can be NULL: YES, Key: MUL"""
        self.jobTitle: str = None
        """Type: varchar(50), Can be NULL: NO"""
        super().__init__(init_data)

```

Ukázka vygenerované třídy bázového `DataManager`u:
```python
# !!! DO NOT MODIFY !!!
# Automatically generated Base Manager class
# Generated by "szndaogen" tool

import typing
from szndaogen.data_access.manager_base import TableManagerBase
from ...models.employees_model import EmployeesModel


class EmployeesManagerBase(TableManagerBase):
    MODEL_CLASS = EmployeesModel

    @classmethod
    def create_model_instance(cls, init_data: typing.Dict = None) -> EmployeesModel:
        if init_data is None:
            init_data = {}

        return super().create_model_instance(init_data)

    def select_one(self, employeeNumber: int, condition: str = "1", condition_params: typing.Tuple = (), projection: typing.Tuple = (), order_by: typing.Tuple = ()) -> EmployeesModel:
        return super().select_one(employeeNumber, condition=condition, condition_params=condition_params, projection=projection, order_by=order_by)

    def select_all(self, condition: str = "1", condition_params: typing.Tuple = (), projection: typing.Tuple = (), order_by: typing.Tuple = (), limit: int = 0, offset: int = 0) -> typing.List[EmployeesModel]:
        return super().select_all(condition=condition, condition_params=condition_params, projection=projection, order_by=order_by, limit=limit, offset=offset)

```
A jako poslední ukázka vygenerované třídy `DataManager`u, které už může být rozšiřována o Vaši funkcionalitu a příštím spuštěním SZN DAOGenu nebude přepsána:
```python
# This file can be modified. If file exists it wont be replaced by "szndaogen" any more.
# Automatically generated Manager class
# Generated by "szndaogen" tool

from .base.employees_manager_base import EmployeesManagerBase


class EmployeesManager(EmployeesManagerBase):
    pass

```

Nyní si můžeme vytvořit ukázkovou aplikaci demonstrující základní principy práce s knihovnou. Tento příklad je obsažen v repozitáři na [GitHubu](https://github.com/seznam/szndaogen/tree/master/example).

```python
from example_dao.managers.employees_manager import EmployeesManager
from szndaogen.config import Config
from szndaogen.data_access.db import DBI
from szndaogen.tools.log import Logger, StdOutLogger


@DBI.transaction("dbi")
def update_employee_first_name(employee_id: int, new_first_name: str, dbi: DBI = None) -> int:
    manager = EmployeesManager(dbi=dbi)  # tell manager to work with passed DBI instance to keep transaction connection
    model_instance = manager.select_one(employee_id)
    model_instance.firstName = new_first_name
    return manager.update_one(model_instance)


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
    employee_manager.insert_one(new_employee)

    # delete item
    employee_manager.delete_one(new_employee)
    # OR
    employee_manager.delete_all(f"{EmployeesManager.MODEL_CLASS.Meta.employeeNumber}=%s", (9999,))
    # OR simply
    employee_manager.delete_all("employeeNumber=%s", (9999,))

```

# Práce s Views

Ještě si blíže ukážeme jak se pracuje s `view`. Ve své podstatě se to od práce s tabulkami liší pouze v tom, že zde nejsou k dispozici metody pro
modifikaci dat v tabulkách. Jinak je přístup identický. Možná bychom jen pro doplnění zdůraznili, že `view` se spouští na klientu a ne na databázovém serveru.
Proto se nejedná o pravé `view`, ale takové pseoudo `view` a na produkčním serveru nemusí ani ve skutečnosti existovat. Potřebuje pouze, aby
existovalo v době generování `Model`ů a `DataManager`ů pomocí SZN DAOGenu při vývoji aplikace. Odměnou za tento přístup jak jsme již dříve uvedli je
neexistence problému s performance, které pro pro view s přibývajícími daty a filtrováním `where` podmínkou nad nimi typické.

Pomocí `view` si můžeme dovolit provádět jakkoli složitá tabulková spojení i s komplikovanými projekcemi nad sloupečky. Což u přístupů podobným těm jak
pracuje `SQLAlchemy` bývá čast problém, nemluvě o špatné čitelnosti takto zapsaného dotazu.

Zkusme si jednoduchý příklad tohoto SQL příkazu:
```sql
SELECT 
    o.`orderNumber`, 
    od.`productCode`, 
    od.`quantityOrdered`, 
    p.`productName`, 
    p.`quantityInStock`,
    IF(p.`quantityInStock` > od.`quantityOrdered`, "enough", "to_stock_needed") AS productInStockStatus
FROM orders AS o
LEFT JOIN orderdetails AS od ON od.`orderNumber`=o.`orderNumber`
LEFT JOIN products AS p ON p.`productName`
WHERE o.`status`="In Process"
```

převést na `view`

```sql
DELIMITER $$

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`%` SQL SECURITY DEFINER VIEW `view_orders_to_be_processed` AS (
SELECT
  `o`.`orderNumber`      AS `orderNumber`,
  `od`.`productCode`     AS `productCode`,
  `od`.`quantityOrdered` AS `quantityOrdered`,
  `p`.`productName`      AS `productName`,
  `p`.`quantityInStock`  AS `quantityInStock`,
  IF((`p`.`quantityInStock` > `od`.`quantityOrdered`),'enough','to_stock_needed') AS `productInStockStatus`
FROM ((`orders` `o`
    LEFT JOIN `orderdetails` `od` ON ((`od`.`orderNumber` = `o`.`orderNumber`)))
    LEFT JOIN `products` `p` ON (`p`.`productName`))
WHERE (`o`.`status` = 'In Process'))$$

DELIMITER ;
```

Spusťme znovu SZN DAOGen pomocí uloženého bash skriptu `szndaogen-localhost-classicmodels.sh`, abychom nemuseli znovu vyplňovat údaje o databázovém připojení atp.
```bash
./szndaogen-localhost-classicmodels.sh

Writing model `Customers` into `example_dao/models/customers_model.py`
Skipping manager `Customers` exists `example_dao/managers/customers_manager.py`
Writing manager `Customers` into `example_dao/managers/base/customers_manager_base.py`
Writing model `Employees` into `example_dao/models/employees_model.py`
Skipping manager `Employees` exists `example_dao/managers/employees_manager.py`
Writing manager `Employees` into `example_dao/managers/base/employees_manager_base.py`
Writing model `Offices` into `example_dao/models/offices_model.py`
Skipping manager `Offices` exists `example_dao/managers/offices_manager.py`
Writing manager `Offices` into `example_dao/managers/base/offices_manager_base.py`
Writing model `Orderdetails` into `example_dao/models/orderdetails_model.py`
Skipping manager `Orderdetails` exists `example_dao/managers/orderdetails_manager.py`
Writing manager `Orderdetails` into `example_dao/managers/base/orderdetails_manager_base.py`
Writing model `Orders` into `example_dao/models/orders_model.py`
Skipping manager `Orders` exists `example_dao/managers/orders_manager.py`
Writing manager `Orders` into `example_dao/managers/base/orders_manager_base.py`
Writing model `Payments` into `example_dao/models/payments_model.py`
Skipping manager `Payments` exists `example_dao/managers/payments_manager.py`
Writing manager `Payments` into `example_dao/managers/base/payments_manager_base.py`
Writing model `Productlines` into `example_dao/models/productlines_model.py`
Skipping manager `Productlines` exists `example_dao/managers/productlines_manager.py`
Writing manager `Productlines` into `example_dao/managers/base/productlines_manager_base.py`
Writing model `Products` into `example_dao/models/products_model.py`
Skipping manager `Products` exists `example_dao/managers/products_manager.py`
Writing manager `Products` into `example_dao/managers/base/products_manager_base.py`
Writing model `ViewOrdersToBeProcessed` into `example_dao/models/vieworderstobeprocessed_model.py`
Writing manager `ViewOrdersToBeProcessed` into `example_dao/managers/vieworderstobeprocessed_manager.py`
Writing manager `ViewOrdersToBeProcessed` into `example_dao/managers/base/vieworderstobeprocessed_manager_base.py`
```

Za pár sekund máme hotový výsledek a už můžeme přístupovat k datům vystaveným přes `ViewOrdersToBeProcessedManager` a provádět nad nimi
operace filtrování pomocí `condition=`  a `condition_params=` podmínky, řazení pomocí `order_by=` případně limitovat počet záznamů pomocí `limit=`
parametru metody `select_all`.

```python
from example_dao.managers.view_orders_to_be_processed_manager import ViewOrdersToBeProcessedManager

manager = ViewOrdersToBeProcessedManager()
results = manager.select_all(order_by=("`od`.`quantityOrdered` DESC",), limit=10)

print("Top 10 ordered quauntities waiting for processing")
for item in results:
    print(f"{item.orderNumber} - {item.productCode}: {item.productName}, {item.quantityOrdered}/{item.quantityInStock}")
```

# Slučovací nástroje

Zkuste si představit situaci, že máte v databázi uloženy infomace, které logicky patří blíže k sobě. A potom při vystavení na restovém
API chcete takovéto informace mít schované pod nějakým zastřešujícím přístupovým klíčem. Takovou funkcionalitu přináší funkce, které
jsou součástí SZN DAOGenu. Ukážeme si jejich sílu na několika demonstrativních případech.

## auto_group_dict

Rěkněme, že chceme z databáze dostat seznam zaměstnanců a zjistit ve kterém městě v kanceláři sedí a jaké je do kanceláře telefonní číslo.
Tohle by nám mohl zařídit podobný SQL příkaz:
```sql
SELECT e.`firstName`, e.`lastName`, o.`country`, o.`city`, o.`phone`
FROM `employees` AS e
LEFT JOIN `offices` AS o ON e.`officeCode`=o.`officeCode`
WHERE e.`employeeNumber` IN (1002, 1056, 1102);
```

Výsledkem spuštění takového `view` může být něco podobného.
```python
result = [
  {'firstName': 'Diane', 'lastName': 'Murphy', 'country': 'USA', 'city': 'San Francisco', 'phone': '+1 650 219 4782'},
  {'firstName': 'Mary', 'lastName': 'Patterson', 'country': 'USA', 'city': 'San Francisco', 'phone': '+1 650 219 4782'},
  {'firstName': 'Gerard', 'lastName': 'Bondur', 'country': 'France', 'city': 'Paris', 'phone': '+33 14 723 4404'},
]
```

Nabízelo by se ovšem, aby položky `country`, `city` a `phone` byly zanořeny pod klíčem `office`. Tohle jde vyřešit použitím funkce `auto_group_dict`, 
jenom je potřeba udělat malou úpravu v SQL dotazu.

```sql
SELECT e.`firstName`, e.`lastName`,
    o.`country` as office___country,
    o.`city` as office___city,
    o.`phone` as office___phone
FROM `employees` AS e
LEFT JOIN `offices` AS o ON e.`officeCode`=o.`officeCode`
WHERE e.`employeeNumber` IN (1002, 1056, 1102);
```

Potom by výsledek view vypadal nějak takto:

```python
result = [
    {'firstName': 'Diane', 'lastName': 'Murphy', 'office___country': 'USA', 'office___city': 'San Francisco', 'office___phone': '+1 650 219 4782'},
    {'firstName': 'Mary', 'lastName': 'Patterson', 'office___country': 'USA', 'office___city': 'San Francisco', 'office___phone': '+1 650 219 4782'},
    {'firstName': 'Gerard', 'lastName': 'Bondur', 'office___country': 'France', 'office___city': 'Paris', 'office___phone': '+33 14 723 4404'}
]
```
Každou položku pole lze pak prohnat funkcí `auto_group_dict` z modulu `szndaogen.tools.auto_group`. Funkce počítá s tím, že položky, které se mají seskupit pod jeden klíč, jsou pojmenovány ve formátu `seskupujícíKlíč___názevPoložky` (odděleno 3mi podtržítky).
Výsledek by pak vypadal takto:
```python
from pprint import pprint
from szndaogen.tools.auto_group import auto_group_dict

new_result = [auto_group_dict(item) for item in result]
pprint(new_result)

[{'firstName': 'Diane',
  'lastName': 'Murphy',
  'office': {'city': 'San Francisco',
             'country': 'USA',
             'phone': '+1 650 219 4782'}},
 {'firstName': 'Mary',
  'lastName': 'Patterson',
  'office': {'city': 'San Francisco',
             'country': 'USA',
             'phone': '+1 650 219 4782'}},
 {'firstName': 'Gerard',
  'lastName': 'Bondur',
  'office': {'city': 'Paris',
             'country': 'France',
             'phone': '+33 14 723 4404'}}
]
```

## auto_group_list
Zkusme teď logiku obrátit. Budeme chtít zjistit osazenstvo něktré z kanceláří. Tohle zjistíme takovýmto příkazem:
```sql
SELECT o.`country`, o.`city`, o.`phone`, e.`firstName`, e.`lastName`
FROM `offices` AS o
LEFT JOIN `employees` AS e ON o.`officeCode`=e.`officeCode`
WHERE o.`officeCode` = 1;
```
Výsledek
```python
result = [
    {'country': 'USA', 'city': 'San Francisco', 'phone': '+1 650 219 4782', 'firstName': 'Diane', 'lastName': 'Murphy'}, 
    {'country': 'USA', 'city': 'San Francisco', 'phone': '+1 650 219 4782', 'firstName': 'Mary', 'lastName': 'Patterson'},
    {'country': 'USA', 'city': 'San Francisco', 'phone': '+1 650 219 4782', 'firstName': 'Jeff', 'lastName': 'Firrelli'},
    {'country': 'USA', 'city': 'San Francisco', 'phone': '+1 650 219 4782', 'firstName': 'Anthony', 'lastName': 'Bow'},
    {'country': 'USA', 'city': 'San Francisco', 'phone': '+1 650 219 4782', 'firstName': 'Leslie', 'lastName': 'Jennings'},
    {'country': 'USA', 'city': 'San Francisco', 'phone': '+1 650 219 4782', 'firstName': 'Leslie forever', 'lastName': 'Thompson'},
]
```
Už na první pohled je zjevné, že by bylo šikovnější mít data rozdělena pro kancelář ve výsledku jenom 1x a seznam zaměstnanců pod klíčem employee. Upravíme si `view` do této podoby:
```sql
SELECT o.`country`, o.`city`, o.`phone`, 
    e.`firstName` AS employee__firstName,
    e.`lastName` AS employee__lastName
FROM `offices` AS o
LEFT JOIN `employees` AS e ON o.`officeCode`=e.`officeCode`
WHERE o.`officeCode` = 1;
```
A zkusíme výsledek prohnat funkcí `auto_group_list`, která počítá s tím, že položky, které se mají seskupit do jednoho pole pod zvolený klíč, jsou pojmenovány ve formátu `seskupujícíKlíč__názevPoložky` (odděleno 2mi podtržítky).
```python
from pprint import pprint
from szndaogen.tools.auto_group import auto_group_list

new_result = auto_group_list(result)
pprint(new_result)

{
 'city': 'San Francisco',
 'country': 'USA',
 'phone': '+1 650 219 4782',
 'employee': [{'firstName': 'Diane', 'lastName': 'Murphy'},
              {'firstName': 'Mary', 'lastName': 'Patterson'},
              {'firstName': 'Jeff', 'lastName': 'Firrelli'},
              {'firstName': 'Anthony', 'lastName': 'Bow'},
              {'firstName': 'Leslie', 'lastName': 'Jennings'},
              {'firstName': 'Leslie forever', 'lastName': 'Thompson'}],
}
```

## auto_group_list_by_pkeys
V předchozím příkladě se setkáváme s určitou nevýhodou a to tou, že jsme schopni takto sloučit data jenom pro jednu kancelář, ale v reálu budou nastávat
případy, kdy chceme vypsat na API zaměstnance ze všech kancelářích najednou. Udělat to lze, ale musíme jít slučovací funkci trošku naproti tím, že ji řekněme
z čeho má se má skládat slučovací klíč a které položky má pak dávat k sobě. V tomto případě se nabízí jako slučovací klíč si jednoduše zvolit 'officeCode' kanceláře.

```sql
SELECT o.`officeCode`,o.`country`, o.`city`, o.`phone`, 
    e.`firstName` AS employee__firstName,
    e.`lastName` AS employee__lastName
FROM `offices` AS o
LEFT JOIN `employees` AS e ON o.`officeCode`=e.`officeCode`
```

Výsledek rovnou proženeme funkcí `auto_group_list_by_pkeys` a jako slučovací klíč definujeme tuple `("officeCode",)`

```python
from pprint import pprint
from szndaogen.tools.auto_group import auto_group_list_by_pkeys

new_result = auto_group_list_by_pkeys(("officeCode",) result)
pprint(new_result)

{'1': {'officeCode': '1',
       'city': 'San Francisco',
       'country': 'USA',
       'phone': '+1 650 219 4782',
       'employee': [{'firstName': 'Diane', 'lastName': 'Murphy'},
                    {'firstName': 'Mary', 'lastName': 'Patterson'},
                    {'firstName': 'Jeff', 'lastName': 'Firrelli'},
                    {'firstName': 'Anthony', 'lastName': 'Bow'},
                    {'firstName': 'Leslie', 'lastName': 'Jennings'},
                    {'firstName': 'Leslie forever', 'lastName': 'Thompson'}],
       },
 '2': {'officeCode': '2','city': 'Boston',
       'country': 'USA',
       'phone': '+1 215 837 0825',
       'employee': [{'firstName': 'Julie', 'lastName': 'Firrelli'},
                    {'firstName': 'Steve', 'lastName': 'Patterson'}],
       },
}
```

# Závěr
Na závěr bychom rádi shrnuli několi výhod a nevýhod představeného řešení.
výhody:
- změny ve struktuře je potřeba udělat jenom na jedné straně aplikace a to na databázi
- nemusíte otrocky psát modely pro tabulky a hlídat si konvenci a strukturu zápisu mezi jednotlivými modely
- automaticky se generují metainformace z tabulek do docstringů v modelech
- pracuje jak s tabulkami tak s `views`
- `view` netrpí na výkonostní problémy
- `view` newmusí být nutně definováno v produkční DB, stačí jenom na DEVu
- šablony `Modely` a `DataManager`y jsou napsány v Jinja2 a každý si může definovat svou vlastní šablonu jak má `Model` nebo `DataManager` vypadat
- Code completion v PyCharmu funguje perfektně a napovídá Vám vše co máte v definicích `Model`ů nebo `DataManager`ů zapsáno
- je to jednoduché a rychlé k použití. Jakákoli změna v DB struktuře se do sekundy může přegenerovat v definicích `Model`ů nebo `DataManager`ů

nevýhody:
- před ostatními kolegy programátory se může stát, že se budete stydět za to, že pracujete s nečím tak jednoduchým a dělá to práci za Vás
- jednu opravdovou nevýhodu tohle řešení v sobě opravdu skrývá a to, že při spolupráci více lidí na jednom projektu je lepší mít pro každého člena separátní DB, aby se spouštěním generátoru nad společnou databází ostatním kolegům nedosávaly do pracovní větve změny jiných kolegů. My jsme to např. řešili tak, že generátor a commit změn v modelech jsme prováděli až v DEV větvi.

Snad i v nějkterém z Vašich projektů najde tato knihovna využití a budete ji používat se stejnou radostí jako my.
