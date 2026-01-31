import sys
import json
import os
import serial
import serial.tools.list_ports

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QSpinBox, QComboBox, QGroupBox, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

PRESET_FILE = "presets.json"


class StepperController(QWidget):
    def __init__(self):
        super().__init__()

        self.serial = None
        self.current_position = 0
        self.presets = {}

        self.setWindowTitle("Candel Maker")
        self.setFixedWidth(460)
        script_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(script_dir, 'logo.png') # Assumes 'logo.png' is in the same directory
        self.setWindowIcon(QIcon(icon_path)) # Set the window icon
        self.init_ui()
        self.refresh_ports()
        self.load_presets()

        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial)
        self.timer.start(50)

    # ---------------- UI ----------------
    def init_ui(self):
        layout = QVBoxLayout()

        # ===== Serial =====
        serial_group = QGroupBox("Serial Connection")
        serial_layout = QHBoxLayout()

        self.port_combo = QComboBox()


        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)

        serial_layout.addWidget(self.port_combo)
        serial_layout.addWidget(self.connect_btn)
        serial_group.setLayout(serial_layout)
        layout.addWidget(serial_group)

        self.conn_status = QLabel("Disconnected")
        self.conn_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.conn_status)

        # ===== Home =====
        self.home_btn = QPushButton("Home")
        self.home_btn.clicked.connect(self.home)
        layout.addWidget(self.home_btn)

        # ===== Absolute Move =====
        abs_group = QGroupBox("Absolute Move")
        abs_layout = QVBoxLayout()

        self.target_spin = QSpinBox()
        self.target_spin.setRange(-5, 1000)
        self.target_spin.setSuffix(" mm")

        self.abs_btn = QPushButton("Move Absolute")
        self.abs_btn.clicked.connect(self.move_absolute)

        abs_layout.addWidget(self.target_spin)
        abs_layout.addWidget(self.abs_btn)
        abs_group.setLayout(abs_layout)
        layout.addWidget(abs_group)

        # ===== Actual Index =====
        self.index_label = QLabel("Actual Index: 0")
        self.index_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.index_label)
        # ===== Index Move =====
        index_group = QGroupBox("Index Move")
        index_layout = QHBoxLayout()
        
        self.target_index = QSpinBox()
        self.target_index.setRange(0, 5)
        self.target_index.setSuffix(" index")
        self.index_btn = QPushButton("Move to Index")
        self.index_btn.clicked.connect(lambda: self.index(self.target_index.value()))
        index_layout.addWidget(self.target_index)
        index_layout.addWidget(self.index_btn)
        index_group.setLayout(index_layout)
        layout.addWidget(index_group)
        



        # ===== Presets =====
        preset_group = QGroupBox("Presets")
        preset_layout = QHBoxLayout()

        self.preset_combo = QComboBox()

        self.load_preset_btn = QPushButton("Load")


        self.load_preset_btn.clicked.connect(self.load_preset)

        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.load_preset_btn)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

    

        # ===== Status =====
        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    # ---------------- Presets ----------------
    def load_presets(self):
        if os.path.exists(PRESET_FILE):
            with open(PRESET_FILE, "r") as f:
                self.presets = json.load(f)

        self.preset_combo.clear()
        self.preset_combo.addItems(self.presets.keys())

    def load_preset(self):
        name = self.preset_combo.currentText()
        if name not in self.presets:
            return

        preset = self.presets[name]

        self.target_spin.setValue(preset["position"])

        reply = QMessageBox.question(
            self, "Load Preset",
            f"Move to preset '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.move_absolute()

    # ---------------- Serial ----------------
    def refresh_ports(self):
        self.port_combo.clear()
        for p in serial.tools.list_ports.comports():
            self.port_combo.addItem(p.device)

    def toggle_connection(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.serial = None
            self.conn_status.setText("Disconnected")
            self.connect_btn.setText("Connect")
            return

        try:
            self.serial = serial.Serial(
                self.port_combo.currentText(),
                115200,
                timeout=0.1
            )
            self.conn_status.setText("Connected")
            self.connect_btn.setText("Disconnect")
        except Exception as e:
            self.conn_status.setText(str(e))

    def read_serial(self):
        if not self.serial or not self.serial.is_open:
            return

        while self.serial.in_waiting:
            line = self.serial.readline().decode().strip()


    # ---------------- Controls ----------------
    def move_absolute(self):
        target = self.target_spin.value()
        self.send(f"Moveto_mm{target}")
        self.status_label.setText(f"Moving to {target} mm")

    def home(self):
        self.send("Homing")
        self.status_label.setText("Homing")

    def send(self, cmd):
        if self.serial and self.serial.is_open:
            self.serial.write((cmd + "\n").encode())

    def index(self, index_number):
        self.send(f"index_n{index_number}")
        self.status_label.setText(f"Moving to index {index_number}")
    # ---------------- Styling ----------------
    def style_limit(self, label, active):
        label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {"red" if active else "green"};
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 8px;
            }}
            """
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = StepperController()
    win.show()
    sys.exit(app.exec_())
