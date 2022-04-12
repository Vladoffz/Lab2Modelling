import json
import os
from typing import Union, get_type_hints
from environs import Env

env = Env()
env.read_env()


class UnconfiguredEnvironment(Exception):
    pass


class UnableToCastValue(Exception):
    pass


def _parse_bool(val: Union[str, bool]) -> bool:
    if type(val) == bool:
        return val
    else:
        return val.lower() in ['true', 'yes', '1']


class AppConfiguration:
    ENABLE_SEED: bool
    SIM_TIME: int
    RANDOM_SEED: int
    PATH_RESULTS_BANK: str
    PATH_RESULTS_HOSPITAL: str

    def __init__(self, env):
        for field in self.__annotations__:

            default_value = getattr(self, field, None)

            if default_value is None and env.get(field) is None:
                raise UnconfiguredEnvironment(
                    f"The {field} field is required")
            try:
                var_type = get_type_hints(self.__class__)[field]

                if var_type == bool:
                    value = _parse_bool(env.get(field, default_value))
                elif var_type == dict:
                    value = json.loads(
                        env.get(field, default_value).replace("\\\n", ""))
                elif var_type == list:
                    value = json.loads(env.get(field, default_value))
                else:
                    value = var_type(env.get(field, default_value))

                self.__setattr__(field, value)
            except ValueError:
                raise UnableToCastValue(
                    f"Unable to cast value of {env[field]} "
                    f"to type {var_type} for {field} field")

    def __repr__(self):
        return str(self.__dict__)


class BankConfiguration(AppConfiguration):
    NUM_OF_BANK_TELLERS: int
    AVG_SERVICE_TIME: float
    CUSTOMER_INTERVAL: float


class HospitalConfiguration(AppConfiguration):
    PATIENT_TYPES: list
    PATIENT_INTERVAL_TIMES: dict
    NUMBER_OF_HOSPITAL_STAFF: dict
    AVG_REGISTRATION_TIMES: dict
    RECEPTION_TRIP_TIME: float
    CHAMBER_TRIP_TIMES: dict
    LAB_TRIP_TIMES: dict
    LAB_REGISTRY_TIMES: dict
    LAB_ANALYSIS_TIMES: dict


Config = AppConfiguration(os.environ)
BankConfig = BankConfiguration(os.environ)
HospitalConfig = HospitalConfiguration(os.environ)
