from flask import Flask, render_template, request, redirect, url_for 

app = Flask(__name__)

# ファイルからTODOリストを読み込む関数
def load_todos():
    try:
        with open("todos.txt", "r", encoding="utf-8") as file:
            todos = [line.strip() for line in file]
    except FileNotFoundError:
        todos = []
    return todos

# TODOリストをファイルに保存する関数
def save_todos(todos):
    with open("todos.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(todos))

@app.route("/", methods=["GET", "POST"])
def index():
    todos = load_todos()
    if request.method == "POST":
        new_todo = request.form.get("todo")
        if new_todo:
            todos.append(new_todo)
            save_todos(todos)
        return redirect(url_for("index"))
    return render_template("index.html", todos=todos)

# 🔽🔽 ここが削除機能の完成コード 🔽🔽
@app.route("/delete/<int:todo_id>")
def delete(todo_id):
    todos = load_todos()   # 現在のTODOを読み込み

    # 指定IDが範囲内かチェックして削除
    if 0 <= todo_id < len(todos):
        del todos[todo_id]
        save_todos(todos)  # 新しいリストを保存

    return redirect(url_for("index"))
# 🔼🔼 ここまでが削除機能 🔼🔼

if __name__ == "__main__":
    app.run(debug=True)

