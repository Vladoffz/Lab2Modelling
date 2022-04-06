import random
import pandas as pd
import simpy as sp
import seaborn as sns
from matplotlib import pyplot as plt
from app.config import (
    AVG_SERVICE_TIME,
    CUSTOMER_INTERVAL,
    NUM_OF_BANK_TELLERS,
    RANDOM_SEED,
    SIM_TIME)


class Bank(object):

    def __init__(self, env: sp.Environment, num_bank_tellers, service_time):

        self.env = env
        self.tellers = [sp.Resource(env) for i in range(num_bank_tellers)]
        self.service_time = service_time
        self.customers_info = {}

    def service(self, customer_name: str):

        time_in_Bank = random.expovariate(1.0 / self.service_time)

        yield self.env.timeout(time_in_Bank)

        self.customers_info[f'{customer_name}']['finished_at'] = self.env.now
        self.customers_info[f'{customer_name}']['lead_time'] = time_in_Bank


def customer(env: sp.Environment, name: str, bank: Bank):

    arrive = env.now
    queue_length = [
        no_in_system(bank.tellers[i]) for i in range(len(bank.tellers))
    ]
    for i in range(len(queue_length)):
        if queue_length[i] == 0 or queue_length[i] == min(queue_length):
            choice = i

            break

    with bank.tellers[choice].request() as req:
        # waiting in queue
        yield req
        wait = env.now - arrive
        # we got to the bank teller
        bank.customers_info[f'{name}'] = {
            'name': f"Customer {name}",
            'arrival': arrive,
            'queue_status': queue_length,
            'chosen_queue': choice,
            'wait_in_queue': wait,
        }

        yield env.process(bank.service(name))


def no_in_system(bank_teller: sp.Resource) -> int:
    """Total number of customers in the resource bank teller."""
    return max([0, len(bank_teller.put_queue) + bank_teller.count])


def setup_simulation(
        env: sp.Environment,
        bank: Bank,
        customer_interval: float
):

    iteration_number = 0

    while True:
        yield env.timeout(random.expovariate(1.0 / customer_interval))
        iteration_number += 1
        env.process(customer(env, iteration_number, bank))


def build_histogram(data: dict, histogram_name: str):

    df = pd.DataFrame.from_dict(
        data, orient='index', columns=[
            'wait_in_queue', 'lead_time'
        ])

    sns.set_style("darkgrid")
    ax = sns.histplot(data=df, kde=True, bins='auto')
    plt.xlabel("Time")
    plt.ylabel("Count of customers")

    for i in range(2):
        labels = [str(v) if v else '' for v in ax.containers[i].datavalues]
        ax.bar_label(ax.containers[i], labels=labels)

    # ax.bar_label(ax.containers[0], color='orange')
    ax.set_title(histogram_name, fontsize=18)
    plt.title(histogram_name)
    plt.show()


def load_csv_file(data: dict):

    df = pd.DataFrame.from_dict(data)
    df.T.to_csv('simulation_results.csv')


if __name__ == "__main__":

    try:
        random.seed(RANDOM_SEED)
        env = sp.Environment()
        bank = Bank(
            env,
            NUM_OF_BANK_TELLERS,
            AVG_SERVICE_TIME
        )
        env.process(setup_simulation(
            env,
            bank,
            CUSTOMER_INTERVAL
        ))
        # env.run(until=SIM_TIME)
        while env.peek() < SIM_TIME:
            env.step()
        build_histogram(bank.customers_info, 'Histogram')
        load_csv_file(bank.customers_info)

    except Exception as ex:
        print(ex)
