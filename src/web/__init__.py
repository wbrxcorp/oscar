import flask

app = flask.Flask("web")
app.config.update(JSON_AS_ASCII=False)

@app.route("/")
def index():
    return "Hello!"

