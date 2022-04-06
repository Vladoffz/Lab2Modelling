import random
import numpy as np
import simpy as sp

from app.config import (
    PATIENT_TYPES,
    PATIENT_INTERVAL_TIMES,
    AVG_REGISTRATION_TIMES,
    RECEPTION_TRIP_TIME,
    CHAMBER_TRIP_TIME_LOW,
    CHAMBER_TRIP_TIME_HIGH,
    LAB_TRIP_TIME_LOW,
    LAB_TRIP_TIME_HIGH,
    LAB_REGISTRY_TIME_SHAPE,
    LAB_REGISTRY_TIME_SCALE,
    LAB_ANALYSIS_TIME_SHAPE,
    LAB_ANALYSIS_TIME_SCALE,
    RANDOM_SEED,
    SIM_TIME)


class ReceptionDepartment(object):

    def __init__(
            self,
            env: sp.Environment,
            num_doctors: int,
            reception_trip_time: float,
            registration_times: dict
    ):

        self.env = env
        self.doctor_on_duty = sp.PriorityResource(env, num_doctors)
        self.reception_trip_time = reception_trip_time
        self.registration_times = registration_times

    def trip_to_reception(self, patient_name: str):

        spent_time = random.expovariate(
            1.0 / self.reception_trip_time)

        yield self.env.timeout(spent_time)

    def registration(self, patient_type: str, patient_name: str):

        spent_time = random.expovariate(
            1.0 / self.registration_times[patient_type])

        yield self.env.timeout(spent_time)


class MedicalChamber(object):

    def __init__(
            self,
            env: sp.Environment,
            num_nurses: int,
            accompaniment_time_low: float,
            accompaniment_time_high: float
    ):

        self.env = env
        self.nurse = sp.Resource(env, num_nurses)
        self.accompaniment_time_low = accompaniment_time_low
        self.accompaniment_time_high = accompaniment_time_high

    def nurse_accompaniment(self, patient_name: str):

        spent_time = np.random.randint(
            self.accompaniment_time_low, self.accompaniment_time_high)

        yield self.env.timeout(spent_time)


class LabRegistry(object):

    def __init__(
            self,
            env: sp.Environment,
            num_administrators: int,
            trip_time_low: float,
            trip_time_high: float,
            registry_time_shape: float,
            registry_time_scale: float
    ):

        self.env = env
        self.registry_admin = sp.Resource(env, num_administrators)
        self.trip_time_low = trip_time_low
        self.trip_time_high = trip_time_high
        self.registry_time_shape = registry_time_shape
        self.registry_time_scale = registry_time_scale

    def trip_to_lab(self, patient_name: str):

        spent_time = np.random.randint(
            self.trip_time_low, self.trip_time_high)

        yield self.env.timeout(spent_time)

    def service(self, patient_name: str):

        spent_time = np.random.gamma(
            shape=self.registry_time_shape, scale=self.registry_time_scale)

        yield self.env.timeout(spent_time)


class LabWaitingRoom(object):

    def __init__(
            self,
            env: sp.Environment,
            num_assistants: int,
            analysis_time_shape: float,
            analysis_time_scale: float
    ):

        self.env = env
        self.lab_assistant = sp.Resource(env, num_assistants)
        self.analysis_time_shape = analysis_time_shape
        self.analysis_time_scale = analysis_time_scale

    def analyse(self, patient_name: str):

        spent_time = np.random.gamma(
            shape=self.analysis_time_shape, scale=self.analysis_time_scale)

        yield self.env.timeout(spent_time)


class CustomerInfo(object):

    __match_args__ = ('name', 'customer_type')

    def __init__(
        self,
        name: str,
        customer_type: str
    ):
        self.name = name
        self.customer_type = customer_type


class Hospital(object):

    def __init__(
        self,
        env: sp.Environment,
        patient_types: list,
        patient_intervals: dict,
        reception: ReceptionDepartment,
        medical_chamber: MedicalChamber,
        lab_registry: LabRegistry,
        lab_waiting_room: LabWaitingRoom
    ):
        self.env = env
        self.patient_types = patient_types
        self.patient_intervals = patient_intervals
        self.reception = reception
        self.medical_chamber = medical_chamber
        self.lab_registry = lab_registry
        self.lab_waiting_room = lab_waiting_room

    def handling_customer(self, customer_obj: CustomerInfo):

        match customer_obj:
            case CustomerInfo(str(name), "1" as type):

                with self.reception.doctor_on_duty.request(priority=1) as req:

                    self.reception.trip_to_reception(name)
                    arrive = self.env.now

                    # waiting in queue
                    yield req
                    wait = self.env.now - arrive
                    # we got to the doctor on duty
                    self.env.process(
                        self.reception.registration(type, name))

                with self.medical_chamber.nurse.request() as req:

                    arrive_after_register = self.env.now
                    # waiting in queue
                    yield req
                    wait = self.env.now - arrive_after_register
                    # print(f"Ожидал медсестру - {wait}. Пользователь {name}.")
                    # go to the chamber
                    self.env.process(
                        self.medical_chamber.nurse_accompaniment(name))

            case CustomerInfo(str(name), "2" | "3" as type):

                with self.reception.doctor_on_duty.request(priority=2) as req:

                    self.reception.trip_to_reception(name)

                    arrive = self.env.now

                    # waiting in queue
                    yield req
                    wait = self.env.now - arrive
                    # we got to the doctor on duty
                    self.env.process(self.reception.registration(type, name))

                with self.lab_registry.registry_admin.request() as req:

                    self.lab_registry.trip_to_lab(name)

                    arrive = self.env.now
                    # waiting in queue
                    yield req
                    wait = self.env.now - arrive
                    # we got to the administrator
                    self.env.process(self.lab_registry.service(name))

                with self.lab_waiting_room.lab_assistant.request() as req:

                    arrive = self.env.now
                    # waiting in queue
                    yield req
                    wait = self.env.now - arrive
                    # we got to the administrator
                    self.env.process(self.lab_waiting_room.analyse(name))

                if type == "2":

                    self.lab_registry.trip_to_lab(name)

                    with self.reception.doctor_on_duty.request(priority=1) as req:

                        arrive = self.env.now
                        # waiting in queue
                        yield req
                        wait = self.env.now - arrive
                        # we got to the doctor on duty
                        self.env.process(
                            self.reception.registration(type, name))

                    with self.medical_chamber.nurse.request() as req:

                        arrive_after_register = self.env.now
                        # waiting in queue
                        yield req
                        wait = self.env.now - arrive_after_register
                        self.env.process(
                            self.medical_chamber.nurse_accompaniment(name))

            case _:
                print("Такого типа пациентов нет")


def start_simulation(env, patient_intervals, hospital):

    iteration_number = 0

    while True:
        i = random.randint(1, 3)
        yield env.timeout(
            random.expovariate(1.0 / patient_intervals[str(i)]))
        iteration_number += 1
        env.process(hospital.handling_customer(
            CustomerInfo(str(iteration_number), str(i))))

        print(
            f"Начал пользователь- {iteration_number}. Тип {i}. TIME - {env.now}")


if __name__ == "__main__":

    try:

        # random.seed(RANDOM_SEED)
        env = sp.Environment()
        reception = ReceptionDepartment(
            env,
            2,
            RECEPTION_TRIP_TIME,
            AVG_REGISTRATION_TIMES,
        )
        chamber = MedicalChamber(
            env,
            3,
            CHAMBER_TRIP_TIME_LOW,
            CHAMBER_TRIP_TIME_HIGH,
        )
        lab_registry = LabRegistry(
            env,
            2,
            LAB_TRIP_TIME_LOW,
            LAB_TRIP_TIME_HIGH,
            LAB_REGISTRY_TIME_SHAPE,
            LAB_REGISTRY_TIME_SCALE,
        )
        lab_waiting_room = LabWaitingRoom(
            env,
            2,
            LAB_ANALYSIS_TIME_SHAPE,
            LAB_ANALYSIS_TIME_SCALE,
        )
        hospital = Hospital(
            env,
            PATIENT_TYPES,
            PATIENT_INTERVAL_TIMES,
            reception,
            chamber,
            lab_registry,
            lab_waiting_room,
        )
        env.process(start_simulation(
            env,
            PATIENT_INTERVAL_TIMES,
            hospital,
        ))
        while env.peek() < SIM_TIME:
            env.step()

    except Exception as ex:
        print(ex)
