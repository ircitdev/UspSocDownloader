"""Main application module."""
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    \"\"\"Main function.\"\"\"
    print(f"Hello from {os.getenv('APP_NAME', 'UspSocDownloader')}!")

if __name__ == "__main__":
    main()
