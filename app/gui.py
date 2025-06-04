from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QListWidget, QLabel, QHBoxLayout, QListWidgetItem,
)
from PyQt5.QtCore import Qt

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

        #Delete feature button
        self.deleteFeatureBtn = QPushButton("Delete Selected Feature")
        self.deleteFeatureBtn.setEnabled(False)
        layout.addWidget(self.deleteFeatureBtn)

        self.features_list.itemSelectionChanged.connect(self.on_feature_selected)
        self.deleteFeatureBtn.clicked.connect(self.on_delete_feature)

    def load_features(self):
        self.features_list.clear()
        for fid, desc in self.agent.get_features():
            item = QListWidgetItem(desc)
            item.setData(Qt.UserRole, fid)
            self.features_list.addItem(item)

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

    def on_feature_selected(self):
        # Enable the delete button only when exactly one feature is selected
        has_sel = len(self.features_list.selectedItems()) == 1
        self.deleteFeatureBtn.setEnabled(has_sel)

    def on_delete_feature(self):
        item = self.features_list.currentItem()
        if not item:
            return
        # retrieve the feature’s database ID stored in UserRole
        feature_id = item.data(Qt.UserRole)
        # tell the agent (and thus Memory) to delete it
        self.agent.delete_feature(feature_id)
        # remove it from the widget
        row = self.features_list.row(item)
        self.features_list.takeItem(row)