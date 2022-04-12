import os
import numpy as np
import pandas as pd


def get_statistics_bank(path_to_csv: str, file_name: str):

    bank = pd.read_csv(os.path.join(
        os.getcwd(), path_to_csv + file_name + '.csv'), delimiter=',')

    # Average load of each cashier
    chosen_queue_list = bank['chosen_queue'].tolist()

    print('Первая очердь вибрана кол-раз ' +
          str(sum(x == 0 for x in chosen_queue_list)))
    print('Вторая очердь вибрана кол-раз ' +
          str(sum(x == 1 for x in chosen_queue_list)))

    # The average number of customers in each queue
    queue_1_status = []
    queue_2_status = []

    print(bank['queue_status'][0][3])

    for i in range(len(bank['queue_status'])):

        queue_1_status.append(int(bank['queue_status'][i][1]))
        queue_2_status.append(int(bank['queue_status'][i][4]))

    q1 = np.array(queue_1_status)
    q2 = np.array(queue_2_status)

    print("Mean q1: " + str(q1.mean()))
    print("Mean q2: " + str(q2.mean()))

    # Середній час перебування клієнта в банку
    print("Mean wasted_time: " + str(bank['all_wasted_time'].mean()))


def get_statistics_hospital(path_to_csv: str, file_names: list):

    for item in file_names:
        hospital = pd.read_csv(os.path.join(
            os.getcwd(), path_to_csv + item + '.csv'), delimiter=',')

        wasted_time = np.array(hospital['all_wasted_time'])

        wasted_time = wasted_time[~np.isnan(wasted_time)]

        print(f'Mean wasted time ({item}) ' + str(wasted_time.mean()))
