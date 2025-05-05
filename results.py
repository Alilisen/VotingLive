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
TOPIC_VOTE = "votinglivepoll/vote"
TOPIC_QUESTION = "votinglivepoll/question"
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
        """Initial UI setup"""
        self.layout = QVBoxLayout()

        # Display the question
        self.question = QLabel("En attente de question...")
        self.layout.addWidget(self.question)

        # Set up the figure and canvas for the histogram
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)

        self.setLayout(self.layout)

    def init_mqtt(self):
        """Initialize MQTT client"""
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER, PORT)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        print("Connecté au broker MQTT.")
        client.subscribe(TOPIC_QUESTION)
        client.subscribe(TOPIC_VOTE)

    def on_message(self, client, userdata, msg):
        """MQTT message received callback"""
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
        """Mise à jour de la question et des résultats de vote"""
        self.question.setText(question)

        # Remove old results and reset the list of results
        for vr in self.voteresults:
            self.layout.removeWidget(vr)
            vr.deleteLater()

        self.voteresults = []
        self.vote_counts = {}

        # Initialize the votes to 0 for each choice
        for choice in choices:
            self.vote_counts[choice] = 0

        # Add the labels to the UI
        for choice in choices:
            vr = QLabel(f"{choice}: 0 votes")
            self.voteresults.append(vr)
            self.layout.addWidget(vr)

        # Update the bar chart
        self.update_histogram()

    def update_votes(self, response, increment):
        """Update the vote count"""
        if response in self.vote_counts:
            self.vote_counts[response] += increment
            print(self.vote_counts)

            # Update the text for the choice
            for i in range(len(self.voteresults)):
                if self.voteresults[i].text().startswith(response):
                    self.voteresults[i].setText(f"{response}: {self.vote_counts[response]} votes")

            # Update the bar chart after each vote
            self.update_histogram()

    def update_histogram(self):
        """Update the histogram to reflect the current vote counts"""
        choices = list(self.vote_counts.keys())
        votes = list(self.vote_counts.values())

        # Clear previous data
        self.ax.clear()

        # Plot the new bar chart
        self.ax.bar(choices, votes, color='skyblue')

        # Add labels and title
        self.ax.set_xlabel('Choices')
        self.ax.set_ylabel('Votes')
        self.ax.set_title('Voting Results')

        # Redraw the canvas
        self.canvas.draw()

# Lancer l'application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoteResults()
    sys.exit(app.exec_())
