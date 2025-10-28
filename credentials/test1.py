from dotenv import load_dotenv
import os

load_dotenv()

google_cloud_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
print(google_cloud_credentials)