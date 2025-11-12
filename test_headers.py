from flask import Flask, request
from werkzeug.serving import run_simple

app = Flask(__name__)

@app.route('/test')
def test():
    return {
        'lower': request.headers.get('telegram_id'),
        'title': request.headers.get('Telegram-Id'),
        'upper': request.headers.get('TELEGRAM_ID'),
        'original': request.headers.get('telegram_id'),
        'all_headers': dict(request.headers)
    }

if __name__ == '__main__':
    print("Starting test server on port 5001...")
    run_simple('0.0.0.0', 5001, app)
