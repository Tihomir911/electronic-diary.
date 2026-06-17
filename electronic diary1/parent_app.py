
# parent_app_fixed.py
# Клиентское приложение для родителей
# Python 3.13, PyQt5

import sys, os, json, socket, threading, time, hashlib, base64
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QListWidget, QDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QColorDialog, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont


DESKTOP = Path.home() / "Desktop"
BIBI = DESKTOP / "bibi"
BIBI.mkdir(parents=True, exist_ok=True)


def derive_key(password: str) -> bytes:
    return hashlib.sha256(password.encode('utf-8')).digest()

def encrypt_text(plain: str, password: str) -> str:
    key = derive_key(password)
    data = plain.encode('utf-8')
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ key[i % len(key)])
    return base64.b64encode(bytes(out)).decode('utf-8')

def decrypt_text(cipher_b64: str, password: str) -> str:
    key = derive_key(password)
    try:
        data = base64.b64decode(cipher_b64.encode('utf-8'))
    except Exception:
        return ""
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ key[i % len(key)])
    try:
        return out.decode('utf-8')
    except Exception:
        return ""


class ParentClient(threading.Thread):
    def __init__(self, host, port, token, parent_fio, child_fio, callback):
        super().__init__(daemon=True)
        self.host, self.port, self.token = host, port, token
        self.parent_fio, self.child_fio = parent_fio, child_fio
        self.sock, self.running = None, False
        self.callback = callback

    def run(self):
        self.running = True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            msg = {"cmd": "subscribe", "token": self.token,
                   "parent_fio": self.parent_fio, "child_fio": self.child_fio}
            self.sock.sendall(json.dumps(msg).encode('utf-8'))

            while self.running:
                data = self.sock.recv(65536)
                if not data:
                    break
                try:
                    j = json.loads(data.decode('utf-8'))
                except:
                    continue
                if j.get("cmd") == "journal_update":
                    self.callback(self.token, j.get("journal"))
        except Exception as e:
            print("Client error:", e)

    def stop(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        
class AuthParentDialog(QDialog):
    def __init__(self, title, existing=False):
        super().__init__()
        self.setWindowTitle(title)
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)

        lbl = QLabel(title, alignment=Qt.AlignCenter)
        font = QFont(); font.setPointSize(14); font.setBold(True)
        lbl.setFont(font)
        layout.addWidget(lbl)

        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(QLabel("Пароль:")); layout.addWidget(self.password)

        # 👁 кнопка показать/скрыть
        eye = QPushButton("👁"); eye.setCheckable(True)
        def toggle_pw(ch): self.password.setEchoMode(QLineEdit.Normal if ch else QLineEdit.Password)
        eye.toggled.connect(toggle_pw)
        layout.addWidget(eye)

        self.fio = QLineEdit(); self.child = QLineEdit()
        if not existing:
            layout.addWidget(QLabel("ФИО родителя:")); layout.addWidget(self.fio)
            layout.addWidget(QLabel("ФИО ученика:")); layout.addWidget(self.child)

        btn = QPushButton("Продолжить"); btn.clicked.connect(self.accept)
        layout.addWidget(btn)



class ParentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parent App")
        self.resize(1100, 700)

        self.theme = {"mode": "dark", "bg": "#2b2b2b", "text": "#FFFFFF", "border": "#FFFFFF", "border_size": 1.0}
        self.groups = {}   # token -> {"journal":..., "client":...}
        self.current_token = None
        
        self.load_settings()
        self.load_or_register()

        self.parent_info = {"parent_fio": "Родитель", "child_fio": "Ученик"}

        self.build_ui()
        self.apply_theme()
        
    def load_or_register(self):
     file_path = BIBI / "parent_info.txt"
     if file_path.exists():
        # вход
        dlg = AuthParentDialog("Авторизация", existing=True)
        if dlg.exec_():
            password = dlg.password.text().strip()
            enc = file_path.read_text(encoding="utf-8")
            dec = decrypt_text(enc, password)
            if not dec:
                QMessageBox.warning(self, "Ошибка", "Неверный пароль")
                sys.exit(0)
            self.parent_info = json.loads(dec)
        else:
            sys.exit(0)
     else:
       
        dlg = AuthParentDialog("Регистрация", existing=False)
        if dlg.exec_():
            password = dlg.password.text().strip()
            parent_fio = dlg.fio.text().strip()
            child_fio = dlg.child.text().strip()
            if not password or not parent_fio:
                QMessageBox.warning(self, "Ошибка", "Заполните все поля")
                sys.exit(0)
            self.parent_info = {"parent_fio": parent_fio, "child_fio": child_fio}
            enc = encrypt_text(json.dumps(self.parent_info), password)
            file_path.write_text(enc, encoding="utf-8")
        else:
            sys.exit(0)
            
    def save_settings(self):
     path = BIBI / "parent_settings.json"
     with open(path, "w", encoding="utf-8") as f:
        json.dump({"theme": self.theme}, f, ensure_ascii=False, indent=2)

    def load_settings(self):
     path = BIBI / "parent_settings.json"
     if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                s = json.load(f)
            self.theme.update(s.get("theme", {}))
        except: pass

    def build_ui(self):
        layout = QHBoxLayout(self)

        
        left = QVBoxLayout()
        self.group_list = QListWidget()
        self.group_list.itemClicked.connect(self.on_group_selected)
        left.addWidget(QLabel("Мои группы", alignment=Qt.AlignCenter))
        left.addWidget(self.group_list)

        btn_add = QPushButton("Добавить группу")
        btn_add.clicked.connect(self.add_group_dialog)
        left.addWidget(btn_add)
        layout.addLayout(left, 1)

        
        right = QVBoxLayout()

        topbar = QHBoxLayout()
        self.btn_view = QPushButton("Вид")
        self.btn_view.clicked.connect(self.open_view_options)
        topbar.addWidget(self.btn_view)

        self.btn_theme = QPushButton("Тема")
        self.btn_theme.clicked.connect(self.toggle_theme)
        topbar.addWidget(self.btn_theme)

        right.addLayout(topbar)

        self.table = QTableWidget(0, 0)
        right.addWidget(self.table, 8)

        layout.addLayout(right, 3)

    
    def apply_theme(self):
        bg, text, border, bs = self.theme["bg"], self.theme["text"], self.theme["border"], self.theme["border_size"]
        self.setStyleSheet(f"""
          QWidget {{ background-color: {bg}; color: {text}; }}
          QPushButton {{ background-color: {bg}; color: {text}; border: {bs}px solid {border}; padding: 6px; border-radius: 6px }}
          QListWidget {{ background-color: {bg}; color: {text}; border: {bs}px solid {border} }}
          QTableWidget {{ background-color: {bg}; color: {text}; border: {bs}px solid {border} }}
          QHeaderView::section {{
             background-color: {bg};
             color: {text};
             border: {bs}px solid {border};
             padding: 4px;
           }}
        """)

    def open_view_options(self):
        dlg = QDialog(self); dlg.setWindowTitle("Вид")
        v = QVBoxLayout(dlg)
        btn_text, btn_bg, btn_border = QPushButton("Текст"), QPushButton("Фон"), QPushButton("Обводка")
        sp_border = QSpinBox(); sp_border.setRange(1, 20); sp_border.setValue(int(self.theme.get("border_size",1.0)*10))
        btn_text.clicked.connect(lambda: self.pick_color("text"))
        btn_bg.clicked.connect(lambda: self.pick_color("bg"))
        btn_border.clicked.connect(lambda: self.pick_color("border"))
        v.addWidget(btn_text); v.addWidget(btn_bg); v.addWidget(btn_border)
        v.addWidget(QLabel("Размер обводки (x0.1)")); v.addWidget(sp_border)
        def apply_and_close():
            self.theme["border_size"] = sp_border.value()/10.0
            self.apply_theme(); dlg.accept()
        v.addWidget(QPushButton("Применить", clicked=apply_and_close))
        dlg.exec_()

    def pick_color(self, key):
        c = QColorDialog.getColor()
        if c.isValid():
            self.theme[key] = c.name(); self.apply_theme()

    def toggle_theme(self):
        if self.theme["mode"] == "dark":
            self.theme.update({"mode":"light","bg":"#FFFFFF","text":"#000000","border":"#000000"})
        else:
            self.theme.update({"mode":"dark","bg":"#2b2b2b","text":"#FFFFFF","border":"#FFFFFF"})
        self.apply_theme()

    
    def add_group_dialog(self):
        dlg = QDialog(self); dlg.setWindowTitle("Добавить группу")
        v = QVBoxLayout(dlg)
        token_edit = QLineEdit(); v.addWidget(QLabel("Вставьте токен (формат: token@ip:port)")); v.addWidget(token_edit)
        def connect_group():
            tok = token_edit.text().strip()
            if "@" not in tok or ":" not in tok:
                QMessageBox.warning(dlg, "Ошибка", "Неверный формат токена"); return
            base, addr = tok.split("@",1); host, port = addr.split(":")
            client = ParentClient(host, int(port), base,
                                  self.parent_info["parent_fio"], self.parent_info["child_fio"],
                                  self.on_journal_received)
            client.start()
            self.groups[tok] = {"journal": None, "client": client}
            self.refresh_group_list()
            dlg.accept()
        v.addWidget(QPushButton("Подключиться", clicked=connect_group))
        dlg.exec_()

    def refresh_group_list(self):
        self.group_list.clear()
        for tok, data in self.groups.items():
            name = "(ожидание)" if not data["journal"] else data["journal"].get("name","журнал")
            self.group_list.addItem(f"{name} | {tok}")

    def on_group_selected(self, item):
        tok = item.text().split("|",1)[-1].strip()
        self.current_token = tok
        journal = self.groups[tok]["journal"]
        if journal: self.show_table(journal)

    def on_journal_received(self, token, journal):
        fulltok = [k for k in self.groups.keys() if k.startswith(token)][0]
        self.groups[fulltok]["journal"] = journal
        self.save_journal_local(fulltok, journal)
        self.refresh_group_list()
        if self.current_token == fulltok:
            self.show_table(journal)

    def show_table(self, journal):
        cols, rows = journal.get("cols", []), journal.get("rows", [])
        self.table.clear()
        self.table.setColumnCount(len(cols)); self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels(cols)
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                it = QTableWidgetItem(str(val))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, c, it)

    def save_journal_local(self, token, journal):
        safe = token.replace("@","_").replace(":","_")
        path = BIBI / f"journal_{safe}.txt"
        # шифруем ключом = ФИО родителя + токен
        key = self.parent_info.get("parent_fio","") + token
        enc = encrypt_text(json.dumps(journal, ensure_ascii=False), key)
        path.write_text(enc, encoding="utf-8")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ParentApp(); w.show()
    sys.exit(app.exec_())

