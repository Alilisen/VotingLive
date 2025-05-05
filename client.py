import sys
import json
import traceback
from functools import partial
from datetime import datetime

# Vérification paho-mqtt et PyQt5
try:
    import paho.mqtt.client as mqtt
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QLabel,
        QPushButton, QMessageBox, QGridLayout, QLineEdit,
        QScrollArea
    )
except ImportError as e:
    print("Module manquant :", e)
    print("Installez-les avec : pip install paho-mqtt PyQt5")
    sys.exit(1)

# -------- CONFIGURATION --------
BROKER         = "broker.hivemq.com"
PORT           = 1883
TOPIC_QUESTION = "votinglivepoll/question"
TOPIC_VOTE     = "votinglivepoll/vote"
# ---------------------------------

class WelcomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bienvenue – Voting Live")
        self.resize(400, 200)
        self.setStyleSheet("background-color: #1f0036; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
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

    def on_validate(self):
        pseudo = self.input.text().strip()
        if not pseudo:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un pseudo.")
            return
        try:
            self.client = VotingClient(pseudo)
            self.close()
        except Exception:
            traceback.print_exc()

class VotingClient(QWidget):
    # signal: index, question, choices
    question_signal = pyqtSignal(int, str, list)

    def __init__(self, pseudo):
        super().__init__()
        self.pseudo = pseudo
        self.polls = []             # stockage des sondages reçus
        self.voted_polls = set()    # indices des sondages déjà votés
        self.current_poll_idx = None

        self.setWindowTitle(f"Sondage live — {pseudo}")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #0d0026;")

        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(30)

        # Label question
        self.lbl_question = QLabel("En attente de question…")
        self.lbl_question.setWordWrap(True)
        self.lbl_question.setAlignment(Qt.AlignCenter)
        self.lbl_question.setStyleSheet(
            "QLabel { color:white; font-size:22px; font-weight:bold;"
            " padding:20px; border:3px solid #9b4dff; border-radius:15px;"
            " background-color:#1a0033; }"
        )
        self.main_layout.addWidget(self.lbl_question)

        # Grille choix
        self.grid = QGridLayout()
        self.grid.setSpacing(20)
        self.main_layout.addLayout(self.grid)
        self.buttons = []

        # Zone liste des sondages
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("border: none;")
        self.scroll_area.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(20)
        self.scroll_area.setWidget(self.list_container)
        self.scroll_area.hide()
        self.main_layout.addWidget(self.scroll_area)

        # Connexion du signal
        self.question_signal.connect(self.handle_question)

        # Démarrer MQTT
        try:
            self.start_mqtt()
        except Exception:
            traceback.print_exc()

        self.show()

    def start_mqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER, PORT)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe(TOPIC_QUESTION)

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            question = data["question"]
            choices = data["choices"]
        except Exception:
            return
        # Stocker le sondage et émettre son index
        idx = len(self.polls)
        self.polls.append((question, choices))
        self.question_signal.emit(idx, question, choices)

    def handle_question(self, idx, question, choices):
        self.current_poll_idx = idx
        already_voted = idx in self.voted_polls

        # Afficher question, cacher liste
        self.scroll_area.hide()
        self.lbl_question.show()
        for b in self.buttons:
            b.show()

        # Mettre à jour question et choix
        self.lbl_question.setText(question)
        # Nettoyer anciens boutons
        for b in self.buttons:
            self.grid.removeWidget(b)
            b.deleteLater()
        self.buttons.clear()
        # Créer boutons de choix
        for i, text in enumerate(choices):
            btn = QPushButton(f"{chr(65 + i)}. {text}")
            btn.setMinimumHeight(60)
            btn.setStyleSheet(
                "QPushButton { background-color:#1a0033; color:white;"
                " border:3px solid #9b4dff; border-radius:12px;"
                " font-size:18px; font-weight:bold; }"
                " QPushButton:hover { background-color:#330066; }"
            )
            btn.setEnabled(not already_voted)
            btn.clicked.connect(partial(self.send_vote, text))
            self.buttons.append(btn)
            row, col = divmod(i, 2)
            self.grid.addWidget(btn, row, col)

    def send_vote(self, choice):
        idx = self.current_poll_idx
        if idx in self.voted_polls:
            return
        timestamp = int(datetime.now().timestamp())
        # Payload avec la question associée
        payload = json.dumps({
            "pseudo":   self.pseudo,
            "question": self.lbl_question.text(),
            "reponse":  choice,
            "timestamp": timestamp
        })
        self.client.publish(TOPIC_VOTE, payload)

        # Confirmation
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Succès")
        msg.setText("Votre vote a été enregistré !")
        msg.setStyleSheet(
            "QLabel { color: white; }"
            "QPushButton { color: white; background-color: #8f00ff;"
            " border-radius:6px; padding:6px 12px; }"
            "QPushButton:hover { background-color: #b84dff; }"
        )
        msg.exec_()

        # Marquer module comme voté
        self.voted_polls.add(idx)
        for b in self.buttons:
            b.setEnabled(False)

        # Afficher liste des sondages restants
        self.show_poll_list()

    def show_poll_list(self):
        self.lbl_question.hide()
        for b in self.buttons:
            b.hide()

        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        available = False
        for idx, (question, _) in enumerate(self.polls):
            if idx in self.voted_polls:
                continue
            available = True
            block = QPushButton(question)
            block.setCursor(Qt.PointingHandCursor)
            block.setMinimumHeight(80)
            block.setStyleSheet(
                "QPushButton { color: white; background-color: #1a0033;"
                " border:3px solid #9b4dff; border-radius:15px;"
                " font-size:18px; text-align:left; padding:20px; }"
                "QPushButton:hover { background-color:#330066; }"
            )
            block.clicked.connect(partial(self.handle_question, idx, question, self.polls[idx][1]))
            self.list_layout.addWidget(block)

        if not available:
            lbl = QLabel("Vous avez répondu à tous les sondages.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "QLabel { color:white; font-size:20px; font-weight:bold; }"
            )
            self.list_layout.addWidget(lbl)

        self.scroll_area.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        w = WelcomeWindow()
        sys.exit(app.exec_())
    except Exception:
        traceback.print_exc()
