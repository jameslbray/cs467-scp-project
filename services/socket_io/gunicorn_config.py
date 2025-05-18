import os

# Gunicorn config
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = 1  # multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
errorlog = "-"
loglevel = "info"
accesslog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Application config
wsgi_app = "app.main:app"
