import json
import sys
import paho.mqtt.client as paho
from paho import mqtt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QFrame,
    QPushButton, QMessageBox, QSpacerItem, QSizePolicy, QScrollArea,
    QComboBox, QHBoxLayout
)
from PyQt5.QtGui import QFont, QPalette, QColor, QIntValidator
from PyQt5.QtCore import Qt


def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)

def on_publish(client, userdata, mid, properties=None):
    print("Message Published: " + str(mid))

client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
client.on_connect = on_connect
client.on_publish = on_publish  
client.connect("broker.hivemq.com", 1883)
client.loop_start()

class QuestionCreator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Création de question")
        self.setStyleSheet("background-color: #1f0036;")
        self.resize(700, 600)

        # Garde en mémoire les questions déjà publiées
        self.published_questions = set()

        self.choices_inputs = []
        self.init_ui()
        self.show()

    def init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        scroll_widget = QWidget()
        self.layout = QVBoxLayout(scroll_widget)
        self.layout.setSpacing(25)
        self.layout.setContentsMargins(40, 40, 40, 40)

        # Titre
        title = QLabel("Créer une question")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: bold;
            }
        """)
        self.layout.addWidget(title)

        # Champ question
        self.question_input = self.add_input(self.layout, "Entrez la question...")

        # Combo box pour le nombre de choix
        count_layout = QHBoxLayout()
        label_count = QLabel("Nombre de choix (2-30) :")
        label_count.setStyleSheet("color: white; font-size: 16px;")

        self.choice_count_input = QLineEdit()
        self.choice_count_input.setValidator(QIntValidator(2, 30))
        self.choice_count_input.setPlaceholderText("Ex : 4")
        self.choice_count_input.setStyleSheet("""
            QLineEdit {
                background-color: #2e0055;
                color: white;
                font-size: 16px;
                padding: 8px;
                border: 2px solid #8f00ff;
                border-radius: 8px;
            }
            QLineEdit:focus {
                border: 2px solid #b84dff;
            }
        """)
        self.choice_count_input.textChanged.connect(self.on_choice_count_change)

        count_layout.addWidget(label_count)
        count_layout.addWidget(self.choice_count_input)
        self.layout.addLayout(count_layout)

        # Conteneur pour les champs de choix
        self.choices_container = QVBoxLayout()
        self.layout.addLayout(self.choices_container)

        # Init avec 4 choix par défaut
        self.update_choice_fields(4)

        # Bouton publier
        send_btn = QPushButton("Publier la question")
        send_btn.setMinimumHeight(50)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #8f00ff;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #b84dff;
            }
        """)
        send_btn.clicked.connect(self.publish_question)
        self.layout.addWidget(send_btn)

        scroll.setWidget(scroll_widget)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        self.setLayout(self.layout)

    def add_input(self, layout, placeholder):
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        input_field.setStyleSheet("""
            QLineEdit {
                background-color: #2e0055;
                color: white;
                border: 2px solid #8f00ff;
                border-radius: 10px;
                padding: 10px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border: 2px solid #b84dff;
            }
        """)
        layout.addWidget(input_field)
        return input_field

    def update_choice_fields(self, count):
        # Nettoyer les anciens champs
        for i in reversed(range(self.choices_container.count())):
            widget = self.choices_container.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.choices_inputs = []

        for i in range(count):
            field = QLineEdit()
            field.setPlaceholderText(f"Choix {i + 1}")
            field.setStyleSheet("""
                QLineEdit {
                    background-color: #2e0055;
                    color: white;
                    border: 2px solid #8f00ff;
                    border-radius: 10px;
                    padding: 10px;
                    font-size: 16px;
                }
                QLineEdit:focus {
                    border: 2px solid #b84dff;
                }
            """)
            self.choices_container.addWidget(field)
            self.choices_inputs.append(field)

    def on_choice_count_change(self):
        text = self.choice_count_input.text()
        if text.isdigit():
            count = int(text)
            if 2 <= count <= 30:
                self.update_choice_fields(count)

    def publish_question(self):
        question = self.question_input.text().strip()
        choices = [c.text().strip() for c in self.choices_inputs]

        # Vérifier remplissage
        if not question or any(not c for c in choices):
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Erreur")
            msg.setText("Veuillez remplir tous les champs.")
            msg.setStyleSheet("""
                QLabel { color: white; }
                QPushButton {
                    color: white;
                    background-color: #8f00ff;
                    border-radius: 6px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #b84dff;
                }
            """)
            msg.exec_()
            return

        # Empêcher les doublons
        if question in self.published_questions:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Erreur")
            msg.setText("Cette question a déjà été publiée.")
            msg.setStyleSheet("""
                QLabel { color: white; }
                QPushButton {
                    color: white;
                    background-color: #8f00ff;
                    border-radius: 6px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #b84dff;
                }
            """)
            msg.exec_()
            return

        # Publication
        message = json.dumps({"question": question, "choices": choices})
        client.publish("votinglivepoll/question", message, qos=1)

        # Marquer comme publié
        self.published_questions.add(question)

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Succès")
        msg.setText("La question a été publiée !")
        msg.setStyleSheet("""
            QLabel { color: white; }
            QPushButton {
                color: white;
                background-color: #8f00ff;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #b84dff;
            }
        """)
        msg.exec_()

        self.clear_fields()

    def clear_fields(self):
        self.question_input.clear()
        for c in self.choices_inputs:
            c.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QuestionCreator()
    sys.exit(app.exec_())
