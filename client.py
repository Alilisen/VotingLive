import sys
import json
import traceback
from functools import partial
 
# Vérification paho et PyQt5
try:
    import paho.mqtt.client as mqtt
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QLabel,
        QPushButton, QMessageBox, QGridLayout, QLineEdit
    )
except ImportError as e:
    print(" Module manquant :", e)
    print("Installez-les avec `pip install paho-mqtt PyQt5`")
    sys.exit(1)
 
# -------- CONFIGURATION --------
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_QUESTION = "votinglivepoll/question"
TOPIC_VOTE     = "votinglivepoll/vote"
# ---------------------------------
 
class WelcomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        print("[DEBUG] WelcomeWindow init")
        self.setWindowTitle("Bienvenue – Voting Live")
        self.resize(400, 200)
        self.setStyleSheet("background-color: #1f0036; color: white;")
 
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30,30,30,30)
        layout.setSpacing(20)
 
        lbl = QLabel("Entre ton pseudo :")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size:16px;")
        layout.addWidget(lbl)
 
        self.input = QLineEdit()
        self.input.setPlaceholderText("Pseudo")
        self.input.setStyleSheet(
            "QLineEdit { padding:8px; font-size:14px;"
            " border:2px solid #8f00ff; border-radius:8px; }"
        )
        layout.addWidget(self.input)
 
        btn = QPushButton("Valider")
        btn.setStyleSheet(
            "QPushButton { background-color:#8f00ff; color:white;"
            " font-size:14px; padding:8px; border-radius:8px; }"
            " QPushButton:hover { background-color:#aa33ff; }"
        )
        btn.clicked.connect(self.on_validate)
        layout.addWidget(btn)
 
        self.show()
        print("[DEBUG] WelcomeWindow shown")
 
    def on_validate(self):
        pseudo = self.input.text().strip()
        print(f"[DEBUG] Valider clicked, pseudo='{pseudo}'")
        if not pseudo:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un pseudo.")
            return
        try:
            self.client = VotingClient(pseudo)
            self.close()
        except Exception:
            traceback.print_exc()
 
class VotingClient(QWidget):
    question_signal = pyqtSignal(str, list)
 
    def __init__(self, pseudo):
        super().__init__()
        print(f"[DEBUG] VotingClient init with pseudo={pseudo}")
        self.pseudo = pseudo
        self.setWindowTitle(f"Sondage live — {pseudo}")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #0d0026;")
 
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40,40,40,40)
        layout.setSpacing(30)
 
        self.lbl_question = QLabel("En attente de question…")
        self.lbl_question.setWordWrap(True)
        self.lbl_question.setAlignment(Qt.AlignCenter)
        self.lbl_question.setStyleSheet(
            "QLabel { color:white; font-size:22px; font-weight:bold;"
            " padding:20px; border:3px solid #9b4dff; border-radius:15px;"
            " background-color:#1a0033; }"
        )
        layout.addWidget(self.lbl_question)
 
        self.grid = QGridLayout()
        self.grid.setSpacing(20)
        layout.addLayout(self.grid)
        self.buttons = []
 
        # Connexion du signal
        self.question_signal.connect(self.handle_question)
 
        # Démarre MQTT
        try:
            self.start_mqtt()
        except Exception:
            traceback.print_exc()
 
        self.show()
        print("[DEBUG] VotingClient shown")
 
    def start_mqtt(self):
        print("[DEBUG] Initializing MQTT client")
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER, PORT)
        self.client.loop_start()
        print("[DEBUG] MQTT loop started")
 
    def on_connect(self, client, userdata, flags, rc):
        print(f"[DEBUG] on_connect rc={rc}")
        client.subscribe(TOPIC_QUESTION)
        print(f"[DEBUG] Subscribed to {TOPIC_QUESTION}")
 
    def on_message(self, client, userdata, msg):
        print(f"[DEBUG] on_message topic={msg.topic} payload={msg.payload}")
        try:
            data = json.loads(msg.payload.decode())
            question = data["question"]
            choices = data["choices"]
            print(f"[DEBUG] Parsed question='{question}', choices={choices}")
        except Exception as e:
            print("[ERROR] Invalid JSON or missing keys:", e)
            return
        # Émet le signal au thread UI
        self.question_signal.emit(question, choices)
 
    def handle_question(self, question, choices):
        print(f"[DEBUG] handle_question question='{question}', choices={choices}")
        self.lbl_question.setText(question)
        # Supprime anciens
        for b in self.buttons:
            self.grid.removeWidget(b)
            b.deleteLater()
        self.buttons.clear()
        # Crée nouveaux
        for i, text in enumerate(choices):
            btn = QPushButton(f"{chr(65+i)}. {text}")
            btn.setMinimumHeight(60)
            btn.setStyleSheet(
                "QPushButton { background-color:#1a0033; color:white;"
                " border:3px solid #9b4dff; border-radius:12px;"
                " font-size:18px; font-weight:bold; }"
                " QPushButton:hover { background-color:#330066; }"
            )
            btn.clicked.connect(partial(self.send_vote, text))
            self.buttons.append(btn)
            row, col = divmod(i,2)
            self.grid.addWidget(btn, row, col)
 
    def send_vote(self, choice):
        print(f"[DEBUG] Sending vote '{choice}'")
        payload = json.dumps({"pseudo":self.pseudo,"reponse":choice})
        self.client.publish(TOPIC_VOTE, payload)
        QMessageBox.information(self, "Vote envoyé", f"Tu as voté : {choice}")
 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        w = WelcomeWindow()
        sys.exit(app.exec_())
    except Exception:
        traceback.print_exc()