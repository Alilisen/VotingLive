import json
import sys
import paho.mqtt.client as paho 
from paho import mqtt 
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QFrame,
    QPushButton, QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QComboBox, QHBoxLayout



Question1 = {"question": "Pierre aime :",
			"choices": ["Les cailloux", "Les rochers", "Lola", "Rien"]
}

Q1 = json.dumps(Question1) 

def on_connect(client, userdata, flags, rc, properties=None): 
	print("CONNACK received with code %s." % rc) 
def on_publish(client, userdata, mid, properties=None): 
	print("Message Published: " + str(mid)) 

client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5) 
client.on_connect = on_connect 
client.on_publish = on_publish  
client.connect("broker.hivemq.com", 1883) 
client.publish("votinglivepoll/question", Q1, qos=1) 
 
class QuestionCreator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Créateur de question - Style Jeu TV")
        self.setStyleSheet("background-color: #1f0036;")
        self.resize(700, 600)
        self.choices_inputs = []
        self.init_ui()
        self.show()

    def init_ui(self):
        self.layout = QVBoxLayout()
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
        combo_layout = QHBoxLayout()
        label_combo = QLabel("Nombre de choix :")
        label_combo.setStyleSheet("color: white; font-size: 16px;")
        self.choice_count_combo = QComboBox()
        self.choice_count_combo.setStyleSheet("background-color: #2e0055; color: white; font-size: 16px;")
        self.choice_count_combo.addItems([str(i) for i in range(2, 7)])
        self.choice_count_combo.currentIndexChanged.connect(self.update_choice_fields)

        combo_layout.addWidget(label_combo)
        combo_layout.addWidget(self.choice_count_combo)
        self.layout.addLayout(combo_layout)

        # Conteneur pour les champs de choix
        self.choices_container = QVBoxLayout()
        self.layout.addLayout(self.choices_container)

        # Init avec 4 choix
        self.update_choice_fields(2)  # par défaut 2 + index = 4

        # Bouton publier
        send_btn = QPushButton("📤 Publier la question")
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

    def update_choice_fields(self, index):
        # Nettoyer les anciens champs
        for i in reversed(range(self.choices_container.count())):
            widget = self.choices_container.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.choices_inputs = []
        count = int(self.choice_count_combo.currentText())

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
    
    def publish_question(self):
        question = self.question_input.text().strip()
        choices = [c.text().strip() for c in self.choices_inputs]

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

        message = json.dumps({"question": question, "choices": choices})
        client.publish("votinglivepoll/question", message, qos=1)

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