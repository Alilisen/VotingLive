import sys
import json
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QScrollArea, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# -------- CONFIG --------
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_VOTE = "votinglivepoll/vote"
TOPIC_QUESTION = "votinglivepoll/question"
# ------------------------

class Communicate(QObject):
    new_poll = pyqtSignal(int, str, list)
    new_vote = pyqtSignal(str, str)  # question, choice

class VoteResults(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Résultats des sondages")
        self.setStyleSheet("background-color: #1f0036;")
        self.resize(900, 700)

        # Stockage des sondages et votes
        self.polls = []               # liste de dict {"question": str, "choices": list[str]}
        self.vote_counts_list = []    # liste de dict mapping choice->count
        self.current_poll_idx = None

        # Signaux
        self.comm = Communicate()
        self.comm.new_poll.connect(self.add_poll)
        self.comm.new_vote.connect(self.record_vote)

        # UI
        self.init_ui()
        # MQTT
        self.init_mqtt()

        self.show()

    def init_ui(self):
        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)

        # Section liste des sondages
        self.poll_list_area = QScrollArea()
        self.poll_list_area.setWidgetResizable(True)
        self.poll_list_widget = QFrame()
        self.poll_list_widget.setStyleSheet("QFrame { background: #1a0033; }")
        self.poll_list_layout = QVBoxLayout(self.poll_list_widget)
        self.poll_list_layout.setContentsMargins(10, 10, 10, 10)
        self.poll_list_layout.setSpacing(10)
        self.poll_list_area.setWidget(self.poll_list_widget)
        label = QLabel("Sélectionnez un sondage:")
        label.setStyleSheet("QLabel { color: white; font-size: 20px; font-weight: bold; }")
        self.main_layout.addWidget(label)

        self.main_layout.addWidget(self.poll_list_area)

        # Zone résultats (cachée au départ)
        self.result_widget = QWidget()
        result_layout = QVBoxLayout(self.result_widget)
        result_layout.setSpacing(20)

        # Affichage question
        self.question_lbl = QLabel("")
        self.question_lbl.setAlignment(Qt.AlignCenter)
        self.question_lbl.setWordWrap(True)
        self.question_lbl.setStyleSheet(
            "QLabel { color: white; font-size: 24px; font-weight: bold; padding: 10px; }"
        )
        result_layout.addWidget(self.question_lbl)

        # Layout du contenu: labels et graphiques
        self.content_layout = QHBoxLayout()
        result_layout.addLayout(self.content_layout)

        # Colonne labels
        self.labels_frame = QFrame()
        self.labels_frame.setStyleSheet(
            "QFrame { background-color: #2e0055; border-radius: 10px; }"
        )
        self.labels_layout = QVBoxLayout(self.labels_frame)
        self.labels_layout.setContentsMargins(20, 20, 20, 20)
        self.labels_layout.setSpacing(10)
        self.labels_scroll = QScrollArea()
        self.labels_scroll.setWidgetResizable(True)
        self.labels_scroll.setWidget(self.labels_frame)
        self.content_layout.addWidget(self.labels_scroll, 1)

        # Colonne graphiques
        self.fig, (self.ax_bar, self.ax_pie) = plt.subplots(
            2, 1, figsize=(5, 6), constrained_layout=True
        )
        self.canvas = FigureCanvas(self.fig)
        self.content_layout.addWidget(self.canvas, 2)

        # Bouton retour
        self.back_btn = QPushButton("Retour aux sondages")
        self.back_btn.setStyleSheet(
            "QPushButton { background: #8f00ff; color: white; padding: 8px;"
            " border-radius: 6px; font-size: 16px; }"
            "QPushButton:hover { background: #b84dff; }"
        )
        self.back_btn.clicked.connect(self.show_poll_list)
        result_layout.addWidget(self.back_btn)

        self.result_widget.hide()
        self.main_layout.addWidget(self.result_widget)

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
            q = data.get("question", "")
            choices = data.get("choices", [])
            idx = len(self.polls)
            self.comm.new_poll.emit(idx, q, choices)
        elif msg.topic == TOPIC_VOTE:
            # on récupère question et réponse du payload
            question = data.get("question", "")
            choice   = data.get("reponse", "")
            self.comm.new_vote.emit(question, choice)

    def add_poll(self, idx, question, choices):
        # Stocker
        self.polls.append({"question": question, "choices": choices})
        self.vote_counts_list.append({c: 0 for c in choices})
        # Créer bloc sondage
        btn = QPushButton(question)
        btn.setStyleSheet(
            "QPushButton { color: white; background: #1a0033; padding: 12px;"
            " border: 2px solid #9b4dff; border-radius: 8px; font-size: 18px; text-align: left; }"
            "QPushButton:hover { background: #330066; }"
        )
        btn.clicked.connect(lambda _, i=idx: self.show_results(i))
        self.poll_list_layout.addWidget(btn)

    def record_vote(self, question, choice):
        # Recherche sondage correspondant
        for i, poll in enumerate(self.polls):
            if poll["question"] == question:
                counts = self.vote_counts_list[i]
                if choice in counts:
                    counts[choice] += 1
                    # si affiché, mise à jour
                    if self.current_poll_idx == i:
                        self.update_results_ui(i)
                break

    def show_results(self, idx):
        self.poll_list_area.hide()
        self.result_widget.show()
        self.current_poll_idx = idx
        self.update_results_ui(idx)

    def update_results_ui(self, idx):
        poll = self.polls[idx]
        counts = self.vote_counts_list[idx]
        # Mettre à jour question
        self.question_lbl.setText(poll["question"])
        # Vider anciens labels
        for j in reversed(range(self.labels_layout.count())):
            w = self.labels_layout.itemAt(j).widget()
            if w:
                w.deleteLater()
        # Ajouter labels
        for choice, cnt in counts.items():
            lbl = QLabel(f"{choice}: {cnt} votes")
            lbl.setStyleSheet("QLabel { color: white; font-size: 18px; }")
            self.labels_layout.addWidget(lbl)
        self.labels_layout.addStretch()
        # Mettre à jour graphiques
        self.update_histogram(counts)
        self.update_pie(counts)

    def update_histogram(self, counts):
        self.ax_bar.clear()
        items = [(c, v) for c, v in counts.items() if v > 0]
        if items:
            labels, vals = zip(*items)
            bars = self.ax_bar.bar(labels, vals)
            for bar, v in zip(bars, vals):
                self.ax_bar.annotate(
                    str(v), xy=(bar.get_x()+bar.get_width()/2, v),
                    xytext=(0,3), textcoords='offset points', ha='center', va='bottom'
                )
        else:
            self.ax_bar.text(0.5, 0.5, "Pas de votes", ha='center', va='center', fontsize=12)
            self.ax_bar.set_xticks([])
            self.ax_bar.set_yticks([])
        self.canvas.draw()

    def update_pie(self, counts):
        self.ax_pie.clear()
        items = [(c, v) for c, v in counts.items() if v > 0]
        if items:
            labels, vals = zip(*items)
            self.ax_pie.pie(vals, labels=labels, autopct="%1.1f%%")
        else:
            self.ax_pie.text(0.5, 0.5, "Pas de votes", ha='center', va='center', fontsize=12)
        self.canvas.draw()

    def show_poll_list(self):
        self.result_widget.hide()
        self.poll_list_area.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoteResults()
    sys.exit(app.exec_())
