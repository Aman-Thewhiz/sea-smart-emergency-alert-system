import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

workers = 1
threads = 4

timeout = 120
graceful_timeout = 120

keepalive = 5

worker_class = "gthread"

loglevel = "info"

accesslog = "-"
errorlog = "-"