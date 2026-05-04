import socket
import os
import shutil
import tempfile
import winreg
import sys
import math
import struct
import wave
import json
import locale
import subprocess
import wx.adv
import base64
import re
from pathlib import Path

from config import APP_NAME, get_base_path
from locales import TRANSLATIONS

# --- SETTINGS MANAGER ---
class SettingsManager:
	def __init__(self):
		self.filepath = os.path.join(str(Path.home()), f".{APP_NAME.lower()}_settings.json")
		self.defaults = {
			"language": "auto",
			"run_in_background": True,
			"autostart": False,
			"play_tick_sound": True,
			"play_done_sound": True,
			"sound_mode": "legacy",
			"save_path": ""
		}
		self.settings = self.load()

	def load(self):
		if os.path.exists(self.filepath):
			try:
				with open(self.filepath, "r", encoding="utf-8") as f:
					data = json.load(f)
					merged = self.defaults.copy()
					merged.update(data)
					return merged
			except Exception: pass
		return self.defaults.copy()

	def save(self):
		try:
			with open(self.filepath, "w", encoding="utf-8") as f:
				json.dump(self.settings, f, indent=4)
		except Exception: pass

	def get(self, key):
		return self.settings.get(key, self.defaults.get(key))

	def set(self, key, value):
		self.settings[key] = value

# --- TRANSLATOR ---
class Translator:
	def __init__(self, settings_manager):
		self.settings = settings_manager
		self.current_lang = self._determine_language()

	def _determine_language(self):
		setting = self.settings.get("language")
		if setting in ["en", "de"]:
			return setting
		try:
			sys_lang = locale.getdefaultlocale()[0]
			if sys_lang and sys_lang.startswith("de"):
				return "de"
		except Exception: pass
		return "en"

	def update_lang(self):
		self.current_lang = self._determine_language()

	def get(self, key, *args):
		text = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"]).get(key, key)
		if args:
			try: text = text.format(*args)
			except Exception: pass
		return text

# --- AUTOSTART MANAGER ---
class AutostartManager:
	@staticmethod
	def set_autostart(enable=True):
		key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
		try:
			if enable:
				if getattr(sys, 'frozen', False):
					exe_path = f'"{sys.executable}" --minimized'
				else:
					main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
					exe_path = f'"{sys.executable}" "{main_script}" --minimized'
				winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
			else:
				try: winreg.DeleteValue(key, APP_NAME)
				except FileNotFoundError: pass
		except Exception: pass
		finally: winreg.CloseKey(key)

	@staticmethod
	def is_autostart_enabled():
		key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
		try:
			winreg.QueryValueEx(key, APP_NAME)
			return True
		except FileNotFoundError: return False
		finally: winreg.CloseKey(key)

# --- NETWORK UTILS ---
class NetworkUtils:
	@staticmethod
	def get_local_ip():
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try:
			s.connect(('10.255.255.255', 1))
			IP = s.getsockname()[0]
		except Exception: IP = '127.0.0.1'
		finally: s.close()
		return IP

	@staticmethod
	def get_downloads_folder():
		return str(Path.home() / "Downloads")

class ZipUtils:
	@staticmethod
	def compress_folder(folder_path):
		folder_name = os.path.basename(folder_path)
		temp_dir = tempfile.gettempdir()
		base_name = os.path.join(temp_dir, folder_name)
		zip_path = shutil.make_archive(base_name, 'zip', folder_path)
		return zip_path

	@staticmethod
	def extract_zip(zip_path, target_dir):
		try:
			folder_name = os.path.splitext(os.path.basename(zip_path))[0]
			extract_path = os.path.join(target_dir, folder_name)
			counter = 1
			original_path = extract_path
			while os.path.exists(extract_path):
				extract_path = f"{original_path}_{counter}"
				counter += 1
			os.makedirs(extract_path, exist_ok=True)
			shutil.unpack_archive(zip_path, extract_path)
			return extract_path
		except Exception: return None

# --- AUDIO UTILS ---
class AudioUtils:
	@staticmethod
	def load_modern_sound(sound_type):
		sounds_file = os.path.join(get_base_path(), "sounds.dat")
		if not os.path.exists(sounds_file): return None
		try:
			with open(sounds_file, "r", encoding="utf-8") as f:
				content = f.read()
			match = re.search(f"{sound_type}\\{{(.*?)\\}}", content, re.DOTALL)
			if match:
				b64_data = match.group(1).replace('\n', '').replace('\r', '').strip()
				wav_data = base64.b64decode(b64_data)
				
				temp_path = os.path.join(tempfile.gettempdir(), f"landrop_modern_{sound_type}.wav")
				with open(temp_path, "wb") as wf:
					wf.write(wav_data)
				
				snd = wx.adv.Sound(temp_path)
				if snd.IsOk():
					return snd
		except Exception: pass
		return None

	@staticmethod
	def _generate_sound(filename, frequencies_and_durations, volume):
		sample_rate = 44100
		data = bytearray()
		for freq, duration in frequencies_and_durations:
			num_samples = int(sample_rate * duration)
			for i in range(num_samples):
				val = math.sin(2 * math.pi * freq * i / sample_rate)
				envelope = math.exp(-i * 10 / sample_rate)
				sample = int(volume * val * envelope)
				data.extend(struct.pack("<h", sample))
		
		temp_path = os.path.join(tempfile.gettempdir(), f"landrop_{filename}.wav")
		with wave.open(temp_path, "wb") as wf:
			wf.setnchannels(1)
			wf.setsampwidth(2)
			wf.setframerate(sample_rate)
			wf.writeframes(bytes(data))
		return wx.adv.Sound(temp_path)

	@classmethod
	def get_tick_sound(cls):
		return cls._generate_sound("tick", [(300, 0.03)], volume=8000)

	@classmethod
	def get_done_sound(cls):
		return cls._generate_sound("done", [(800, 0.1), (1200, 0.2)], volume=20000)

# --- TAILSCALE UTILS ---
class TailscaleUtils:
	@staticmethod
	def get_online_peers():
		peers = []
		try:
			startupinfo = None
			if os.name == 'nt':
				startupinfo = subprocess.STARTUPINFO()
				startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

			result = subprocess.run(["tailscale", "status", "--json"], 
									capture_output=True, text=True, 
									startupinfo=startupinfo, timeout=3)
			
			if result.returncode == 0:
				data = json.loads(result.stdout)
				self_ips = []
				if "Self" in data and "TailscaleIPs" in data["Self"]:
					self_ips = data["Self"]["TailscaleIPs"]

				if "Peer" in data:
					for pubkey, peer in data["Peer"].items():
						if peer.get("Online") and "TailscaleIPs" in peer and len(peer["TailscaleIPs"]) > 0:
							ip = peer["TailscaleIPs"][0]
							if ip not in self_ips:
								host = peer.get("HostName", "Unknown")
								peers.append((ip, host))
		except Exception: pass
		return peers