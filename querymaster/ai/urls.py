from django.urls import include, path


urlpatterns = [
    path("v1/", include("querymaster.ai.api.v1.urls")),
]
