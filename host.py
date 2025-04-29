import json
import sys
import paho.mqtt.client as paho 
from paho import mqtt 
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox


Question1 = {"question": "Pierre aime :",
			"choices": ["Les cailloux", "Les rochers", "Lola", "Les nazis"]
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
client.loop_forever() 
