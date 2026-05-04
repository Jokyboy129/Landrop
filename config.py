import os
import sys

# --- APP CONFIGURATION ---
BROADCAST_PORT = 50000
TRANSFER_PORT = 50001
WEB_PORT = 8080
INSTANCE_PORT = 50002	# Port für Single-Instance-Check
BUFFER_SIZE = 1048576	# 1 MB für maximale Netzwerk-Performance (vorher 4096)
SEPARATOR = "<SEPARATOR>"
APP_NAME = "Landrop"

def get_base_path():
	""" Returns the correct path whether running as .py or compiled .exe """
	if getattr(sys, 'frozen', False):
		return sys._MEIPASS
	return os.path.dirname(os.path.abspath(__file__))

HTML_TEMPLATE_PATH = os.path.join(get_base_path(), "interface.html")