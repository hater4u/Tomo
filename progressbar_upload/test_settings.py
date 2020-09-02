SITE_ID = 1

FILE_UPLOAD_MAX_MEMORY_SIZE = 1

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'progressbar_upload',
    }
}

FILE_UPLOAD_HANDLERS = (
    "progressbar_upload.upload_handler.ProgressBarUploadHandler",
)

SECRET_KEY = 'very_secret_key'
