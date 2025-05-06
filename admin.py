import sys
import json
import time
import subprocess
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame, QLabel, QScrollArea, QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# -------- CONFIG --------
BROKER         = "broker.hivemq.com"
PORT           = 1883
TOPIC_VOTE     = "votinglivepoll/vote"
TOPIC_QUESTION = "votinglivepoll/question"
# ------------------------


class Communicate(QObject):
    new_poll = pyqtSignal(int, str, list)
    new_vote = pyqtSignal(str, str, float)


class VoteResults(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poll Manager")
        self.setStyleSheet("background-color: #1f0036;")
        self.resize(1250, 800)

        self.polls                  = []
        self.vote_counts_list       = []
        self.time_series_total_list = []
        self.series_per_choice_list = []
        self.start_times            = []

        # Signaux
        self.comm = Communicate()
        self.comm.new_poll.connect(self.add_poll)
        self.comm.new_vote.connect(self.record_vote)

        # UI + MQTT
        self.init_ui()
        self.init_mqtt()

        self.show()

    def init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(20)

        left = QVBoxLayout()
        lbl = QLabel("Sélection des sondages")
        lbl.setStyleSheet("QLabel { color: white; font-size: 22px; font-weight: bold; }")
        left.addWidget(lbl)

        self.poll_list_area = QScrollArea()
        self.poll_list_area.setWidgetResizable(True)
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #1a0033; }")
        self.poll_list_layout = QVBoxLayout(frame)
        self.poll_list_layout.setContentsMargins(5, 5, 5, 5)
        self.poll_list_layout.setSpacing(8)
        self.poll_list_layout.addStretch(1)
        self.poll_list_area.setWidget(frame)
        left.addWidget(self.poll_list_area, 1)

        run_btn = QPushButton("Lancer le créateur de sondage")
        run_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        run_btn.setStyleSheet("""
            QPushButton {
                background-color: #8f00ff;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #b84dff;
            }
        """)
        run_btn.clicked.connect(
            lambda: subprocess.Popen([sys.executable, "question_creation.py"])
        )
        left.addWidget(run_btn)

        root.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(15)

        # Question
        self.question_lbl = QLabel("En attente de sélection…")
        self.question_lbl.setStyleSheet(
            "QLabel { color: white; font-size: 22px; font-weight: bold; }"
        )
        self.question_lbl.setWordWrap(True)
        right.addWidget(self.question_lbl)

        content = QHBoxLayout()
        content.setSpacing(20)

        labels_frame = QFrame()
        labels_frame.setStyleSheet("QFrame { background: #2e0055; border-radius:8px; }")
        self.labels_layout = QVBoxLayout(labels_frame)
        self.labels_layout.setContentsMargins(15, 15, 15, 15)
        self.labels_layout.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(labels_frame)
        content.addWidget(scroll, 1)

        self.fig, (self.ax_bar, self.ax_pie) = plt.subplots(
            2, 1, figsize=(4, 5), constrained_layout=True
        )
        self.canvas = FigureCanvas(self.fig)
        content.addWidget(self.canvas, 2)

        right.addLayout(content, 2)

        evo = QHBoxLayout()
        evo.setSpacing(20)

        self.time_fig, self.time_ax = plt.subplots(
            figsize=(4, 2), constrained_layout=True
        )
        self.time_canvas = FigureCanvas(self.time_fig)
        evo.addWidget(self.time_canvas, 1)

        self.choice_fig, self.choice_ax = plt.subplots(
            figsize=(4, 2), constrained_layout=True
        )
        self.choice_canvas = FigureCanvas(self.choice_fig)
        evo.addWidget(self.choice_canvas, 1)

        right.addLayout(evo, 1)

        root.addLayout(right, 3)

    def init_mqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = lambda c, u, f, rc: c.subscribe(
            [(TOPIC_QUESTION, 0), (TOPIC_VOTE, 0)]
        )
        self.client.on_message = self.on_message
        self.client.connect(BROKER, PORT)
        self.client.loop_start()

    def on_message(self, client, userdata, msg):
        data = json.loads(msg.payload.decode())
        if msg.topic == TOPIC_QUESTION:
            q  = data.get("question", "")
            cs = data.get("choices", [])
            idx = len(self.polls)
            self.comm.new_poll.emit(idx, q, cs)
        else:
            q  = data.get("question", "")
            ch = data.get("reponse", "")
            ts = float(data.get("timestamp", time.time()))
            self.comm.new_vote.emit(q, ch, ts)

    def add_poll(self, idx, question, choices):
        self.polls.append({"question": question, "choices": choices})
        self.vote_counts_list.append({c: 0 for c in choices})
        self.time_series_total_list.append([])
        self.series_per_choice_list.append({c: [] for c in choices})
        self.start_times.append(None)

        btn = QPushButton(question)
        btn.setStyleSheet(
            "QPushButton { color:white; background:#1a0033; text-align:left; padding:8px; border:none; }"
            "QPushButton:hover { background:#330066; }"
        )
        btn.clicked.connect(lambda _, i=idx: self.show_results(i))
        self.poll_list_layout.insertWidget(self.poll_list_layout.count() - 1, btn)

    def record_vote(self, question, choice, timestamp):
        for i, p in enumerate(self.polls):
            if p["question"] == question:
                cnts = self.vote_counts_list[i]
                if choice in cnts:
                    cnts[choice] += 1
                    if self.start_times[i] is None:
                        self.start_times[i] = timestamp
                    t_rel = timestamp - self.start_times[i]
                    total = sum(cnts.values())
                    self.time_series_total_list[i].append((t_rel, total))
                    spc = self.series_per_choice_list[i]
                    for c, ser in spc.items():
                        prev = ser[-1][1] if ser else 0
                        ser.append((t_rel, prev + (1 if c == choice else 0)))
                    if hasattr(self, "current_idx") and self.current_idx == i:
                        self.update_ui(i)
                break

    def show_results(self, idx):
        self.current_idx = idx
        self.update_ui(idx)

    def update_ui(self, idx):
        poll   = self.polls[idx]
        counts = self.vote_counts_list[idx]

        self.question_lbl.setText(poll["question"])

        while self.labels_layout.count():
            it = self.labels_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

        for c, v in counts.items():
            lbl = QLabel(f"{c}: {v} votes")
            lbl.setStyleSheet("QLabel { color:white; font-size:16px; }")
            self.labels_layout.addWidget(lbl)
        self.labels_layout.addStretch(1)

        self.update_histogram(counts)
        self.update_pie(counts)
        self.update_time_total(idx)
        self.update_time_per_choice(idx)

    def update_histogram(self, counts):
        self.ax_bar.clear()
        items = [(c,v) for c,v in counts.items() if v>0]
        if items:
            labels, vals = zip(*items)
            bars = self.ax_bar.bar(labels, vals, color='skyblue')
            for b,v in zip(bars, vals):
                self.ax_bar.annotate(str(v),
                                    (b.get_x()+b.get_width()/2, v),
                                    xytext=(0,3), textcoords='offset points',
                                    ha='center')
            self.ax_bar.get_yaxis().set_visible(False)
            for spine in ('left','top','right'):
                self.ax_bar.spines[spine].set_visible(False)
        else:
            self.ax_bar.text(0.5,0.5,"Pas de votes",ha='center',va='center')
            self.ax_bar.set_xticks([]); self.ax_bar.set_yticks([])
        self.canvas.draw()

    def update_pie(self, counts):
        """Met à jour le camembert, ou affiche un message sans axes s'il n'y a pas de votes."""
        choices = [c for c, v in counts.items() if v > 0]
        votes   = [v for v in counts.values()   if v > 0]

        self.ax_pie.clear()

        if choices:
            self.ax_pie.pie(votes, labels=choices, autopct="%1.1f%%")
        else:
            self.ax_pie.text(
                0.5, 0.5,
                "Pas de votes",
                ha="center", va="center",
                fontsize=14, color="black"
            )
            self.ax_pie.set_xticks([])
            self.ax_pie.set_yticks([])

        self.ax_pie.set_facecolor("white")
        self.canvas.draw()


    def update_time_total(self, idx):
        data = self.time_series_total_list[idx]
        self.time_ax.clear()
        if data:
            xs, ys = zip(*data)
            self.time_ax.step(xs, ys, where='post', label='Total')
            self.time_ax.set_xlabel("s")
            self.time_ax.set_ylabel("Total")
            self.time_ax.set_xlim(left=0)
            self.time_ax.legend()
        else:
            self.time_ax.text(
                0.5, 0.5, "Pas de votes",
                ha="center", va="center", fontsize=12
            )
            self.time_ax.set_xticks([]); self.time_ax.set_yticks([])
        self.time_canvas.draw()

    def update_time_per_choice(self, idx):
        spc = self.series_per_choice_list[idx]
        self.choice_ax.clear()
        for c, ser in spc.items():
            if ser:
                xs, ys = zip(*ser)
                self.choice_ax.step(xs, ys, where="post", label=c)
        if any(spc.values()):
            self.choice_ax.legend(fontsize=8)
            self.choice_ax.set_xlabel("s")
            self.choice_ax.set_ylabel("Votes")
            self.choice_ax.set_xlim(left=0)
        else:
            self.choice_ax.text(
                0.5, 0.5, "Pas de votes",
                ha="center", va="center", fontsize=12
            )
            self.choice_ax.set_xticks([]); self.choice_ax.set_yticks([])
        self.choice_canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoteResults()
    sys.exit(app.exec_())
