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

        self.setWindowTitle("Stepper Motor Controller")
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
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "115200", "250000"])
        self.baud_combo.setCurrentText("115200")

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)

        serial_layout.addWidget(self.port_combo)
        serial_layout.addWidget(self.baud_combo)
        serial_layout.addWidget(self.connect_btn)
        serial_group.setLayout(serial_layout)
        layout.addWidget(serial_group)

        self.conn_status = QLabel("Disconnected")
        self.conn_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.conn_status)

        # ===== Position =====
        self.pos_label = QLabel("Current position: 0 steps")
        self.pos_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.pos_label)

        # ===== Absolute Move =====
        abs_group = QGroupBox("Absolute Move")
        abs_layout = QVBoxLayout()

        self.target_spin = QSpinBox()
        self.target_spin.setRange(-100000, 100000)
        self.target_spin.setSuffix(" steps")

        self.abs_btn = QPushButton("Move Absolute")
        self.abs_btn.clicked.connect(self.move_absolute)

        abs_layout.addWidget(self.target_spin)
        abs_layout.addWidget(self.abs_btn)
        abs_group.setLayout(abs_layout)
        layout.addWidget(abs_group)

        # ===== Relative Move =====
        rel_group = QGroupBox("Relative Move")
        rel_layout = QHBoxLayout()

        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 10000)
        self.step_spin.setValue(100)
        self.step_spin.setSuffix(" steps")

        self.plus_btn = QPushButton("+")
        self.minus_btn = QPushButton("-")

        self.plus_btn.clicked.connect(lambda: self.move_relative(1))
        self.minus_btn.clicked.connect(lambda: self.move_relative(-1))

        rel_layout.addWidget(self.step_spin)
        rel_layout.addWidget(self.plus_btn)
        rel_layout.addWidget(self.minus_btn)
        rel_group.setLayout(rel_layout)
        layout.addWidget(rel_group)

        # ===== Speed =====
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 5000)
        self.speed_spin.setValue(500)
        self.speed_spin.setSuffix(" steps/s")
        layout.addWidget(self.speed_spin)

        # ===== Presets =====
        preset_group = QGroupBox("Presets")
        preset_layout = QHBoxLayout()

        self.preset_combo = QComboBox()

        self.save_preset_btn = QPushButton("Save")
        self.load_preset_btn = QPushButton("Load")

        self.save_preset_btn.clicked.connect(self.save_preset)
        self.load_preset_btn.clicked.connect(self.load_preset)

        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.save_preset_btn)
        preset_layout.addWidget(self.load_preset_btn)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # ===== Home =====
        self.home_btn = QPushButton("Home")
        self.home_btn.clicked.connect(self.home)
        layout.addWidget(self.home_btn)

        # ===== Limit Switches =====
        limit_group = QGroupBox("Limit Switches")
        limit_layout = QHBoxLayout()

        self.min_limit = QLabel("MIN")
        self.max_limit = QLabel("MAX")

        self.style_limit(self.min_limit, False)
        self.style_limit(self.max_limit, False)

        limit_layout.addWidget(self.min_limit)
        limit_layout.addWidget(self.max_limit)
        limit_group.setLayout(limit_layout)
        layout.addWidget(limit_group)

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

    def save_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not name:
            return

        self.presets[name] = {
            "position": self.current_position,
            "speed": self.speed_spin.value()
        }

        with open(PRESET_FILE, "w") as f:
            json.dump(self.presets, f, indent=4)

        self.load_presets()
        self.preset_combo.setCurrentText(name)

    def load_preset(self):
        name = self.preset_combo.currentText()
        if name not in self.presets:
            return

        preset = self.presets[name]

        self.target_spin.setValue(preset["position"])
        self.speed_spin.setValue(preset["speed"])

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
                int(self.baud_combo.currentText()),
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
            self.parse_message(line)

    # ---------------- Protocol ----------------
    def parse_message(self, msg):
        parts = msg.split()

        if parts[0] == "POS":
            self.current_position = int(parts[1])
            self.pos_label.setText(f"Current position: {self.current_position} steps")

        elif parts[0] == "LIM":
            label = self.min_limit if parts[1] == "MIN" else self.max_limit
            self.style_limit(label, int(parts[2]))

    # ---------------- Controls ----------------
    def move_absolute(self):
        target = self.target_spin.value()
        speed = self.speed_spin.value()
        self.send(f"MOVE {target} {speed}")
        self.status_label.setText(f"Moving to {target}")

    def move_relative(self, direction):
        step = self.step_spin.value() * direction
        speed = self.speed_spin.value()
        self.send(f"MOVEREL {step} {speed}")

    def home(self):
        self.send("HOME")
        self.status_label.setText("Homing")

    def send(self, cmd):
        if self.serial and self.serial.is_open:
            self.serial.write((cmd + "\n").encode())

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
