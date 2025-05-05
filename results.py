import sys
import json
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# -------- CONFIG --------
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_VOTE = "votinglivepollbis/vote"
TOPIC_QUESTION = "votinglivepollbis/question"
# ------------------------

class Communicate(QObject):
    update_vote_signal = pyqtSignal(str, int)
    update_question_signal = pyqtSignal(str, list)

class VoteResults(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Résultats du sondage")
        self.setStyleSheet("background-color: #1f0036;")
        self.resize(900, 700)

        # données
        self.vote_counts = {}
        self.voteresults = []

        # signaux
        self.comm = Communicate()
        self.comm.update_vote_signal.connect(self.update_votes)
        self.comm.update_question_signal.connect(self.update_question)

        # UI + MQTT
        self.init_ui()
        self.init_mqtt()
        self.show()

    def init_ui(self):
        # Layout principal
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # Label question
        self.question = QLabel("En attente de question…")
        self.question.setAlignment(Qt.AlignCenter)
        self.question.setWordWrap(True)
        self.question.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        self.main_layout.addWidget(self.question)

        # Conteneur deux colonnes
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(30)

        # Colonne de gauche : cadre + scroll area
        self.labels_frame = QFrame()
        self.labels_frame.setStyleSheet("""
            QFrame { background-color: #2e0055; border-radius: 10px; }
        """)
        self.labels_layout = QVBoxLayout()
        self.labels_layout.setContentsMargins(20, 20, 20, 20)
        self.labels_layout.setSpacing(10)
        self.labels_frame.setLayout(self.labels_layout)

        # Emballer dans un QScrollArea
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.labels_frame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #2e0055;
                width: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #8f00ff;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                height: 0px;
            }
        """)
        self.content_layout.addWidget(self.scroll_area, 1)

        # Colonne de droite : graphiques empilés verticalement
        self.fig, (self.ax_bar, self.ax_pie) = plt.subplots(
            2, 1, figsize=(6, 8), constrained_layout=True
        )
        self.canvas = FigureCanvas(self.fig)
        self.content_layout.addWidget(self.canvas, 2)

        self.main_layout.addLayout(self.content_layout)
        self.setLayout(self.main_layout)

    def init_mqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER, PORT)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe(TOPIC_QUESTION)
        client.subscribe(TOPIC_VOTE)

    def on_message(self, client, userdata, msg):
        data = json.loads(msg.payload.decode())
        if msg.topic == TOPIC_QUESTION:
            question = data.get("question", "")
            choices  = data.get("choices", [])
            self.comm.update_question_signal.emit(question, choices)
        else:
            response = data.get("reponse", "")
            self.comm.update_vote_signal.emit(response, 1)

    def update_question(self, question, choices):
        # Met à jour le texte de la question
        self.question.setText(question)

        # Efface anciens labels (widgets + spacers)
        while self.labels_layout.count():
            item = self.labels_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.voteresults.clear()
        self.vote_counts.clear()

        # Crée nouveaux compteurs et labels (taille fixe + stretch en bas)
        from PyQt5.QtWidgets import QSizePolicy
        for choice in choices:
            self.vote_counts[choice] = 0
            lbl = QLabel(f"{choice}: 0 votes")
            lbl.setStyleSheet("QLabel { color: white; font-size: 18px; padding: 5px; }")
            lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.voteresults.append(lbl)
            self.labels_layout.addWidget(lbl)
        self.labels_layout.addStretch(1)

        # Mise à jour graphiques
        self.update_histogram()
        self.update_pie_chart()

    def update_votes(self, response, inc):
        if response in self.vote_counts:
            self.vote_counts[response] += inc
            # Met à jour label textuel
            for lbl in self.voteresults:
                if lbl.text().startswith(response):
                    lbl.setText(f"{response}: {self.vote_counts[response]} votes")
            # Mise à jour graphiques
            self.update_histogram()
            self.update_pie_chart()

    def update_histogram(self):
        # Filtre votes > 0
        choices = [c for c, v in self.vote_counts.items() if v > 0]
        votes   = [v for v in self.vote_counts.values()  if v > 0]

        self.ax_bar.clear()
        if choices:
            bars = self.ax_bar.bar(choices, votes, color='skyblue')
            self.ax_bar.set_title("Nombres de votes", color="black")
            self.ax_bar.set_xlabel("Choix", color="black")
            # faire disparaître l'axe des ordonnées
            self.ax_bar.yaxis.set_visible(False)
            # supprimer le cadre complet autour de l'histogramme
            self.ax_bar.set_frame_on(False)
            for bar, val in zip(bars, votes):
                self.ax_bar.annotate(
                    str(val),
                    xy=(bar.get_x() + bar.get_width()/2, val),
                    xytext=(0, 3), textcoords='offset points',
                    ha='center', va='bottom',
                    color='black', fontsize=10
                )
        else:
            self.ax_bar.text(0.5, 0.5, "Pas de votes",
                             ha="center", va="center", fontsize=12)
            self.ax_bar.set_xticks([])
            self.ax_bar.set_yticks([])

        self.ax_bar.set_facecolor("white")
        self.canvas.draw()

    def update_pie_chart(self):
        choices = [c for c, v in self.vote_counts.items() if v > 0]
        votes   = [v for v in self.vote_counts.values()  if v > 0]

        self.ax_pie.clear()
        if choices:
            self.ax_pie.pie(
                votes,
                labels=choices,
                autopct="%1.1f%%"
            )
            self.ax_pie.set_title("Répartition", color="black")
        else:
            self.ax_pie.text(0.5, 0.5, "Pas de votes",
                              ha="center", va="center", fontsize=12)

        self.ax_pie.set_facecolor("white")
        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoteResults()
    sys.exit(app.exec_())
