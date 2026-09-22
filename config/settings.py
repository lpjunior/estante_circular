import os
from pathlib import Path

from dotenv import load_dotenv

# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.getenv(
    "DJANGO_ENV",
    "development",
)

# ============================================================
# AMBIENTE
# ============================================================

# O .env serve somente como fallback para desenvolvimento local.
#
# load_dotenv() NÃO sobrescreve variáveis que já existem no
# sistema operacional quando override=False.
#
# Portanto:
# Local:
#   variáveis ausentes no SO -> carregadas do .env
#
# Vercel:
#   variáveis já fornecidas pelo Vercel -> preservadas
#
# Mesmo que um .env aparecesse acidentalmente no ambiente,
# ele não substituiria valores já definidos pelo Vercel.

if ENVIRONMENT == "development":
    load_dotenv(
        BASE_DIR / ".env",
        override=False,
    )


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================


def get_env(name, default=None, required=False):
    """
    Obtém uma variável de ambiente.

    Se required=True e a variável não existir ou estiver vazia,
    interrompe a inicialização com uma mensagem clara.
    """

    value = os.getenv(name, default)

    if required and (value is None or value == ""):
        raise RuntimeError(
            f"A variável de ambiente obrigatória '{name}' não foi definida."
        )

    return value


def get_bool_env(name, default=False):
    """
    Converte variável de ambiente textual para booleano.
    """

    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_list_env(name, default=""):
    """
    Converte uma variável separada por vírgulas em lista.
    """

    value = os.getenv(name, default)

    return [item.strip() for item in value.split(",") if item.strip()]


# ============================================================
# SEGURANÇA
# ============================================================

SECRET_KEY = get_env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-development-only",
)


DEBUG = get_bool_env(
    "DJANGO_DEBUG",
    default=False,
)


ALLOWED_HOSTS = get_list_env(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
)


# ============================================================
# APPLICATION DEFINITION
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cloudinary",
    "core",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": get_env(
            "POSTGRES_DB",
            required=True,
        ),
        "USER": get_env(
            "POSTGRES_USER",
            required=True,
        ),
        "PASSWORD": get_env(
            "POSTGRES_PASSWORD",
            required=True,
        ),
        "HOST": get_env(
            "POSTGRES_HOST",
            required=True,
        ),
        "PORT": get_env(
            "POSTGRES_PORT",
            default="5432",
        ),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "sslmode": get_env(
                "POSTGRES_SSLMODE",
                default="require",
            ),
        },
    }
}


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.MinimumLengthValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.CommonPasswordValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.NumericPasswordValidator"),
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "pt-BR"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "/static/"


# Diretório em que collectstatic reunirá os arquivos.
STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# EMAIL
# ============================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# ============================================================
# AUTENTICAÇÃO
# ============================================================

LOGIN_URL = 'core:login'
LOGIN_REDIRECT_URL = 'core:index'
LOGOUT_REDIRECT_URL = 'core:index'


# ============================================================
# IMAGE STORAGE
# ============================================================

CLOUDINARY_URL= os.getenv("CLOUDINARY_URL")