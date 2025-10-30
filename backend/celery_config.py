"""
Celery configuration for distributed task processing
"""
import os

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")

# Celery broker settings
broker_url = REDIS_URL
result_backend = REDIS_URL

# Task settings
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "UTC"
enable_utc = True

# Task execution settings
task_track_started = True  # Track when task starts
task_time_limit = 30 * 60  # 30 minutes hard limit
task_soft_time_limit = 25 * 60  # 25 minutes soft limit

# Worker settings
worker_prefetch_multiplier = 5
worker_max_tasks_per_child = 1000

# Result backend settings
result_expires = 3600  # Results expire after 1 hour
