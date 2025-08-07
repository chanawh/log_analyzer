import logging
import sys
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("log_analysis.log"),
        logging.StreamHandler()
    ]
)

def launch_gui():
    """Launch the Tkinter GUI."""
    try:
        from gui.gui import launch_gui as _launch_gui
        _launch_gui()
    except ImportError as e:
        print(f"❌ Error importing GUI: {e}")
        print("GUI interface requires Tkinter. Please install python3-tk or try the web interface:")
        print("python main.py --interface web")
        sys.exit(1)

def launch_web_frontend(port=8080, debug=False):
    """Launch the web-based frontend."""
    try:
        from frontend.app import app
        print(f"🚀 Starting Log Analyzer Web Frontend on http://localhost:{port}")
        print("📊 Access the dashboard to demo all features")
        print("🔧 Available modules: SSH Browser, Log Analysis, SQL Database")
        app.run(debug=debug, host='0.0.0.0', port=port)
    except ImportError as e:
        print(f"❌ Error importing web frontend: {e}")
        print("Please ensure Flask and other dependencies are installed.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting web frontend: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Log Analyzer - Production-Ready Log Analysis Tool')
    parser.add_argument('--interface', '-i', choices=['gui', 'web'], default='web',
                        help='Interface to launch (default: web)')
    parser.add_argument('--port', '-p', type=int, default=8080,
                        help='Port for web interface (default: 8080)')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug mode for web interface')
    
    args = parser.parse_args()
    
    if args.interface == 'web':
        launch_web_frontend(port=args.port, debug=args.debug)
    else:
        print("🚀 Starting Log Analyzer GUI")
        print("💡 For web interface, use: python main.py --interface web")
        launch_gui()

if __name__ == "__main__":
    main()