from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('ranges/', views.ranges_page, name='ranges'),
    path('api/weather', views.api_weather, name='api_weather'),
    path('api/records', views.records, name='records'),
    path('api/records/<int:pk>', views.record_detail, name='record_detail'),
    path('records/<int:pk>/', views.record_page, name='record_page'),
    path('searches/<int:pk>/', views.search_page, name='search_page'),
    path('api/searches', views.searches, name='searches'),
    path('api/searches/<int:pk>', views.delete_search, name='delete_search'),
]
