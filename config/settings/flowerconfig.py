from decouple import config


broker = config("REDIS_URL")
url_prefix = "flower"
basic_auth = [f"{config('FLOWER_USERNAME')}:{config('FLOWER_PASSWORD')}"]
