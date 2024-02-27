"""sample_app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import path

from .views import async_view_with_loaders, edit_book, view_with_loaders

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("book/<int:pk>/edit/", edit_book, name="edit-book"),
    path("view1", view_with_loaders, name="view1"),
    path("async_view1", async_view_with_loaders, name="async_view1"),
]
