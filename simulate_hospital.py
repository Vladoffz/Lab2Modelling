import random
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import simpy as sp
import seaborn as sns
from utils.load import load_csv_file
from utils.statistic import get_statistics_hospital
from app.config import Config, HospitalConfig


class PatientInfo(object):

    __match_args__ = ('type', 'request')

    def __init__(
        self,
        name: str,
        type: str
    ):
        self.name = name
        self.type = type
        self.request = {
            'is_reg_finish': False,
            'is_service_finish': False,
            'is_analyse_finish': False,
            'is_re-reg_finish': False,
        }


class ReceptionDepartment(object):

    def __init__(
            self,
            env: sp.Environment,
            hospital_staff: dict,
            reception_trip_time: float,
            registration_times: dict,
            accompaniment_time: dict,
    ):

        self.env = env
        self.hospital_staff = hospital_staff
        self.doctor_on_duty = sp.PriorityResource(
            env, hospital_staff['doctors'])
        self.nurse = sp.PriorityResource(env, hospital_staff['nurses'])
        self.reception_trip_time = reception_trip_time
        self.registration_times = registration_times
        self.accompaniment_time = accompaniment_time

    def trip_to_reception(
        self,
        patient: PatientInfo,
        start_at: float
    ):

        spent_time = random.expovariate(
            1.0 / self.reception_trip_time)

        yield self.env.timeout(spent_time)

        if patient.type == "1":
            result_type1[f'{patient.name}'] = {
                'name': f"Customer {patient.name}",
                'started_at': start_at,
                'trip_to_reception_time': spent_time
            }
        elif patient.type == "2":
            result_type2[f'{patient.name}'] = {
                'name': f"Customer {patient.name}",
                'started_at': start_at,
                'trip_to_reception_time': spent_time
            }
        elif patient.type == "3":
            result_type3[f'{patient.name}'] = {
                'name': f"Customer {patient.name}",
                'started_at': start_at,
                'trip_to_reception_time': spent_time
            }

    def registration(
        self,
        patient: PatientInfo,
        wait: float
    ):
        spent_time = random.expovariate(
            1.0 / self.registration_times[patient.type])

        yield self.env.timeout(spent_time)

        dict = chose_dict(patient)

        dict.update({'wait_doctor': wait})
        dict.update({'registration_time': spent_time})

    def accompaniment_to_chamber(
        self,
        patient: PatientInfo,
        wait: float
    ):
        spent_time = np.random.uniform(
            self.accompaniment_time['low'], self.accompaniment_time['high'])

        yield self.env.timeout(spent_time)

        dict = chose_dict(patient)

        dict.update({'wait_accompaniment_time': wait})
        dict.update({'accompaniment_time': spent_time})
        dict.update({'finished_at':  self.env.now})
        wasted_time = dict['finished_at'] - dict['started_at']
        dict.update({'all_wasted_time': wasted_time})

    def request_registration(self, patient: PatientInfo, priority: int = 0):

        start_at = self.env.now

        if patient.request['is_reg_finish'] == False:
            yield self.env.process(self.trip_to_reception(
                patient, start_at))
        elif patient.request['is_analyse_finish'] == True:
            yield self.env.process(laboratory.trip(patient))

        with self.doctor_on_duty.request(priority) as req:

            arrive_at = self.env.now
            # waiting in queue
            yield req
            wait = self.env.now - arrive_at
            # we got to the doctor on duty
            yield self.env.process(self.registration(patient, wait))

            if patient.request['is_reg_finish'] == True:
                patient.request.update({'is_re-reg_finish': True})
            else:
                patient.request.update({'is_reg_finish': True})

            hospital.handling_customer(patient)

    def request_accompaniment(self, patient: PatientInfo, priority: int = 0):

        with self.nurse.request(priority) as req:

            arrive = self.env.now
            # waiting in queue
            yield req
            wait = self.env.now - arrive
            # go to the chamber
            yield self.env.process(
                self.accompaniment_to_chamber(patient, wait))


class Labaratory(object):

    def __init__(
            self,
            env: sp.Environment,
            hospital_staff: dict,
            trip_time: dict,
            registry_time: dict,
            analysis_time: dict,
    ):

        self.env = env
        self.hospital_staff = hospital_staff
        self.registry_admin = sp.PriorityResource(
            env, hospital_staff['admins'])
        self.lab_assistant = sp.PriorityResource(
            env, hospital_staff['lab_assistans'])
        self.trip_time = trip_time
        self.registry_time = registry_time
        self.analysis_time = analysis_time

    def trip(self, patient: PatientInfo):

        spent_time = np.random.uniform(
            self.trip_time['low'], self.trip_time['high'])

        yield self.env.timeout(spent_time)

        dict = chose_dict(patient)

        if patient.request['is_analyse_finish'] == True:
            old_value = dict.get('trip_time')
            dict.update({'trip_time': old_value + spent_time})
        else:
            dict.update({'trip_time': spent_time})

    def service(self, patient: PatientInfo, wait: float):

        spent_time = np.random.gamma(
            self.registry_time['shape'], 1.0 / self.registry_time['scale'])

        yield self.env.timeout(spent_time)

        dict = chose_dict(patient)

        dict.update({'wait_admin': wait})
        dict.update({'service_time': spent_time})

    def analyse(self, patient: PatientInfo, wait: float):

        spent_time = np.random.gamma(
            self.analysis_time['shape'], 1.0 / self.analysis_time['scale'])

        yield self.env.timeout(spent_time)

        dict = chose_dict(patient)

        dict.update({'wait_assistent': wait})
        dict.update({'analyse_time': spent_time})

    def request_service(self, patient: PatientInfo, priority: int = 0):

        yield self.env.process(self.trip(patient))

        with self.registry_admin.request(priority) as req:

            arrive = self.env.now
            # waiting in queue
            yield req
            wait = self.env.now - arrive
            # we got to the administrator
            yield self.env.process(self.service(patient, wait))

            patient.request.update({'is_service_finish': True})
            hospital.handling_customer(patient)

    def request_analyse(self, patient: PatientInfo, priority: int = 0):

        with self.lab_assistant.request(priority) as req:

            arrive = self.env.now
            # waiting in queue
            yield req
            wait = self.env.now - arrive
            # we got to the assistent
            yield self.env.process(self.analyse(patient, wait))

            if patient.type == "3":

                dict = chose_dict(patient)
                patient.request.update({'is_analyse_finish': True})
                dict.update({'finished_at': self.env.now})
                wasted_time = dict['finished_at'] - dict['started_at']
                dict.update({'all_wasted_time': wasted_time})

            elif patient.type == "2":

                patient.request.update({'is_analyse_finish': True})
                hospital.handling_customer(patient)


class Hospital(object):

    def __init__(
        self,
        env: sp.Environment,
        patient_types: list,
        patient_intervals: dict,
        reception: ReceptionDepartment,
        laboratory: Labaratory,
    ):
        self.env = env
        self.patient_types = patient_types
        self.patient_intervals = patient_intervals
        self.reception = reception
        self.laboratory = laboratory

    def start_simulation(self):

        iteration_number = 0

        while True:

            i = random.randint(
                min(self.patient_types), max(self.patient_types))

            yield self.env.timeout(
                random.expovariate(1.0 / self.patient_intervals[str(i)]))

            iteration_number += 1

            self.handling_customer(
                PatientInfo(str(iteration_number), str(i)))

    def handling_customer(self, patient: PatientInfo):

        match patient:
            case PatientInfo(
                "1" as type, request
            ) if request['is_reg_finish'] == False:

                self.env.process(
                    self.reception.request_registration(patient, 1))

            case PatientInfo(
                "1" as type, request
            ) if request['is_reg_finish'] == True:

                self.env.process(
                    self.reception.request_accompaniment(patient))

            case PatientInfo(
                "2" | "3" as type, request
            ) if request['is_reg_finish'] == False:

                self.env.process(
                    self.reception.request_registration(patient, 2))

            case PatientInfo(
                "2" | "3" as type, request
            ) if request['is_reg_finish'] == True \
                    and request['is_service_finish'] == False:

                self.env.process(
                    self.laboratory.request_service(patient))

            case PatientInfo(
                "2" | "3" as type, request
            ) if request['is_service_finish'] == True \
                    and request['is_analyse_finish'] == False:

                self.env.process(
                    self.laboratory.request_analyse(patient))

            case PatientInfo(
                "2" as type, request
            ) if request['is_analyse_finish'] == True \
                    and request['is_re-reg_finish'] == False:

                self.env.process(
                    self.reception.request_registration(patient, 1))

            case PatientInfo(
                "2" as type, request
            ) if request['is_analyse_finish'] == True \
                    and request['is_re-reg_finish'] == True:

                self.env.process(
                    self.reception.request_accompaniment(patient))

            case _:
                print("Такого типа пациентов нет")


def chose_dict(patient: PatientInfo) -> dict:

    match patient:
        case PatientInfo("1" as type, _):
            dict = result_type1[f'{patient.name}']
        case PatientInfo("2" as type, _):
            dict = result_type2[f'{patient.name}']
        case PatientInfo("3" as type, _):
            dict = result_type3[f'{patient.name}']

    return dict


def build_histogram(data: dict, patinet_type: str, colums: list):

    match patinet_type:
        case "1":
            df = pd.DataFrame.from_dict(
                data, orient='index', columns=colums)
        case "2":
            df = pd.DataFrame.from_dict(
                data, orient='index', columns=colums)
        case "3":
            df = pd.DataFrame.from_dict(
                data, orient='index', columns=colums)

    sns.set_style("darkgrid")
    ax = sns.histplot(data=df, bins='auto')
    plt.xlabel("Time")
    plt.ylabel("Count")

    for c in ax.containers:

        labels = [f'{h:0.1f}' if (h := v.get_height()) != 0 else '' for v in c]

        ax.bar_label(c, labels=labels, fontsize=8, padding=3)

    ax.set_title("Patient type - " + patinet_type, fontsize=18)
    plt.title("Patient type - " + patinet_type)
    plt.show()


if __name__ == "__main__":

    try:

        result_type1 = {}
        result_type2 = {}
        result_type3 = {}

        env = sp.Environment()

        reception = ReceptionDepartment(
            env,
            HospitalConfig.NUMBER_OF_HOSPITAL_STAFF,
            HospitalConfig.RECEPTION_TRIP_TIME,
            HospitalConfig.AVG_REGISTRATION_TIMES,
            HospitalConfig.CHAMBER_TRIP_TIMES,
        )

        laboratory = Labaratory(
            env,
            HospitalConfig.NUMBER_OF_HOSPITAL_STAFF,
            HospitalConfig.LAB_TRIP_TIMES,
            HospitalConfig.LAB_REGISTRY_TIMES,
            HospitalConfig.LAB_ANALYSIS_TIMES,
        )

        hospital = Hospital(
            env,
            HospitalConfig.PATIENT_TYPES,
            HospitalConfig.PATIENT_INTERVAL_TIMES,
            reception,
            laboratory
        )

        env.process(hospital.start_simulation())

        while env.peek() < Config.SIM_TIME:
            env.step()

        colums_type1 = [
            'trip_to_reception_time', 'wait_doctor', 'registration_time',
            'wait_accompaniment_time',
            'accompaniment_time'
        ]

        colums_1_type2 = [
            'trip_to_reception_time', 'wait_doctor', 'registration_time'
        ]

        colums_2_type2 = [
            'trip_time', 'wait_admin', 'service_time', 'wait_assistent',
            'analyse_time'
        ]

        colums_3_type2 = [
            'wait_accompaniment_time',
            'accompaniment_time'
        ]

        colums_1_type3 = [
            'trip_to_reception_time', 'wait_doctor', 'registration_time',
        ]

        colums_2_type3 = [
            'wait_assistent', 'analyse_time'
        ]

        colusms_finish = [
            'all_wasted_time'
        ]

        build_histogram(result_type1, '1', colums_type1)
        build_histogram(result_type1, '1', colusms_finish)

        build_histogram(result_type2, '2', colums_1_type2)
        build_histogram(result_type2, '2', colums_2_type2)
        build_histogram(result_type2, '2', colums_3_type2)
        build_histogram(result_type2, '2', colusms_finish)

        build_histogram(result_type3, '3', colums_1_type3)
        build_histogram(result_type3, '3', colums_2_type3)
        build_histogram(result_type3, '3', colusms_finish)

        load_csv_file(
            result_type1,
            Config.PATH_RESULTS_HOSPITAL,
            'result_type1'
        )
        load_csv_file(
            result_type2,
            Config.PATH_RESULTS_HOSPITAL,
            'result_type2'
        )
        load_csv_file(
            result_type3,
            Config.PATH_RESULTS_HOSPITAL,
            'result_type3'
        )

        get_statistics_hospital(Config.PATH_RESULTS_HOSPITAL, [
            'result_type1', 'result_type2', 'result_type3'
        ])

    except Exception as ex:
        print(ex)
