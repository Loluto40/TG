# gui_app.py
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QLineEdit, QListWidget, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from subprocess import Popen, PIPE


GROUPS_FILE = 'groups.txt'
PROXIES_FILE = 'proxies.txt'


class Worker(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, channel, cmd):
        super().__init__()
        self.channel = channel
        self.cmd = cmd

    def run(self):
        args = ['python', 'core.py', self.channel, self.cmd]
        process = Popen(args, stdout=PIPE, stderr=PIPE, text=True)
        for line in iter(process.stdout.readline, ''):
            self.log_signal.emit(line.strip())
        for line in iter(process.stderr.readline, ''):
            self.log_signal.emit(f"[ERROR] {line.strip()}")


class GroupProxyManager(QWidget):
    groups_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление группами и прокси")
        self.resize(400, 300)
        layout = QVBoxLayout()

        # Управление группами
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("Введите @username или ID группы")
        layout.addWidget(QLabel("Добавить группу:"))
        layout.addWidget(self.group_input)

        add_group_btn = QPushButton("Добавить группу")
        add_group_btn.clicked.connect(self.add_group)
        layout.addWidget(add_group_btn)

        self.group_list = QListWidget()
        layout.addWidget(QLabel("Список групп:"))
        layout.addWidget(self.group_list)

        del_group_btn = QPushButton("Удалить выбранную группу")
        del_group_btn.clicked.connect(self.delete_selected_group)
        layout.addWidget(del_group_btn)

        # Управление прокси
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("ip:port:user:pass или ip:port")
        layout.addWidget(QLabel("Добавить прокси:"))
        layout.addWidget(self.proxy_input)

        add_proxy_btn = QPushButton("Добавить прокси")
        add_proxy_btn.clicked.connect(self.add_proxy)
        layout.addWidget(add_proxy_btn)

        self.proxy_list = QListWidget()
        layout.addWidget(QLabel("Список прокси:"))
        layout.addWidget(self.proxy_list)

        del_proxy_btn = QPushButton("Удалить выбранный прокси")
        del_proxy_btn.clicked.connect(self.delete_selected_proxy)
        layout.addWidget(del_proxy_btn)

        self.setLayout(layout)
        self.load_groups()
        self.load_proxies()

    def load_groups(self):
        self.group_list.clear()
        if not os.path.exists(GROUPS_FILE):
            return
        with open(GROUPS_FILE, 'r') as f:
            for line in f:
                group = line.strip()
                if group:
                    self.group_list.addItem(group)

    def save_groups(self):
        groups = [self.group_list.item(i).text() for i in range(self.group_list.count())]
        with open(GROUPS_FILE, 'w') as f:
            f.write('\n'.join(groups))
        self.groups_updated.emit()

    def add_group(self):
        group = self.group_input.text().strip()
        if group:
            self.group_list.addItem(group)
            self.save_groups()
            self.group_input.clear()

    def delete_selected_group(self):
        selected = self.group_list.currentRow()
        if selected >= 0:
            self.group_list.takeItem(selected)
            self.save_groups()

    def load_proxies(self):
        self.proxy_list.clear()
        if not os.path.exists(PROXIES_FILE):
            return
        with open(PROXIES_FILE, 'r') as f:
            for line in f:
                proxy = line.strip()
                if proxy:
                    self.proxy_list.addItem(proxy)

    def save_proxies(self):
        proxies = [self.proxy_list.item(i).text() for i in range(self.proxy_list.count())]
        with open(PROXIES_FILE, 'w') as f:
            f.write('\n'.join(proxies))

    def add_proxy(self):
        proxy = self.proxy_input.text().strip()
        if proxy:
            self.proxy_list.addItem(proxy)
            self.save_proxies()
            self.proxy_input.clear()

    def delete_selected_proxy(self):
        selected = self.proxy_list.currentRow()
        if selected >= 0:
            self.proxy_list.takeItem(selected)
            self.save_proxies()


class TGAppGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Reposter — Linux")
        self.resize(1000, 600)

        main_layout = QHBoxLayout()

        # Левая часть — управление группами и прокси
        self.manager = GroupProxyManager()
        main_layout.addWidget(self.manager, stretch=1)

        # Правая часть — основной интерфейс управления командами
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        # Канал-источник
        self.source_input = QLineEdit("@mychannel")
        right_layout.addWidget(QLabel("Канал-источник:"))
        right_layout.addWidget(self.source_input)

        # Лог действий
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #f0f0f0; color: black;")
        right_layout.addWidget(QLabel("Лог действий:"))
        right_layout.addWidget(self.log_box)

        # Кнопки команд
        btn_layout = QHBoxLayout()
        self.btn_repost = QPushButton("Репостить все")
        self.btn_pin = QPushButton("Закрепить")
        self.btn_unpin = QPushButton("Открепить")
        self.btn_delete = QPushButton("Удалить последний")

        self.btn_repost.clicked.connect(lambda: self.send_command("/repost_all"))
        self.btn_pin.clicked.connect(lambda: self.send_command("/pin_last"))
        self.btn_unpin.clicked.connect(lambda: self.send_command("/unpin_last"))
        self.btn_delete.clicked.connect(lambda: self.send_command("/delete_last"))

        btn_layout.addWidget(self.btn_repost)
        btn_layout.addWidget(self.btn_pin)
        btn_layout.addWidget(self.btn_unpin)
        btn_layout.addWidget(self.btn_delete)
        right_layout.addLayout(btn_layout)

        right_panel.setLayout(right_layout)
        main_layout.addWidget(right_panel, stretch=2)
        self.setLayout(main_layout)

    def send_command(self, cmd):
        channel = self.source_input.text().strip()
        if not channel:
            self.append_log("[Ошибка] Укажите канал-источник")
            return

        self.worker = Worker(channel, cmd)
        self.worker.log_signal.connect(self.append_log)
        self.worker.start()
        self.append_log(f"Выполняется команда: {cmd}")

    def append_log(self, text):
        self.log_box.append(text)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TGAppGUI()
    window.show()
    sys.exit(app.exec_())