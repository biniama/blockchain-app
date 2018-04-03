from flask import Flask, render_template, request
from flask_socketio import SocketIO
import os
import requests
import hashlib
import threading
import time
import json


app = Flask(__name__)
socketio = SocketIO(app)


class Block:
    def __init__(self, index, previous_hash, timestamp, data, nonce):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.nonce = nonce

        sha256 = hashlib.sha256()

        sha256.update(str(index).encode('utf-8'))
        sha256.update(previous_hash.encode('utf-8'))
        sha256.update(str(timestamp).encode('utf-8'))
        sha256.update(str(data['from']).encode('utf-8'))
        sha256.update(str(data['to']).encode('utf-8'))
        sha256.update(str(data['amount']).encode('utf-8'))
        sha256.update(str(nonce).encode('utf-8'))
        self.hash = sha256.hexdigest()


    def to_json(self):
        return {'index':self.index, 'previous_hash':self.previous_hash, 'timestamp':self.timestamp,
                'data': self.data, 'hash':self.hash, 'nonce':self.nonce }

def get_genesis_block():
    return Block(index=0, previous_hash='0', timestamp=0, data={'from':0000,'to':0000,'amount':0000},
                 nonce=0)

@app.route('/', methods=['GET','POST'])
def get_blocks():
    blockchain_to_render = [block.to_json() for block in blockchain]

    return render_template('main.html',blocks=blockchain_to_render,user_no=my_port,is_miner=is_miner,
                           peers = [peer['port'] for peer in peers if peer['port'] != my_port])


if __name__ == '__main__':
    peers = [{'port': 5001, 'role': 'user'}, {'port': 5002, 'role': 'miner'}, {'port': 5003, 'role': 'miner'}]
    blockchain = [get_genesis_block()]
    nonce_difficulty = 4
    my_port = int(os.environ['MY_PORT'])
    is_miner = os.environ['IS_MINER']
    results = []
    socketio.run(app, port=my_port)
