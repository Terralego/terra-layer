from django.apps import AppConfig
from celery import app as celery_app

class TerraLayerConfig(AppConfig):
    name = 'terralayer'
