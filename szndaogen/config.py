class Config:
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = ""
    MYSQL_USER: str = "mysql"
    MYSQL_PASSWORD: str = ""
    MYSQL_POOL_SIZE: int = None
    MYSQL_POOL_CONNECTION_TIMEOUT: int = 1000

    MANAGER_AUTO_MAP_MODEL_ATTRIBUTES = False
    """ If `True` => Model attributes will be mapped on class attributes automatically in results of `select_one` or `select_all` methods. """
