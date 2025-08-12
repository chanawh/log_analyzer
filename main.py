import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("log_analysis.log"), logging.StreamHandler()],
)

from gui.gui import launch_gui

if __name__ == "__main__":
    launch_gui()
