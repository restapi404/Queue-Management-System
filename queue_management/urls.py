from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('queue_app.urls')),
    # Provide login/logout views at /accounts/ (used by @user_passes_test redirects)
    path('accounts/', include('django.contrib.auth.urls')),
]