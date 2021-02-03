"""ocelot URL Configuration

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
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from leaderboard.views import competition
from leaderboard.views import frontpage
from leaderboard.views import signin
from leaderboard.views import signout
from leaderboard.views import signup
from leaderboard.views import submit
from leaderboard.views import teampage
from leaderboard.views import updates
from leaderboard.views import welcome
from ocelot.settings import DEBUG
from ocelot.settings import STATIC_ROOT
from ocelot.settings import STATIC_URL

# pylint: disable-msg=invalid-name
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', frontpage, name='frontpage-view'),
    path('competition/<competition_id>', competition, name='competition-view'),
    path('sign-in', signin, name='signin-view'),
    path('sign-out', signout, name='signout-view'),
    path('signup', signup, name='signup-view'),
    path('submit', submit, name='submit-view'),
    path('teampage', teampage, name='teampage-view'),
    path('updates', updates, name='updates-view'),
    path('welcome', welcome, name='welcome-view'),
]

if DEBUG:
    urlpatterns += static(STATIC_URL, document_root=STATIC_ROOT)
