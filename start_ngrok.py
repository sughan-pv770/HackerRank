import os
import sys
from pyngrok import ngrok, conf
from app import create_app

def start_with_ngrok():
    # Stop pyngrok from trying to download and use the local ngrok.exe
    ngrok_path = os.path.join(os.path.dirname(__file__), "ngrok.exe")
    
    if not os.path.exists(ngrok_path):
        print("\n" + "!" * 60)
        print("🛑 NGROK.EXE NOT FOUND! 🛑")
        print("Your college network (nmc@mec.edu.in) is blocking automatic downloads.")
        print()
        print("PLEASE FOLLOW THESE STEPS:")
        print("1. Open your web browser and go to: https://download.ngrok.com/windows")
        print("2. Download the ZIP file.")
        print("3. Extract 'ngrok.exe' and copy it DIRECTLY into: d:\\test\\terv-test\\")
        print("4. Run this script again.")
        print("!" * 60 + "\n")
        return

    # Configure pyngrok to use the manually downloaded binary
    config = conf.PyngrokConfig(ngrok_path=ngrok_path, region='us')
    
    try:
        # Open a tunnel to port 5000
        public_url = ngrok.connect(5000, pyngrok_config=config)
        print("\n" + "=" * 60)
        print("🚀 NGROK TUNNEL CREATED SUCCESSFULLY! 🚀")
        print(f"🔗 YOUR PUBLIC LINK: {public_url.public_url}")
        print("=" * 60 + "\n")
        
        # Start the Flask app
        app = create_app()
        app.run(port=5000, host="127.0.0.1", use_reloader=False)
        
    except Exception as e:
        print(f"\n❌ Ngrok connection failed: {e}")
        print("You might need an authtoken for Ngrok. Visit https://dashboard.ngrok.com/login")
        print("Run in terminal: ngrok config add-authtoken <your-token>")

if __name__ == "__main__":
    start_with_ngrok()
