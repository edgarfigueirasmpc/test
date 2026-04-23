from django.urls import path

from .views import app_login, app_logout, index

app_name = "planner"

urlpatterns = [
    path("entrar/", app_login, name="login"),
    path("salir/", app_logout, name="logout"),
    path("", index, name="index"),
]
