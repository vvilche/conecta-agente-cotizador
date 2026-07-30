import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5001')}"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"
