#!/usr/bin/env python

from flask import Flask, g, request, jsonify, url_for
import os

from ai import Snake

app = Flask(__name__)

SNAKE_ID = os.environ['SNAKE_ID']
PORT = int(os.getenv('PORT', 5000))

ai = Snake(SNAKE_ID)

@app.before_request
def parse_request():
    g.data = request.get_json(force=True, silent=True)
    app.logger.debug('\nREQUEST: %s', g.data)

@app.after_request
def debug_response(response):
    if response.content_type == 'application/json':
        app.logger.debug('\nRESPONSE: %s', response.data)
    return response


@app.route('/')
def whois():
    head_url = url_for('static', filename='chick.gif', _external=True)
    return jsonify({
        'color': '#FFFFFF',
        'head': head_url,
    })


@app.route('/start', methods=['POST'])
def start():
    response = ai.start(g.data)
    return jsonify(response)


@app.route('/move', methods=['POST'])
def move():
    response = ai.move(g.data)
    return jsonify(response)


@app.route('/end', methods=['POST'])
def end():
    response = ai.end(g.data)
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True, port=PORT)
