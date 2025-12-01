from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Azure AD
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    TENANT_ID = os.getenv("TENANT_ID")

    # OAuth scope and redirect path
    SCOPE = ["User.Read"]
    REDIRECT_PATH = "/getAToken"

    # DOMO
    DOMO_API_HOST = os.getenv("DOMO_API_HOST", "https://api.domo.com")
    DOMO_EMBED_HOST = os.getenv("DOMO_EMBED_HOST", "https://public.domo.com")
    DOMO_CLIENT_ID = os.getenv("DOMO_CLIENT_ID")
    DOMO_CLIENT_SECRET = os.getenv("DOMO_CLIENT_SECRET")
    CARD_DASHBOARD = os.getenv("C_D", "cards")
