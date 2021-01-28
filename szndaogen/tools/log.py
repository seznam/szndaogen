import sys
import traceback
from datetime import datetime
from .cli_colors import CMD, FG


class BaseLogger:
    def __init__(self):
        self.format_string = "{datetime} [{prefix}] {event} | {kwargs}"

    def _log(self, prefix: str, event: str, **kwargs) -> str:
        """
        Overwrite this method with your own logger
        :param prefix: Log prefix
        :param event: Log event (critical. error, exception, info, warning, debug)
        :param kwargs: Custom keyword arguments
        """
        return self.format_string.format(prefix=prefix, event=event, datetime=datetime.now(), kwargs=kwargs)

    def critical(self, event: str, **kwargs) -> str:
        return self._log("critical", event, **kwargs)

    def error(self, event: str, **kwargs) -> str:
        return self._log("error", event, **kwargs)

    def exception(self, event: str, **kwargs) -> str:
        return self._log("exception", event, **kwargs)

    def info(self, event: str, **kwargs) -> str:
        return self._log("info", event, **kwargs)

    def warning(self, event: str, **kwargs) -> str:
        return self._log("warning", event, **kwargs)

    def debug(self, event: str, **kwargs) -> str:
        return self._log("debug", event, **kwargs)


class StdOutLogger(BaseLogger):
    def _log(self, prefix: str, event: str, **kwargs) -> None:
        print(prefix, event, file=sys.stdout)
        for key, value in kwargs.items():
            print(f"    {key}: {value}", file=sys.stdout)

    def critical(self, event: str, **kwargs) -> None:
        return self._log(f"{FG.red}{CMD.bold}[CRITICAL ]{CMD.reset} ", event, **kwargs)  # red/bold

    def error(self, event: str, **kwargs) -> None:
        return self._log(f"{FG.red}[ERROR    ]{CMD.reset} ", event, **kwargs)  # red

    def exception(self, event: str, **kwargs) -> None:
        traceback.print_exc(file=sys.stdout)
        return self._log(f"{FG.purple}{CMD.bold}[EXCEPTION]{CMD.reset} ", event, **kwargs)  # purple/bold

    def info(self, event: str, **kwargs) -> None:
        return self._log("[INFO     ] ", event, **kwargs)

    def warning(self, event: str, **kwargs) -> None:
        return self._log(f"{FG.orange}[WARNING  ]{CMD.reset} ", event, **kwargs)  # orange

    def debug(self, event: str, **kwargs) -> None:
        return self._log("[DEBUG    ] ", event, **kwargs)


class Logger:
    """
    Static class proxy for logger instance. Usage: Logger.log.[method]
    """
    log: BaseLogger = BaseLogger()
    """ Logger instance. Default is BaseLogger with no output into file or stdout. """

    @classmethod
    def set_external_logger(cls, logger_instance: BaseLogger) -> BaseLogger:
        """
        Set custom or predefined logger instance based on BaseLogger interface.
        :param logger_instance: Custom logger instance
        :return: Instance of setted logger
        """
        cls.log = logger_instance
        return cls.log
