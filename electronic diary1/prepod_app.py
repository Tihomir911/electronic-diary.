# prepod_app_fixed.py
"""
Prepod - исправленная версия
Python 3.13, PyQt5
"""

import os
import sys
import sqlite3
import json
import base64
import secrets
import hashlib
import time
from datetime import datetime
from pathlib import Path
from functools import partial
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGridLayout, QListWidget, QTableWidget, QTableWidgetItem,
    QColorDialog, QSpinBox, QDialog, QMessageBox, QTextEdit, QInputDialog
)
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt, QTimer
import socket
import threading


DESKTOP = Path.home() / "Desktop"
BIBI = DESKTOP / "bibi"
BIBI.mkdir(parents=True, exist_ok=True)

DB_PATH = BIBI / "prepod_db.sqlite"
SETTINGS_PATH = BIBI / "prepod_settings.json"
EXPORT_PATH = BIBI / "exports"
EXPORT_PATH.mkdir(exist_ok=True)



def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS teacher (
        id INTEGER PRIMARY KEY,
        fio TEXT,
        subject TEXT,
        password_hash TEXT,
        salt TEXT,
        logged_in INTEGER DEFAULT 0
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY,
        name TEXT,
        token TEXT UNIQUE
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY,
        fio TEXT,
        group_id INTEGER,
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS parents (
        id INTEGER PRIMARY KEY,
        parent_fio TEXT,
        student_fio TEXT,
        group_id INTEGER,
        password_enc TEXT,
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS journals (
        id INTEGER PRIMARY KEY,
        group_id INTEGER,
        table_json TEXT,
        last_updated TIMESTAMP,
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )''')
    conn.commit()
    conn.close()

init_db()


def _derive_key_bytes(password: str, salt: str) -> bytes:
    return hashlib.sha256((password + salt).encode('utf-8')).digest()

def encrypt_text(plaintext: str, password: str, salt: str) -> str:
    kb = _derive_key_bytes(password, salt)
    data = plaintext.encode('utf-8')
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ kb[i % len(kb)])
    return base64.b64encode(bytes(out)).decode('utf-8')

def decrypt_text(ciphertext_b64: str, password: str, salt: str) -> str:
    kb = _derive_key_bytes(password, salt)
    data = base64.b64decode(ciphertext_b64.encode('utf-8'))
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ kb[i % len(kb)])
    return out.decode('utf-8')


def get_teacher():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT id, fio, subject, password_hash, salt, logged_in FROM teacher LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row

def save_teacher(fio, subject, password_hash, salt):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("DELETE FROM teacher")
    c.execute("INSERT INTO teacher (fio, subject, password_hash, salt, logged_in) VALUES (?, ?, ?, ?, 1)",
              (fio, subject, password_hash, salt))
    conn.commit()
    conn.close()

def set_teacher_logged(flag: bool):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("UPDATE teacher SET logged_in = ?", (1 if flag else 0,))
    conn.commit()
    conn.close()


SERVER_PORT = 50000

class SimpleSenderServer(threading.Thread):
    def __init__(self, host="0.0.0.0", port=SERVER_PORT):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.sock = None
        self._running = False
        self.connected_parents = {}

    def run(self):
        self._running = True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.listen(5)
        except Exception as e:
            print("Server start error:", e)
            return

        while self._running:
            try:
                client, addr = self.sock.accept()
                threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
            except Exception:
                break

        def handle_client(self, client: socket.socket, addr):
            try:
              data = client.recv(65536).decode('utf-8').strip()
              if not data:
                client.close()
                return
              try:
                  msg = json.loads(data)
              except:
                client.close()
                return

              if msg.get("cmd") == "subscribe":
                token = msg.get("token")
                parent_fio = msg.get("parent_fio", "?")
                child_fio = msg.get("child_fio", "?")

                # сохраняем подключенного родителя
                self.connected_parents[token] = {
                    "addr": addr,
                    "time": time.time(),
                    "parent_fio": parent_fio,
                    "child_fio": child_fio
                }

                # уведомление в UI
                if hasattr(self, "ui_callback"):
                    self.ui_callback(f"👨‍👩‍👦 Родитель {parent_fio} (ученик {child_fio}) подключился к группе [{token}] с IP {addr[0]}")

                # сразу отправляем последний журнал группы
                conn = sqlite3.connect(str(DB_PATH))
                c = conn.cursor()
                c.execute("""
                    SELECT table_json FROM journals 
                    WHERE group_id=(SELECT id FROM groups WHERE token=?)
                    ORDER BY last_updated DESC LIMIT 1
                """, (token,))
                row = c.fetchone()
                conn.close()
                if row:
                    try:
                        j = {"cmd": "journal_update", "journal": json.loads(row[0])}
                        client.sendall(json.dumps(j, ensure_ascii=False).encode('utf-8'))
                    except Exception as e:
                        print("send journal error:", e)

              client.close()
            except Exception as e:
             print("handle_client error:", e)
            try:
                client.close()
            except:
                pass


    def stop(self):
        self._running = False
        try:
            if self.sock:
                self.sock.close()
        except:
            pass


class PrepodApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prepod - журнал")
        self.resize(1100, 700)

        # тема по-умолчанию
        self.theme = {
            "mode": "dark",
            "bg": "#2b2b2b",
            "text": "#FFFFFF",
            "border": "#FFFFFF",
            "border_size": 1.0
        }
        self.load_settings()

        # UI
        self.init_ui()

        # подключение: редактирование заголовка по двойному клику
        self.table.horizontalHeader().sectionDoubleClicked.connect(self.edit_header)

        # сервер
        self.server = SimpleSenderServer()
        self.server.ui_callback = self.show_msg

        try:
            self.server.start()
        except Exception as e:
            print("Server start exception:", e)

        # автосохранение
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(10 * 60 * 1000)  # 10 минут
        self.autosave_timer.timeout.connect(self.auto_save_current_group)

 
    def init_ui(self):
        layout = QHBoxLayout(self)

        # левая панель
        left = QVBoxLayout()
        lbl = QLabel("Группы")
        lbl.setAlignment(Qt.AlignCenter)
        left.addWidget(lbl)
        self.group_list = QListWidget()
        self.group_list.itemClicked.connect(self.on_group_selected)
        left.addWidget(self.group_list)

        btn_create_group = QPushButton("Создать группу")
        btn_create_group.clicked.connect(self.create_group_dialog)
        left.addWidget(btn_create_group)

        btn_open_parents = QPushButton("Открыть базу с родителями")
        btn_open_parents.clicked.connect(self.open_parents_db)
        left.addWidget(btn_open_parents)

        layout.addLayout(left, 1)

        right = QVBoxLayout()

        topbar = QHBoxLayout()
        self.btn_view = QPushButton("Вид")
        self.btn_view.clicked.connect(self.open_view_options)
        topbar.addWidget(self.btn_view)

        self.btn_theme = QPushButton("Тема")
        
        
