from celery import Celery


app = Celery("querymaster")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
