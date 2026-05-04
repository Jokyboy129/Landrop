import wx
import wx.adv
import socket
import threading
import json
import os
import time
import email.parser
import shutil
import sys
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import *
from utils import AutostartManager, NetworkUtils, ZipUtils, AudioUtils, SettingsManager, Translator, TailscaleUtils

# --- FIX FOR --noconsole MODE ---
if sys.stdout is None or sys.stderr is None:
	class NullWriter:
		def write(self, text): pass
		def flush(self): pass
	sys.stdout = NullWriter()
	sys.stderr = NullWriter()

# --- SETTINGS DIALOG ---
class SettingsDialog(wx.Dialog):
	def __init__(self, parent, settings_mgr, tr):
		super().__init__(parent, title=tr.get("set_title"), size=(450, 420))
		self.settings = settings_mgr
		self.tr = tr
		
		try: 
			self.test_tick = AudioUtils.get_tick_sound()
			self.test_done = AudioUtils.get_done_sound()
		except Exception: 
			self.test_tick = None
			self.test_done = None

		self.init_ui()
		self.CentreOnParent()

	def init_ui(self):
		panel = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)

		# Language
		hbox_lang = wx.BoxSizer(wx.HORIZONTAL)
		hbox_lang.Add(wx.StaticText(panel, label=self.tr.get("set_language")), 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)
		self.cb_lang = wx.ComboBox(panel, choices=[self.tr.get("set_lang_auto"), "English", "Deutsch"], style=wx.CB_READONLY)
		curr_lang = self.settings.get("language")
		if curr_lang == "en": self.cb_lang.SetSelection(1)
		elif curr_lang == "de": self.cb_lang.SetSelection(2)
		else: self.cb_lang.SetSelection(0)
		hbox_lang.Add(self.cb_lang, 1, wx.EXPAND)
		vbox.Add(hbox_lang, 0, wx.EXPAND | wx.ALL, 15)

		# Save Path
		hbox_path = wx.BoxSizer(wx.HORIZONTAL)
		hbox_path.Add(wx.StaticText(panel, label=self.tr.get("set_save_path")), 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)
		current_path = self.settings.get("save_path")
		if not current_path: current_path = NetworkUtils.get_downloads_folder()
		self.dir_save = wx.DirPickerCtrl(panel, path=current_path, message=self.tr.get("set_save_path"))
		hbox_path.Add(self.dir_save, 1, wx.EXPAND)
		vbox.Add(hbox_path, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

		# Checkboxes
		self.chk_bg = wx.CheckBox(panel, label=self.tr.get("set_run_bg"))
		self.chk_bg.SetValue(self.settings.get("run_in_background"))
		vbox.Add(self.chk_bg, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

		self.chk_auto = wx.CheckBox(panel, label=self.tr.get("set_autostart"))
		self.chk_auto.SetValue(self.settings.get("autostart"))
		vbox.Add(self.chk_auto, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
		
		vbox.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

		# Sound Options
		hbox_smode = wx.BoxSizer(wx.HORIZONTAL)
		hbox_smode.Add(wx.StaticText(panel, label=self.tr.get("set_sound_mode")), 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)
		self.cb_smode = wx.ComboBox(panel, choices=[self.tr.get("set_sound_legacy"), self.tr.get("set_sound_modern")], style=wx.CB_READONLY)
		if self.settings.get("sound_mode") == "modern": self.cb_smode.SetSelection(1)
		else: self.cb_smode.SetSelection(0)
		hbox_smode.Add(self.cb_smode, 1, wx.EXPAND)
		vbox.Add(hbox_smode, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

		self.chk_snd_tick = wx.CheckBox(panel, label=self.tr.get("set_sound_tick"))
		self.chk_snd_tick.SetValue(self.settings.get("play_tick_sound"))
		vbox.Add(self.chk_snd_tick, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

		self.chk_snd_done = wx.CheckBox(panel, label=self.tr.get("set_sound_done"))
		self.chk_snd_done.SetValue(self.settings.get("play_done_sound"))
		vbox.Add(self.chk_snd_done, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

		hbox_snd = wx.BoxSizer(wx.HORIZONTAL)
		btn_tick = wx.Button(panel, label=self.tr.get("set_test_tick"))
		btn_done = wx.Button(panel, label=self.tr.get("set_test_done"))
		btn_tick.Bind(wx.EVT_BUTTON, self.on_test_tick)
		btn_done.Bind(wx.EVT_BUTTON, self.on_test_done)
		hbox_snd.Add(btn_tick, 0, wx.RIGHT, 10)
		hbox_snd.Add(btn_done, 0)
		vbox.Add(hbox_snd, 0, wx.LEFT | wx.BOTTOM, 15)

		vbox.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 10)

		# Action Buttons
		hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
		btn_save = wx.Button(panel, label=self.tr.get("set_save"))
		btn_cancel = wx.Button(panel, label=self.tr.get("set_cancel"))
		btn_save.Bind(wx.EVT_BUTTON, self.on_save)
		btn_cancel.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CANCEL))
		hbox_btns.Add(btn_cancel, 0, wx.RIGHT, 10)
		hbox_btns.Add(btn_save, 0)
		
		vbox.Add(hbox_btns, 0, wx.ALIGN_RIGHT | wx.ALL, 15)
		panel.SetSizer(vbox)

	def on_test_tick(self, event):
		mode = "modern" if self.cb_smode.GetSelection() == 1 else "legacy"
		if mode == "modern":
			snd = AudioUtils.load_modern_sound("tick")
			if snd: 
				wx.CallAfter(snd.Play, wx.adv.SOUND_ASYNC)
				return
		if self.test_tick: wx.CallAfter(self.test_tick.Play, wx.adv.SOUND_ASYNC)

	def on_test_done(self, event):
		mode = "modern" if self.cb_smode.GetSelection() == 1 else "legacy"
		if mode == "modern":
			snd = AudioUtils.load_modern_sound("finish")
			if snd: 
				wx.CallAfter(snd.Play, wx.adv.SOUND_ASYNC)
				return
		if self.test_done: wx.CallAfter(self.test_done.Play, wx.adv.SOUND_ASYNC)

	def on_save(self, event):
		sel = self.cb_lang.GetSelection()
		if sel == 1: self.settings.set("language", "en")
		elif sel == 2: self.settings.set("language", "de")
		else: self.settings.set("language", "auto")

		self.settings.set("save_path", self.dir_save.GetPath())
		self.settings.set("sound_mode", "modern" if self.cb_smode.GetSelection() == 1 else "legacy")
		self.settings.set("run_in_background", self.chk_bg.GetValue())
		
		auto_val = self.chk_auto.GetValue()
		self.settings.set("autostart", auto_val)
		AutostartManager.set_autostart(auto_val)

		self.settings.set("play_tick_sound", self.chk_snd_tick.GetValue())
		self.settings.set("play_done_sound", self.chk_snd_done.GetValue())
		
		self.settings.save()
		self.EndModal(wx.ID_OK)


# --- TASKBAR ICON ---
class LandropTaskBarIcon(wx.adv.TaskBarIcon):
	def __init__(self, frame):
		super().__init__()
		self.frame = frame
		icon = wx.ArtProvider.GetIcon(wx.ART_GO_DOWN, wx.ART_OTHER, (16, 16))
		self.SetIcon(icon, APP_NAME)
		self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

	def CreatePopupMenu(self):
		menu = wx.Menu()
		item_show = menu.Append(wx.ID_ANY, self.frame.tr.get("tray_show"))
		menu.AppendSeparator()
		item_exit = menu.Append(wx.ID_ANY, self.frame.tr.get("tray_quit"))
		self.Bind(wx.EVT_MENU, self.on_show_app, item_show)
		self.Bind(wx.EVT_MENU, self.on_exit_app, item_exit)
		return menu

	def on_left_down(self, event):
		self.frame.show_from_background()

	def on_show_app(self, event):
		self.frame.show_from_background()

	def on_exit_app(self, event):
		self.frame.real_quit()

# --- WEB SERVER ---
class LandropHTTPHandler(BaseHTTPRequestHandler):
	def log_message(self, format, *args): pass

	def do_GET(self):
		if self.path.startswith("/download/"):
			self.handle_file_download()
			return

		self.send_response(200)
		self.send_header("Content-type", "text/html; charset=utf-8")
		self.end_headers()
		
		hostname = socket.gethostname()
		hosted_file = self.server.app_window.hosted_file_path
		tr = self.server.app_window.tr
		download_section = ""
		
		if hosted_file and os.path.exists(hosted_file):
			fname = os.path.basename(hosted_file)
			display_text = fname
			if fname.endswith(".zip") and self.server.app_window.is_folder_mode:
				display_text = f"📦 {fname}"
			else:
				display_text = f"📄 {fname}"

			download_section = f"""
			<div class="card download-card">
				<h3>📥 {tr.get('web_recv_pc')}</h3>
				<p>{tr.get('web_pc_sending')}<br><strong>{display_text}</strong></p>
				<a href="/download/{fname}" class="btn-download">{tr.get('web_btn_dl')}</a>
			</div>
			"""
		else:
			download_section = f"""
			<div class="card" style="opacity: 0.6;">
				<h3>📥 {tr.get('web_recv_pc')}</h3>
				<p>{tr.get('web_waiting')}</p>
			</div>
			"""

		try:
			with open(HTML_TEMPLATE_PATH, "r", encoding="utf-8") as f:
				html = f.read()
		except FileNotFoundError:
			html = "<h2>Error: interface.html not found!</h2>"

		html = html.replace("{{T_WEB_TITLE}}", tr.get("web_title"))
		html = html.replace("{{T_WEB_CONNECTED}}", tr.get("web_connected"))
		html = html.replace("{{T_WEB_SEND_PC}}", tr.get("web_send_pc"))
		html = html.replace("{{T_WEB_BTN_SEND}}", tr.get("web_btn_send"))
		html = html.replace("{{T_WEB_UPLOADING}}", tr.get("web_uploading"))
		html = html.replace("{{T_WEB_SUCCESS}}", tr.get("web_success"))
		
		html = html.replace("[HOSTNAME]", hostname)
		html = html.replace("[DOWNLOAD_SECTION]", download_section)

		self.wfile.write(html.encode('utf-8'))

	def handle_file_download(self):
		hosted_file = self.server.app_window.hosted_file_path
		if not hosted_file or not os.path.exists(hosted_file):
			self.send_error(404, "File not found")
			return
		filename = os.path.basename(hosted_file)
		try: f = open(hosted_file, 'rb')
		except OSError:
			self.send_error(404, "File not found")
			return
		self.send_response(200)
		self.send_header("Content-Type", "application/octet-stream")
		self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
		fs = os.fstat(f.fileno())
		self.send_header("Content-Length", str(fs.st_size))
		self.end_headers()
		shutil.copyfileobj(f, self.wfile)
		f.close()
		
		tr = self.server.app_window.tr
		wx.CallAfter(self.server.app_window.status_text.SetLabel, tr.get("msg_phone_dl", filename))
		wx.CallAfter(self.server.app_window.play_done_sound)

	def do_POST(self):
		if self.path == '/upload':
			try:
				content_length = int(self.headers.get('Content-Length', 0))
				content_type = self.headers.get('Content-Type', '')

				if 'boundary=' not in content_type:
					self.send_error(400, "Invalid content type")
					return

				boundary = content_type.split("boundary=")[1].encode()
				boundary_line = b"--" + boundary

				saved_files = []
				bytes_remaining = content_length

				def read_until(separator):
					nonlocal bytes_remaining
					data = bytearray()
					while bytes_remaining > 0:
						line = self.rfile.readline()
						bytes_remaining -= len(line)
						data.extend(line)
						if data.endswith(separator):
							return bytes(data[:-len(separator)])
					return bytes(data)

				read_until(boundary_line + b"\r\n")

				while bytes_remaining > 0:
					headers_data = read_until(b"\r\n\r\n")
					if not headers_data:
						break

					headers_str = headers_data.decode('utf-8', 'ignore')
					filename = None
					match = re.search(r'filename="([^"]+)"', headers_str)
					if match:
						filename = match.group(1)

					if filename:
						save_path = os.path.join(self.server.app_window.get_save_path(), os.path.basename(filename))
						target_boundary = b"\r\n" + boundary_line
						buffer = bytearray()
						
						with open(save_path, 'wb') as f:
							while bytes_remaining > 0:
								chunk = self.rfile.read(min(BUFFER_SIZE, bytes_remaining))
								if not chunk: break
								bytes_remaining -= len(chunk)
								buffer.extend(chunk)
								
								idx = buffer.find(target_boundary)
								if idx != -1:
									f.write(buffer[:idx])
									buffer = buffer[idx + len(target_boundary):]
									if buffer.startswith(b"--"):
										bytes_remaining = 0
									else:
										if buffer.startswith(b"\r\n"):
											buffer = buffer[2:]
									break
								else:
									safe_len = len(buffer) - len(target_boundary)
									if safe_len > 0:
										f.write(buffer[:safe_len])
										buffer = buffer[safe_len:]
						
						saved_files.append(filename)
					else:
						target_boundary = b"\r\n" + boundary_line
						buffer = bytearray()
						while bytes_remaining > 0:
							chunk = self.rfile.read(min(BUFFER_SIZE, bytes_remaining))
							bytes_remaining -= len(chunk)
							buffer.extend(chunk)
							idx = buffer.find(target_boundary)
							if idx != -1:
								buffer = buffer[idx + len(target_boundary):]
								if buffer.startswith(b"--"): bytes_remaining = 0
								break
							buffer = buffer[-len(target_boundary):]

				if saved_files:
					tr = self.server.app_window.tr
					msg_text = tr.get("msg_received", ', '.join(saved_files))
					wx.CallAfter(self.server.app_window.status_text.SetLabel, msg_text)
					wx.CallAfter(self.server.app_window.play_done_sound)
					
					if not self.server.app_window.settings.get("play_done_sound"):
						wx.CallAfter(self.server.app_window.show_notification, APP_NAME, msg_text)

				self.send_response(200)
				self.send_header('Content-Type', 'application/json')
				self.end_headers()
				self.wfile.write(b'{"status": "ok"}')
			except Exception as e:
				self.send_error(500, f"Error: {e}")

# --- MAIN APP ---
class FileTransferApp(wx.Frame):
	def __init__(self, instance_sock):
		self.settings = SettingsManager()
		self.tr = Translator(self.settings)
		self.instance_sock = instance_sock
		
		self.active_tick_sound = None
		self.active_done_sound = None
		
		if AutostartManager.is_autostart_enabled() != self.settings.get("autostart"):
			AutostartManager.set_autostart(self.settings.get("autostart"))

		super().__init__(None, title=self.tr.get("app_title"), size=(550, 650))
		
		self.my_ip = NetworkUtils.get_local_ip()
		self.hostname = socket.gethostname()
		self.peers = {}
		self.hosted_file_path = None
		self.is_folder_mode = False
		self.is_closing = False
		
		self.tb_icon = LandropTaskBarIcon(self)
		self.Bind(wx.EVT_CLOSE, self.on_close_attempt)
		
		try: 
			self.tick_sound = AudioUtils.get_tick_sound()
			self.done_sound = AudioUtils.get_done_sound()
		except Exception: 
			self.tick_sound = None
			self.done_sound = None
		
		self.init_ui()
		self.running = True
		
		threading.Thread(target=self.listen_for_instance, daemon=True).start()
		threading.Thread(target=self.listen_for_broadcasts, daemon=True).start()
		threading.Thread(target=self.start_file_server, daemon=True).start()
		threading.Thread(target=self.start_web_server, daemon=True).start()

		self.discovery_timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.on_discovery_timer, self.discovery_timer)
		self.discovery_timer.Start(5000)
		self.perform_discovery()

	def get_save_path(self):
		path = self.settings.get("save_path")
		if not path or not os.path.exists(path):
			return NetworkUtils.get_downloads_folder()
		return path

	def start_modern_tick_loop(self):
		if self.settings.get("play_tick_sound") and self.settings.get("sound_mode") == "modern":
			self.active_tick_sound = AudioUtils.load_modern_sound("tick")
			if self.active_tick_sound:
				self.active_tick_sound.Play(wx.adv.SOUND_ASYNC | wx.adv.SOUND_LOOP)

	def play_legacy_tick(self):
		if self.settings.get("play_tick_sound") and self.settings.get("sound_mode") == "legacy":
			if getattr(self, "tick_sound", None):
				# WICHTIG: Kein Loop beim Legacy-Sound, nur ein einzelner Ping!
				self.tick_sound.Play(wx.adv.SOUND_ASYNC)

	def stop_all_sounds(self):
		try: wx.adv.Sound.Stop()
		except: pass

	def play_done_sound(self):
		self.stop_all_sounds() # Stellt sicher, dass ein laufender Loop beendet wird
		
		if self.settings.get("play_done_sound"):
			mode = self.settings.get("sound_mode")
			if mode == "modern":
				self.active_done_sound = AudioUtils.load_modern_sound("finish")
				if self.active_done_sound:
					self.active_done_sound.Play(wx.adv.SOUND_ASYNC)
					return
			if getattr(self, "done_sound", None):
				self.active_done_sound = self.done_sound
				self.active_done_sound.Play(wx.adv.SOUND_ASYNC)

	def init_ui(self):
		self.panel = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)
		font_bold = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
		
		self.lbl_info = wx.StaticText(self.panel, label=self.tr.get("device_info", self.hostname, self.my_ip))
		self.lbl_info.SetFont(font_bold)
		vbox.Add(self.lbl_info, 0, wx.ALL | wx.CENTER, 10)

		self.link_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, self.tr.get("smartphone_link"))
		self.lbl_link_hint = wx.StaticText(self.panel, label=self.tr.get("open_link"))
		link_txt = wx.TextCtrl(self.panel, value=f"http://{self.my_ip}:{WEB_PORT}", style=wx.TE_READONLY|wx.TE_CENTER)
		self.link_box.Add(self.lbl_link_hint, 0, wx.CENTER|wx.BOTTOM, 5)
		self.link_box.Add(link_txt, 0, wx.EXPAND | wx.ALL, 5)
		vbox.Add(self.link_box, 0, wx.EXPAND | wx.ALL, 10)

		self.lbl_pcs = wx.StaticText(self.panel, label=self.tr.get("found_pcs"))
		self.lbl_pcs.SetFont(font_bold)
		vbox.Add(self.lbl_pcs, 0, wx.LEFT, 15)
		hbox_dev = wx.BoxSizer(wx.HORIZONTAL)
		self.device_combo = wx.ComboBox(self.panel, style=wx.CB_READONLY)
		hbox_dev.Add(self.device_combo, 1, wx.EXPAND | wx.RIGHT, 5)
		self.btn_refresh = wx.Button(self.panel, label=self.tr.get("btn_search"), size=(80, -1))
		self.btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
		hbox_dev.Add(self.btn_refresh, 0)
		vbox.Add(hbox_dev, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

		vbox.Add(wx.StaticLine(self.panel), 0, wx.EXPAND | wx.ALL, 10)
		
		self.lbl_what = wx.StaticText(self.panel, label=self.tr.get("what_to_send"))
		self.lbl_what.SetFont(font_bold)
		vbox.Add(self.lbl_what, 0, wx.LEFT, 15)
		self.mode_box = wx.RadioBox(self.panel, choices=[self.tr.get("mode_file"), self.tr.get("mode_folder")], majorDimension=2, style=wx.RA_SPECIFY_COLS)
		self.mode_box.Bind(wx.EVT_RADIOBOX, self.on_mode_change)
		vbox.Add(self.mode_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

		self.picker_sizer = wx.BoxSizer(wx.VERTICAL)
		self.file_picker = wx.FilePickerCtrl(self.panel, message=self.tr.get("file_picker"))
		self.dir_picker = wx.DirPickerCtrl(self.panel, message=self.tr.get("dir_picker"))
		self.dir_picker.Hide()
		self.picker_sizer.Add(self.file_picker, 1, wx.EXPAND)
		self.picker_sizer.Add(self.dir_picker, 1, wx.EXPAND)
		vbox.Add(self.picker_sizer, 0, wx.EXPAND | wx.ALL, 15)

		hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
		self.send_pc_btn = wx.Button(self.panel, label=self.tr.get("btn_send_pc"), size=(-1, 40))
		self.send_pc_btn.Bind(wx.EVT_BUTTON, self.on_send_to_pc)
		self.host_phone_btn = wx.Button(self.panel, label=self.tr.get("btn_host_phone"), size=(-1, 40))
		self.host_phone_btn.Bind(wx.EVT_BUTTON, self.on_host_for_phone)
		hbox_btns.Add(self.send_pc_btn, 1, wx.RIGHT, 5)
		hbox_btns.Add(self.host_phone_btn, 1, wx.LEFT, 5)
		vbox.Add(hbox_btns, 0, wx.EXPAND | wx.ALL, 15)

		self.gauge = wx.Gauge(self.panel, range=100, size=(-1, 15))
		vbox.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

		self.status_text = wx.StaticText(self.panel, label=self.tr.get("status_ready"), style=wx.ALIGN_CENTER)
		vbox.Add(self.status_text, 0, wx.ALL | wx.EXPAND, 15)

		vbox.Add(wx.StaticLine(self.panel), 0, wx.EXPAND | wx.ALL, 10)
		
		self.btn_settings = wx.Button(self.panel, label=self.tr.get("btn_settings"))
		self.btn_settings.Bind(wx.EVT_BUTTON, self.on_open_settings)
		vbox.Add(self.btn_settings, 0, wx.ALL | wx.ALIGN_RIGHT, 15)

		self.panel.SetSizer(vbox)
		self.Centre()

	def update_ui_strings(self):
		self.SetTitle(self.tr.get("app_title"))
		self.lbl_info.SetLabel(self.tr.get("device_info", self.hostname, self.my_ip))
		self.link_box.GetStaticBox().SetLabel(self.tr.get("smartphone_link"))
		self.lbl_link_hint.SetLabel(self.tr.get("open_link"))
		self.lbl_pcs.SetLabel(self.tr.get("found_pcs"))
		self.btn_refresh.SetLabel(self.tr.get("btn_search"))
		self.lbl_what.SetLabel(self.tr.get("what_to_send"))
		
		self.mode_box.SetString(0, self.tr.get("mode_file"))
		self.mode_box.SetString(1, self.tr.get("mode_folder"))
		
		self.send_pc_btn.SetLabel(self.tr.get("btn_send_pc"))
		self.host_phone_btn.SetLabel(self.tr.get("btn_host_phone"))
		self.status_text.SetLabel(self.tr.get("status_ready"))
		self.btn_settings.SetLabel(self.tr.get("btn_settings"))
		
		self.panel.Layout()

	def show_notification(self, title, msg):
		if self.tb_icon:
			self.tb_icon.ShowBalloon(title, msg, 1000)

	def show_from_background(self):
		self.Show(True)
		if self.IsIconized():
			self.Iconize(False)
		self.Raise()

	def on_open_settings(self, event):
		dlg = SettingsDialog(self, self.settings, self.tr)
		if dlg.ShowModal() == wx.ID_OK:
			self.tr.update_lang()
			self.update_ui_strings()
		dlg.Destroy()

	def on_mode_change(self, event):
		self.Freeze()
		mode = self.mode_box.GetSelection()
		if mode == 0:
			self.dir_picker.Hide()
			self.file_picker.Show()
		else:
			self.file_picker.Hide()
			self.dir_picker.Show()
		
		self.picker_sizer.Layout()
		self.panel.Layout()
		self.SendSizeEvent()
		self.Thaw()

	def on_close_attempt(self, event):
		if self.is_closing or not self.settings.get("run_in_background"):
			self.tb_icon.RemoveIcon()
			self.tb_icon.Destroy()
			self.Destroy()
		else:
			self.Hide()

	def real_quit(self):
		self.running = False
		self.is_closing = True
		try: self.instance_sock.close()
		except: pass
		self.Close()

	def on_host_for_phone(self, event):
		mode = self.mode_box.GetSelection()
		path = self.file_picker.GetPath() if mode == 0 else self.dir_picker.GetPath()
		self.is_folder_mode = (mode == 1)

		if not path or not os.path.exists(path):
			wx.MessageBox(self.tr.get("msg_select_first"), "Info")
			return
		
		final_path = path
		if self.is_folder_mode:
			self.status_text.SetLabel(self.tr.get("msg_zipping"))
			try:
				final_path = ZipUtils.compress_folder(path)
				wx.CallAfter(self.status_text.SetLabel, self.tr.get("msg_zipped"))
			except Exception as e:
				wx.MessageBox(f"Error: {e}", "Error")
				return

		self.hosted_file_path = final_path
		fname = os.path.basename(final_path)
		
		if not self.is_folder_mode:
			msg = self.tr.get("msg_ready_file", fname)
		else:
			msg = self.tr.get("msg_ready_folder", fname)
			
		self.status_text.SetLabel(msg)
		wx.MessageBox(f"{msg}\n\n{self.tr.get('msg_update_web')}", "Info")

	def on_send_to_pc(self, event):
		idx = self.device_combo.GetSelection()
		if idx == wx.NOT_FOUND:
			wx.MessageBox(self.tr.get("msg_select_pc"), "Error")
			return
		target = self.device_combo.GetString(idx)
		ip = target.split('(')[1].replace(')', '')
		mode = self.mode_box.GetSelection()
		path = self.file_picker.GetPath() if mode == 0 else self.dir_picker.GetPath()
		is_folder = (mode == 1)
		
		if not path or not os.path.exists(path): return
		self.send_pc_btn.Disable()
		threading.Thread(target=self.send_file_thread, args=(ip, path, is_folder), daemon=True).start()

	def start_web_server(self):
		try:
			server = HTTPServer(('0.0.0.0', WEB_PORT), LandropHTTPHandler)
			server.app_window = self 
			while self.running: server.handle_request()
		except: pass

	def listen_for_instance(self):
		while self.running:
			try:
				self.instance_sock.settimeout(2)
				data, addr = self.instance_sock.recvfrom(1024)
				if data == b"WAKE_UP":
					wx.CallAfter(self.show_from_background)
			except:
				continue

	def send_file_thread(self, ip, filepath, is_folder):
		wx.CallAfter(self.gauge.SetValue, 0)
		final_path = filepath
		if is_folder:
			wx.CallAfter(self.status_text.SetLabel, self.tr.get("msg_zipping"))
			try: final_path = ZipUtils.compress_folder(filepath)
			except Exception as e:
				wx.CallAfter(wx.MessageBox, f"Error: {e}")
				wx.CallAfter(self.send_pc_btn.Enable)
				return
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.settimeout(10)
		try:
			filesize = os.path.getsize(final_path)
			filename = os.path.basename(final_path)
			wx.CallAfter(self.status_text.SetLabel, self.tr.get("msg_sending", ip))
			s.connect((ip, TRANSFER_PORT))
			s.send(f"{filename}{SEPARATOR}{filesize}".encode())
			ack = s.recv(1024).decode()
			if ack != "OK": raise Exception("No ACK")
			
			bytes_sent = 0
			last_progress = -1
			last_tick_time = time.time()
			
			# Startet den Loop (wird nur im Modern-Modus aktiv)
			wx.CallAfter(self.start_modern_tick_loop)
			
			with open(final_path, "rb") as f:
				while True:
					chunk = f.read(BUFFER_SIZE)
					if not chunk: break
					s.sendall(chunk)
					bytes_sent += len(chunk)
					
					progress = int((bytes_sent / filesize) * 100)
					if progress != last_progress:
						wx.CallAfter(self.gauge.SetValue, progress)
						last_progress = progress

					# Legacy-Tick einmal pro Sekunde triggern (wird im Modern-Modus ignoriert)
					now = time.time()
					if now - last_tick_time >= 1.0:
						wx.CallAfter(self.play_legacy_tick)
						last_tick_time = now

			wx.CallAfter(self.stop_all_sounds)
			wx.CallAfter(self.play_done_sound)
			wx.CallAfter(self.status_text.SetLabel, self.tr.get("msg_success"))
			wx.CallAfter(self.gauge.SetValue, 100)
		except Exception as e:
			wx.CallAfter(self.stop_all_sounds)
			wx.CallAfter(wx.MessageBox, f"Error: {e}", "Error", wx.ICON_ERROR)
		finally:
			s.close()
			wx.CallAfter(self.send_pc_btn.Enable)

	def start_file_server(self):
		server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			server_socket.bind(('0.0.0.0', TRANSFER_PORT))
			server_socket.listen(5)
		except: return
		while self.running:
			try:
				client, addr = server_socket.accept()
				if not self.running: break
				threading.Thread(target=self.handle_incoming_pc_file, args=(client,), daemon=True).start()
			except: break

	def handle_incoming_pc_file(self, client):
		try:
			received = client.recv(BUFFER_SIZE).decode()
			if not received:
				return
				
			filename, filesize = received.split(SEPARATOR)
			filename = os.path.basename(filename)
			filesize = int(filesize)
			client.send("OK".encode())
			
			save_path = os.path.join(self.get_save_path(), filename)
			wx.CallAfter(self.status_text.SetLabel, self.tr.get("msg_receiving", filename))
			
			bytes_read = 0
			
			with open(save_path, "wb") as f:
				while bytes_read < filesize:
					chunk = client.recv(BUFFER_SIZE)
					if not chunk: break
					f.write(chunk)
					bytes_read += len(chunk)

			wx.CallAfter(self.play_done_sound)

			status_msg = self.tr.get("msg_received", filename)
			if filename.endswith(".zip"):
				wx.CallAfter(self.status_text.SetLabel, self.tr.get("msg_extracting"))
				new_folder = ZipUtils.extract_zip(save_path, self.get_save_path())
				if new_folder:
					folder_name = os.path.basename(new_folder)
					status_msg = self.tr.get("msg_received_ext", folder_name)
			
			wx.CallAfter(self.status_text.SetLabel, status_msg)
			
			if not self.settings.get("play_done_sound"):
				wx.CallAfter(self.show_notification, APP_NAME, status_msg)
		except: pass
		finally: client.close()

	def listen_for_broadcasts(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try: sock.bind(('0.0.0.0', BROADCAST_PORT))
		except: return
		while self.running:
			try:
				sock.settimeout(2)
				data, addr = sock.recvfrom(1024)
				msg = json.loads(data.decode())
				if msg['ip'] != self.my_ip:
					if msg['ip'] not in self.peers:
						self.peers[msg['ip']] = msg['host']
						wx.CallAfter(self.update_peer_list, msg['ip'], msg['host'])
			except: continue

	def on_discovery_timer(self, event): 
		self.perform_discovery()
	
	def on_refresh(self, event):
		self.peers = {}
		self.device_combo.Clear()
		self.status_text.SetLabel("...") 
		self.perform_discovery()
		
	def perform_discovery(self):
		self.broadcast_presence()
		threading.Thread(target=self.discover_tailscale_peers, daemon=True).start()

	def discover_tailscale_peers(self):
		ts_peers = TailscaleUtils.get_online_peers()
		for ip, host in ts_peers:
			if ip not in self.peers:
				if self.check_port(ip, TRANSFER_PORT):
					self.peers[ip] = host
					wx.CallAfter(self.update_peer_list, ip, f"{host} [Tailscale]")

	def check_port(self, ip, port, timeout=1.5):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(timeout)
		try:
			result = sock.connect_ex((ip, port))
			return result == 0
		except:
			return False
		finally:
			sock.close()
		
	def broadcast_presence(self):
		msg = json.dumps({"host": self.hostname, "ip": self.my_ip})
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		try: sock.sendto(msg.encode(), ('<broadcast>', BROADCAST_PORT))
		except: pass
		finally: sock.close()
		
	def update_peer_list(self, ip, host):
		label = f"{host} ({ip})"
		if self.device_combo.FindString(label) == wx.NOT_FOUND:
			self.device_combo.Append(label)
			if self.device_combo.GetSelection() == wx.NOT_FOUND: self.device_combo.SetSelection(0)

if __name__ == '__main__':
	app = wx.App()
	
	instance_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		instance_sock.bind(('127.0.0.1', INSTANCE_PORT))
	except socket.error:
		instance_sock.sendto(b"WAKE_UP", ('127.0.0.1', INSTANCE_PORT))
		sys.exit(0)

	frame = FileTransferApp(instance_sock)
	if "--minimized" in sys.argv:
		frame.Show(False)
	else:
		frame.Show(True)
	app.MainLoop()