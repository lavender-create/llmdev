from flask import Flask

app = Flask(__name__)

# ルーティングの基本
@app.route('/')
def index():
    return "Hello, Flask!"

# 複数のルーティングを設定する
@app.route('/about')
def about():
    return "Noriko さんの Flask アプリの About ページです。"


if __name__ == '__main__':
    app.run(debug=True)
