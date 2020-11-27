import helper
import redis

from environs import Env

env = Env()
env.read_env()
r = redis.Redis(host="0.0.0.0", port=env.int("CORE_PEER_REDIS_PORT"))

def main():
    if len(r.smembers("registred")) == 0:
        helper.register_target_peer()

if __name__ == "__main__":
    main()
