from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-key"

@app.route("/")
def home():
    return redirect(url_for("auth"))

@app.route("/auth", methods=["GET", "POST"])
def auth():
    active_tab = request.args.get("tab", "login")

    if request.method == "POST":
        action = request.form.get("action")

        if action == "login":
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()

            if not email or not password:
                flash("Preencha e-mail e senha para entrar.", "error")
            else:
                session["user_name"] = email.split("@")[0].title()
                return redirect(url_for("dashboard"))

        if action == "register":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()

            if not name or not email or not password:
                flash("Preencha todos os campos para criar sua conta.", "error")
                active_tab = "register"
            else:
                session["user_name"] = name
                return redirect(url_for("dashboard"))

    return render_template("auth.html", active_tab=active_tab)

@app.route("/dashboard")
def dashboard():
    if "user_name" not in session:
        return redirect(url_for("auth"))

    return render_template("dashboard.html", user_name=session.get("user_name", "Usuário"))

@app.route("/transacoes")
def transacoes():
    if "user_name" not in session:
        return redirect(url_for("auth"))

    return render_template("transacoes.html", user_name=session.get("user_name", "Usuário"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth"))

if __name__ == "__main__":
    app.run(debug=True)
