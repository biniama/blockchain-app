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

#list all blocks we have so far
@app.route('/', methods=['GET','POST'])
def get_blocks():
    blockchain_to_render = [block.to_json() for block in blockchain]

    return render_template('main.html',blocks=blockchain_to_render,user_no=my_port,is_miner=is_miner, balance = get_balances()[my_port],
                           rewards=rewards,peers = [peer['port'] for peer in peers if peer['port'] != my_port])

def add_deposit(to, amount, where_from):
    nonce = 0
    time_current = 0
    while True:
        sha256 = hashlib.sha256()

        sha256.update(str(blockchain[-1].index+1).encode('utf-8'))
        sha256.update(blockchain[-1].hash.encode('utf-8'))
        sha256.update(str(time_current).encode('utf-8'))
        sha256.update(str(where_from).encode('utf-8'))
        sha256.update(str(to).encode('utf-8'))
        sha256.update(str(amount).encode('utf-8'))
        sha256.update(str(nonce).encode('utf-8'))

        hashed_bytes = sha256.hexdigest()

        if hashed_bytes[0:nonce_difficulty] == '0'*nonce_difficulty:
            new_block = Block(index=blockchain[-1].index+1,previous_hash=blockchain[-1].hash,
                                timestamp=time_current, data={'to':to, 'amount':amount, 'from':where_from},nonce=nonce)
            blockchain.append(new_block)
            break
        nonce += 1

def get_balances(new_from=0,new_to=0,new_amount=0):
    balances = {peer['port']: 0 for peer in peers}

    for block in blockchain:
        if block.data['from'] != 0:
            balances[block.data['from']] -= block.data['amount']
        if block.data['to'] != 0:
            balances[block.data['to']] += block.data['amount']

    if new_from != 0:
        balances[new_from] -= new_amount
    if new_to != 0:
        balances[new_to] += new_amount

    return balances

if __name__ == '__main__':
    peers = [{'port': 5001, 'role': 'user'}, {'port': 5002, 'role': 'miner'}, {'port': 5003, 'role': 'miner'}]
    blockchain = [get_genesis_block()]
    rewards = 0
    nonce_difficulty = 4
    add_deposit(to=5001, amount=50, where_from=0000)
    add_deposit(to=5002, amount=50, where_from=0000)
    add_deposit(to=5003, amount=50, where_from=0000)
    my_port = int(os.environ['MY_PORT'])
    is_miner = os.environ['IS_MINER']
    results = []
    socketio.run(app, port=my_port)
