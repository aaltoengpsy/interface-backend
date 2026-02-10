import os
import json
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request
from flask_cors import CORS
from rq import Queue
from rq.job import Job
from database_helpers import connect, insert, entry_exists
from chat_helpers import get_completion
from correct_answers import right_choices
from worker import conn
import logging
from logging.config import dictConfig

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'study_data.json')


front_url = os.getenv('FRONTEND_URL')
prolific_code = os.getenv('PROLIFIC_CODE')
prolific_url = os.getenv('PROLIFIC_URL')

app = Flask(__name__)

CORS(app, origins = [front_url])
q = Queue(connection=conn)


@app.route('/chat', methods = ['POST'])
def send_message():
    try:
        req = request.get_json()
        messages = req['messages']

        job = q.enqueue(get_completion, messages)
        return {'jobId': job.id}, 202
    except Exception as e:
        return {'error': str(e)}, 500
    
@app.route('/check_response', methods = ['POST'])
def check_response():
    try:
        req = request.get_json()
        job_id = req['jobId']

        job = Job.fetch(id = job_id, connection = conn)
        
        if job.get_status() == 'finished':
            return {'response': job.latest_result().return_value}, 200
        elif job.get_status() in ['failed', 'canceled', 'stopped']:
            raise InterruptedError('Queue error: task', job.get_status())

        return {'processing': True}, 200
    except Exception as e:
        return {'error': str(e)}, 500

RELEVANT_KEYS = {f'{i}.1' for i in range(4, 24)}

def get_answer(resp_val):
    if isinstance(resp_val, dict):
        return resp_val.get('answer', resp_val)
    return resp_val

def evaluate_answers(tasks):
    correct = 0
    results = {}
    for task_key, task_val in tasks.items():
        responses = task_val.get('responses', {})
        for resp_key, resp_val in responses.items():
            if resp_key in RELEVANT_KEYS:
                answer = get_answer(resp_val)
                is_correct = answer in right_choices
                results[resp_key] = is_correct
                if is_correct:
                    correct += 1
    return correct, results

def load_local_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return []

def save_local_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/save', methods = ['POST'])
def save_data():
    try:
        req = request.get_json()

        correct_count, answer_results = evaluate_answers(req['tasks'])
        total_questions = len(right_choices)

        # Save to local JSON file
        newDataRecord = {
            'participantId': req['participantId'],
            'messages': req['messages'],
            'tasks': req['tasks'],
            'condition': req['condition'],
            'correctAnswers': correct_count,
            'totalQuestions': total_questions,
            'answerResults': answer_results,
            'savedAt': datetime.now().isoformat()
        }

        data = load_local_data()
        data.append(newDataRecord)
        save_local_data(data)

        # MongoDB save disabled for local development
        # db = connect()
        # collection = db['data']
        # mongoRecord = {'_id': req['participantId'], 'messages': req['messages'], 'tasks': req['tasks'], 'condition': req['condition']}
        # insert(mongoRecord, collection)

        return {
            'message': 'OK',
            'prolificCode': prolific_code,
            'prolificUrl': prolific_url,
            'correctAnswers': correct_count,
            'totalQuestions': total_questions
        }, 201
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/check_participation', methods = ['POST'])
def check_participation():
    try:
        req = request.get_json()
        pid = str(req['id'])

        # Check local JSON file instead of MongoDB
        data = load_local_data()
        pid_exists = any(record.get('participantId') == pid for record in data)
        if pid_exists:
            return {'participated': True}, 302

        return {'participated': False}, 204
    except Exception as e:
        return {'error': str(e)}, 500