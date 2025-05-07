from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World! 测试服务器工作正常'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)