import os
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

def count_correct_answers(tasks):
    correct = 0
    for task_key, task_val in tasks.items():
        responses = task_val.get('responses', {})
        for resp_key, resp_val in responses.items():
            if resp_key.endswith('.1') and resp_val in right_choices:
                correct += 1
    return correct

@app.route('/save', methods = ['POST'])
def save_data():
    try:
        req = request.get_json()
        newDataRecord = {
            '_id': req['participantId'],
            'messages': req['messages'],
            'tasks': req['tasks'],
            'condition': req['condition']
        }

        db = connect()
        collection = db['data']

        correct_count = count_correct_answers(req['tasks'])
        total_questions = len(right_choices)

        insertSuccess = insert(newDataRecord, collection)
        if insertSuccess == True:
            return {
                'message': 'OK',
                'prolificCode': prolific_code,
                'prolificUrl': prolific_url,
                'correctAnswers': correct_count,
                'totalQuestions': total_questions
            }, 201

        return {'message': 'Record already exists'}, 304
    except Exception as e:
        return {'error': str(e)}, 500
    
@app.route('/check_participation', methods = ['POST'])
def check_participation():
    try:
        req = request.get_json()
        db = connect()
        collection = db['data']

        pid_exists = entry_exists(str(req['id']), collection)
        if pid_exists == True:
            return {'participated': True}, 302

        return {'participated': False}, 204
    except Exception as e:
        return {'error': str(e)}, 500