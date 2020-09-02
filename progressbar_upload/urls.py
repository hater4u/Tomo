from django.conf.urls import url
from progressbar_upload.views import upload_progress

urlpatterns = [
    url(r'^upload_progress$', upload_progress, name="upload_progress"),
]
