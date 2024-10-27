from dotenv import load_dotenv
import os


load_dotenv()
DATABASE_URL_ASYNC = os.environ.get("DATABASE_URL_ASYNC")
DATABASE_URL_ASYNC_ALEMBIC = os.environ.get("DATABASE_URL_ASYNC_ALEMBIC")
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES")
REGISTATION_LINK_CIPHER_KEY = os.environ.get("REGISTATION_LINK_CIPHER_KEY")