import sys
import json
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QMessageBox, QGridLayout, QLineEdit
)
from PyQt5.QtCore import Qt

# -------- CONFIG --------
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_VOTE = "votinglivepoll/vote"
TOPIC_QUESTION = "votinglivepoll/question"
# ------------------------

class WelcomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bienvenue")
        self.setStyleSheet("background-color: #1f0036; color: white;")
        self.resize(400, 200)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        self.label = QLabel("Entre ton pseudo pour commencer :")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.label)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Pseudo")
        self.input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 16px;
                border: 2px solid #8f00ff;
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.input)

        self.button = QPushButton("Valider")
        self.button.setStyleSheet("""
            QPushButton {
                background-color: #8f00ff;
                color: white;
                font-size: 16px;
                padding: 10px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #aa33ff;
            }
        """)
        self.button.clicked.connect(self.validate)
        layout.addWidget(self.button)

        self.setLayout(layout)

    def validate(self):
        pseudo = self.input.text().strip()
        if not pseudo:
            QMessageBox.warning(self, "Erreur", "Merci d’entrer un pseudo.")
            return
        self.quiz = VotingClient(pseudo)
        self.quiz.show()
        self.close()

class VotingClient(QWidget):
    def __init__(self, pseudo):
        super().__init__()
        self.setWindowTitle("Sondage - Style Jeu TV")
        self.setStyleSheet("background-color: #1f0036;")
        self.pseudo = pseudo
        self.init_ui()
        self.init_mqtt()
        self.resize(800, 600)
        self.show()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setSpacing(40)
        self.layout.setContentsMargins(30, 40, 30, 40)

        self.label = QLabel("En attente de question...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: transparent;
                font-size: 28px;
                font-weight: bold;
            }
        """)
        self.layout.addWidget(self.label)

        grid = QGridLayout()
        grid.setSpacing(30)

        self.buttons = []
        self.choices = []  # Store the choices here
        for i in range(4):
            btn = QPushButton(f"{chr(65 + i)}. Réponse {i + 1}")
            btn.setEnabled(False)
            btn.setMinimumHeight(70)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1f0036;
                    color: #ffffff;
                    border: 3px solid #8f00ff;
                    border-radius: 15px;
                    font-size: 18px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #330066;
                }
            """)
            btn.clicked.connect(lambda _, index=i: self.send_vote(self.choices[index]))
            self.buttons.append(btn)

        grid.addWidget(self.buttons[0], 0, 0)
        grid.addWidget(self.buttons[1], 0, 1)
        grid.addWidget(self.buttons[2], 1, 0)
        grid.addWidget(self.buttons[3], 1, 1)

        self.layout.addLayout(grid)
        self.setLayout(self.layout)

    def init_mqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER, PORT)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("Connecté au broker MQTT.")
        client.subscribe(TOPIC_QUESTION)

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            question = data.get("question", "")
            choix = data.get("choix") or data.get("choices")

            if not question or not choix or len(choix) != 4:
                raise ValueError("Message JSON incomplet.")

            self.label.setText(question)
            self.choices = choix  # Store the choices in the choices list
            for i in range(4):
                self.buttons[i].setText(f"{chr(65 + i)}. {choix[i]}")
                self.buttons[i].setEnabled(True)

        except Exception as e:
            print(f"Erreur de parsing du message : {e}")

    def send_vote(self, choice):
        # Send the actual response text instead of index
        message = {
            "pseudo": self.pseudo,
            "reponse": choice
        }
        self.client.publish(TOPIC_VOTE, json.dumps(message))
        QMessageBox.information(self, "Vote envoyé", f"{self.pseudo}, tu as voté : {choice}")


# Lancer l'application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WelcomeWindow()
    window.show()
    sys.exit(app.exec_())
