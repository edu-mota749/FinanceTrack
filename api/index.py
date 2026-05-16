from app import app


@app.route("/favicon.ico")
def favicon():
    return "", 204
