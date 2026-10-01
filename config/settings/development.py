from .base import *
from decouple import config, Csv

DEBUG = True
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,web", cast=Csv())

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}