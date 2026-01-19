from dotenv import load_dotenv

from api.routes import create_app

load_dotenv()

app = create_app()
