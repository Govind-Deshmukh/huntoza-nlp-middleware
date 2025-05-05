from flask import Flask
from routes.extract import extract_blueprint

app = Flask(__name__)
app.register_blueprint(extract_blueprint, url_prefix='/api')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
