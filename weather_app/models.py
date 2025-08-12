from django.db import models

class WeatherRecord(models.Model):
    location_input = models.CharField(max_length=120)
    resolved_name = models.CharField(max_length=160)
    latitude = models.FloatField()
    longitude = models.FloatField()
    start_date = models.DateField()
    end_date = models.DateField()
    weather_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']

class SimpleSearch(models.Model):
    query_text = models.CharField(max_length=120)
    resolved_name = models.CharField(max_length=160)
    latitude = models.FloatField()
    longitude = models.FloatField()
    temperature = models.FloatField(null=True, blank=True)
    # Allow string symbol codes from met.no (e.g., 'clearsky_day')
    weather_code = models.CharField(max_length=40, null=True, blank=True)
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
