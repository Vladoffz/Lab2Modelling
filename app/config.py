from environs import Env

env = Env()
env.read_env()

RANDOM_SEED = env.int("RANDOM_SEED")
SIM_TIME = env.int("SIM_TIME")
NUM_OF_BANK_TELLERS = env.int("NUM_OF_BANK_TELLERS")
AVG_SERVICE_TIME = env.float("AVG_SERVICE_TIME")
CUSTOMER_INTERVAL = env.float("CUSTOMER_INTERVAL")