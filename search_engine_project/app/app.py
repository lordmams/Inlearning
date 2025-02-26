from flask import Flask, render_template, request
from search_engine import search_engine

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get("query")
    results = search_engine(query)
    return render_template("results.html", results=results)

if __name__ == '__main__':
    app.run("0.0.0.0", port=5000, debug=True)