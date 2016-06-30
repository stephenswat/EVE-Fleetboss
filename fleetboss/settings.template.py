from django.contrib import messages
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'social.apps.django_app.default',
    'fleetboss',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',
    'social.pipeline.user.get_username',
    'social.pipeline.user.create_user',
    'fleetboss.pipeline.single_association',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details',
)

ROOT_URLCONF = 'fleetboss.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social.apps.django_app.context_processors.backends',
                'social.apps.django_app.context_processors.login_redirect',
            ],
        },
    },
]

MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

AUTH_USER_MODEL = 'fleetboss.Character'
AUTHENTICATION_BACKENDS = ('social.backends.eveonline.EVEOnlineOAuth2',)

WSGI_APPLICATION = 'fleetboss.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

LANGUAGE_CODE = 'en-uk'
TIME_ZONE = 'UTC'
DATE_FORMAT = 'F j, H:i'
USE_I18N = False
USE_L10N = False
USE_TZ = False

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/login/eveonline/'

STATIC_URL = '/static/'

SOCIAL_AUTH_EVEONLINE_SCOPE = ['fleetRead']
SOCIAL_AUTH_EVEONLINE_KEY = ''
SOCIAL_AUTH_EVEONLINE_SECRET = ''
SOCIAL_AUTH_REDIRECT_IS_HTTPS = False

SECRET_KEY = ''
DEBUG = False
