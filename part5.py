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

def broadcast_transaction(miner_port, recipient_port):
    data_to_return = json.dumps({'from':my_port,'to':recipient_port,'amount':10})
    requests.post('http://127.0.0.1:' + str(miner_port) + '/incoming_transaction', data=data_to_return, headers={'Content-Type': 'application/json'} )

@app.route('/', methods=['GET','POST'])
def get_blocks():
    blockchain_to_render = [block.to_json() for block in blockchain]

    if request.method == 'POST':
        recipient = int(request.form['recipient'])
        peers_to_broadcast = [peer['port'] for peer in peers if peer['role'] == 'miner']
        for user_name in peers_to_broadcast:
            thread = threading.Thread(target=broadcast_transaction,args=(user_name,recipient))
            thread.daemon = True
            thread.start()

    return render_template('main.html',blocks=blockchain_to_render,user_no=my_port,is_miner=is_miner, balance = get_balances()[my_port],
                           rewards=rewards,peers = [peer['port'] for peer in peers if peer['port'] != my_port])

@app.route('/incoming_transaction', methods=['POST'])
def process_transaction():
    global nonce_difficulty
    transaction = request.get_json()
    socketio.emit('am_mining')
    time_current = time.time()
    nonce = 0
    while True:
        sha256 = hashlib.sha256()

        sha256.update(str(blockchain[-1].index+1).encode('utf-8'))
        sha256.update(blockchain[-1].hash.encode('utf-8'))
        sha256.update(str(time_current).encode('utf-8'))
        sha256.update(str(transaction['from']).encode('utf-8'))
        sha256.update(str(transaction['to']).encode('utf-8'))
        sha256.update(str(transaction['amount']).encode('utf-8'))
        sha256.update(str(nonce).encode('utf-8'))

        hashed_bytes = sha256.hexdigest()

        if hashed_bytes[0:nonce_difficulty] == '0'*nonce_difficulty:
            time_diff = time.time() - time_current
            socketio.emit('finished_mining',{'took_me': str(time_diff),'resulting_hash': hashed_bytes,'nonce': nonce})
            new_block_dict = {'index':blockchain[-1].index + 1, 'nonce':nonce, 'previous_hash':blockchain[-1].hash, 'timestamp':time_current,'data': transaction}
            my_dict = {'from_port': my_port, 'seconds': str(time_diff), 'block': new_block_dict}
            requests.post('http://127.0.0.1:' + str(transaction['from']) + '/successfull_block',
                          headers={'Content-Type': 'application/json'}, data=json.dumps(my_dict))
            break
        nonce += 1
    return 'OK'


@app.route('/successfull_block', methods=['POST'])
def gather_results():
    incoming_data = request.get_json()
    socketio.emit('proof_of_work_finished',incoming_data)
    results.append(incoming_data)
    if len(results) == len(peers) - 1:
        winning_data = min(results, key=lambda x: x['seconds'])
        winning_port = winning_data['from_port']
        for user_name in [str(peer['port']) for peer in peers]:
            requests.post('http://127.0.0.1:' + user_name + '/add_block', data=json.dumps(winning_data['block']), headers={'Content-Type': 'application/json'})
        requests.post('http://127.0.0.1:' + str(winning_port) + '/get_reward', data=json.dumps({'reward': 1}))
        results.clear()
    return 'OK'

@app.route('/add_block', methods=['POST'])
def update_ledger():
    incoming_data = request.get_json()
    balances = get_balances(new_from=incoming_data['data']['from'],new_to=incoming_data['data']['to'], new_amount=incoming_data['data']['amount'])
    min_balance = min(balances.values())
    if min_balance < 0:
        socketio.emit('insufficient_balance')
    else:
        incoming_data = request.get_json()
        new_block = Block(index=incoming_data['index'],previous_hash=incoming_data['previous_hash'],
                          timestamp=incoming_data['timestamp'], data=incoming_data['data'],nonce=incoming_data['nonce'])
        blockchain.append(new_block)
        socketio.emit('update_ledger', new_block.to_json())
        socketio.emit('update_balance', balances[my_port])


    return 'OK'

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

@app.route('/get_reward', methods=['POST'])
def update_reward():
    global rewards
    rewards += 1
    socketio.emit('update_rewards', rewards)
    return 'OK'

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