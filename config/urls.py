from decouple import config
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated


schema_view = get_schema_view(
    openapi.Info(
        title="QueryMaster API",
        default_version="v1",
    ),
    url=f"{config('BASE_URL')}",
    permission_classes=[IsAuthenticated],
    authentication_classes=(BasicAuthentication,),
    public=True,
)

urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),
    path("api/v1/core/", include("querymaster.core.api.v1.urls")),
    path("api/v1/users/", include("querymaster.users.api.v1.urls")),
    path("api/ai/", include("querymaster.ai.urls")),
    re_path(
        r"^app/confirm-email/(?P<key>[-:\w]+)/$",
        TemplateView.as_view(),
        name="account_confirm_email",
    ),
    re_path(
        r"^app/password-reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,32})/$",
        TemplateView.as_view(template_name="password_reset_confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema_swagger_ui",
    ),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
        path("silk/", include("silk.urls", namespace="silk")),
    ]
