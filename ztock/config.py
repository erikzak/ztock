# -*- coding: utf-8 -*-
"""
Config handler. Reads/refreshes config from file and handles defaults.
"""
import copy
import json
from typing import Any, Dict, Union

from .utils import parse_decimal


_HIDE = [
    "password",
    "api_key",
]


class Undefined:
    """Undefined argument value."""
    pass


class Config:
    """
    Handles config init from file or dict.
    """
    market_data = None
    logging = None
    traders = []

    def __init__(self, input: Union[str, Dict[Any, Any]]) -> None:
        """
        Inits config object from config file or dict.

        :param input: path to config file or dict with params
        :type input: str or dict
        """
        if (isinstance(input, str)):
            self.file_path = input
        else:
            self.set_params(input)
        self.refresh()
        return

    def __repr__(self) -> str:
        params = copy.deepcopy(vars(self))
        _replace_sensitive_stuff(params)
        return f"{params}"

    def __str__(self) -> str:
        return self.__repr__()

    def get(self, param: str, default: Any = Undefined) -> Any:
        """Returns config parameter if it exists, or default."""
        if (not hasattr(self, param) and not isinstance(default, Undefined)):
            return default
        value = getattr(self, param)
        return value

    def refresh(self) -> None:
        """
        Refreshes config from file, if defined.
        """
        if (hasattr(self, "file_path")):
            self._read_config(self.file_path)
        return

    def _read_config(self, file_path: str) -> None:
        """
        Reads configuration file and applies settings.

        :param file_path: path to config file
        :type file_path: str
        """
        with open(file_path) as reader:
            # Remove comment lines
            config = " ".join([
                line
                for line in reader.readlines()
                if not (line.strip().startswith("//"))
            ])
        config = json.loads(config)
        self.set_params(config)
        return

    def set_params(self, params: Dict[Any, Any]):
        for param, value in params.items():
            # Convert floats to Decimal
            if (isinstance(value, float)):
                value = parse_decimal(value)
                setattr(self, param, value)

            # Convert dicts to new Config instances
            elif (isinstance(value, dict)):
                subsection = getattr(self, param, None)
                if (subsection is not None):
                    subsection.set_params(value)
                else:
                    setattr(self, param, Config(value))
            elif (isinstance(value, list)):
                for i, list_value in enumerate(value):
                    if (isinstance(list_value, dict)):
                        value[i] = Config(list_value)
                setattr(self, param, value)

            else:
                setattr(self, param, value)
        return


def _replace_sensitive_stuff(params: Dict[Any, Any]):
    """Replaces passwords and API keys in __repr__/logs."""
    for param in params.keys():
        if (param.lower() in _HIDE):
            params[param] = "***"
    return params
