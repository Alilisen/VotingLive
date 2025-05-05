import sys
import json
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel
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
        self.setWindowTitle("Vote Results")
        self.init_ui()
        self.init_mqtt()
        self.show()

        self.vote_counts = {}
        self.voteresults = []

        self.comm = Communicate()
        self.comm.update_vote_signal.connect(self.update_votes)
        self.comm.update_question_signal.connect(self.update_question)

    def init_ui(self):
        self.layout = QVBoxLayout()

        # Display the question
        self.question = QLabel("En attente de question...")
        self.layout.addWidget(self.question)

        self.fig, (self.ax, self.ax_pie) = plt.subplots(1, 2, figsize=(10, 5))
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)

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
        client.subscribe(TOPIC_VOTE)

    def on_message(self, client, userdata, msg):
        if msg.topic == TOPIC_QUESTION:
            data = json.loads(msg.payload.decode())
            question = data.get("question", "")
            choices = data.get("choices")
            
            self.comm.update_question_signal.emit(question, choices)

        elif msg.topic == TOPIC_VOTE:
            vote_data = json.loads(msg.payload.decode())
            response = vote_data.get("reponse")
            self.comm.update_vote_signal.emit(response, 1)

    def update_question(self, question, choices):
        self.question.setText(question)

        for vr in self.voteresults:
            self.layout.removeWidget(vr)
            vr.deleteLater()

        self.voteresults = []
        self.vote_counts = {}

        for choice in choices:
            self.vote_counts[choice] = 0

        for choice in choices:
            vr = QLabel(f"{choice}: 0 votes")
            self.voteresults.append(vr)
            self.layout.addWidget(vr)

        self.update_histogram()
        self.update_pie_chart()

    def update_votes(self, response, increment):
        if response in self.vote_counts:
            self.vote_counts[response] += increment
            print(self.vote_counts)

            for i in range(len(self.voteresults)):
                if self.voteresults[i].text().startswith(response):
                    self.voteresults[i].setText(f"{response}: {self.vote_counts[response]} votes")

            self.update_histogram()
            self.update_pie_chart()

    def update_histogram(self):
        choices = list(self.vote_counts.keys())
        votes = list(self.vote_counts.values())

        filtered_choices = [choice for choice, vote in zip(choices, votes) if vote > 0]
        filtered_votes = [vote for vote in votes if vote > 0]

        self.ax.clear()

        if filtered_choices:
            self.ax.bar(filtered_choices, filtered_votes, color='skyblue')

            self.ax.set_xlabel('Choices')
            self.ax.set_ylabel('Votes')
            self.ax.set_title('Voting Results')
        else:
            self.ax.set_title('No votes yet')
            self.ax.set_xlabel('Choices')
            self.ax.set_ylabel('Votes')

        self.canvas.draw()

    def update_pie_chart(self):
        filtered_choices = [choice for choice, vote in self.vote_counts.items() if vote > 0]
        filtered_votes = [vote for vote in self.vote_counts.values() if vote > 0]

        self.ax_pie.clear()

        if filtered_choices:
            self.ax_pie.pie(filtered_votes, labels=filtered_choices, autopct='%1.1f%%', colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
            self.ax_pie.set_title('Voting Results')
        else:
            self.ax_pie.set_title('No votes yet')

        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoteResults()
    sys.exit(app.exec_())
