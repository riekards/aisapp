from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QListWidget, QLabel, QHBoxLayout
)

class MainWindow(QMainWindow):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.setWindowTitle("Self-Evolving AI")
        self._build_ui()

    def _build_ui(self):
        container = QWidget()
        layout = QVBoxLayout()

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        # Input line
        input_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.on_send)
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)

        # Features list
        layout.addWidget(QLabel("Requested Features:"))
        self.features_list = QListWidget()
        layout.addWidget(self.features_list)
        add_feat_btn = QPushButton("Refresh Features")
        add_feat_btn.clicked.connect(self.load_features)
        layout.addWidget(add_feat_btn)

        container.setLayout(layout)
        self.setCentralWidget(container)
        self.load_features()

    def load_features(self):
        self.features_list.clear()
        for f in self.agent.get_features():
            self.features_list.addItem(f)

    def on_send(self):
        user_text = self.input_line.text().strip()
        if not user_text:
            return
        self.chat_display.append(f"<You> {user_text}")
        self.input_line.clear()

        reply = self.agent.handle(user_text)
        self.chat_display.append(f"<AI> {reply}")
        # reload features in case they changed
        self.load_features()
