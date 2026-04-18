import os
from datetime import date, timedelta
from urllib.parse import quote_plus
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "replace-with-a-secure-key")

db_user = os.getenv("DB_USER", "root")
db_password = quote_plus(os.getenv("DB_PASSWORD", ""))
db_host = os.getenv("DB_HOST", "127.0.0.1")
db_port = os.getenv("DB_PORT", "3306")
db_name = os.getenv("DB_NAME", "financetrack")
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


def get_default_user():
    user = User.query.first()
    if user is None:
        user = User(name="Usuário Demo", email="demo@financetrack.local")
        db.session.add(user)
        db.session.commit()
    return user


class User(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False, unique=True)
    transactions = db.relationship("Transaction", back_populates="user")


class Category(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    transactions = db.relationship("Transaction", back_populates="category")


class Transaction(db.Model):
    __tablename__ = "transacoes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(260), nullable=True)

    user = db.relationship("User", back_populates="transactions")
    category = db.relationship("Category", back_populates="transactions")


def create_default_categories():
    default_names = ["Salário", "Lazer", "Alimentação", "Transporte", "Saúde", "Serviços", "Moradia"]
    existing = {category.name for category in Category.query.all()}
    for name in default_names:
        if name not in existing:
            db.session.add(Category(name=name))
    db.session.commit()




def get_current_user():
    if "user_id" not in session:
        user = get_default_user()
        session["user_id"] = user.id
        session["user_name"] = user.name
        return user

    user = User.query.get(session["user_id"])
    if user is None:
        user = get_default_user()
        session["user_id"] = user.id
        session["user_name"] = user.name
    return user


def build_dashboard_data(user):
    today = date.today()
    month_start = today.replace(day=1)
    month_end = month_start + timedelta(days=29)
    transactions = (
        Transaction.query.filter(
            Transaction.user_id == user.id,
            Transaction.date >= month_start,
            Transaction.date <= month_end,
        )
        .order_by(Transaction.date)
        .all()
    )

    labels = [f"{day:02d}" for day in range(1, 31)]
    incomes_by_day = [0.0] * 30
    expenses_by_day = [0.0] * 30

    for tx in transactions:
        index = tx.date.day - 1
        if 0 <= index < 30:
            if tx.type == "income":
                incomes_by_day[index] += tx.amount
            else:
                expenses_by_day[index] += tx.amount

    balance_by_day = []
    balance_total = 0.0
    for i in range(30):
        balance_total += incomes_by_day[i] - expenses_by_day[i]
        balance_by_day.append(round(balance_total, 2))

    incomes_total = sum(incomes_by_day)
    expenses_total = sum(expenses_by_day)

    category_totals = {}
    for tx in transactions:
        if tx.type == "expense":
            category_totals[tx.category.name] = category_totals.get(tx.category.name, 0.0) + tx.amount

    category_labels = list(category_totals.keys())
    category_values = [round(value, 2) for value in category_totals.values()]
    category_breakdown = [
        {"label": name, "value": round(value, 2)}
        for name, value in category_totals.items()
    ]
    category_total = round(sum(category_values), 2)

    recent_transactions = (
        Transaction.query.filter_by(user_id=user.id)
        .order_by(Transaction.date.desc())
        .limit(5)
        .all()
    )

    return {
        "labels": labels,
        "incomes": [round(value, 2) for value in incomes_by_day],
        "expenses": [round(value, 2) for value in expenses_by_day],
        "balances": balance_by_day,
        "incomes_total": round(incomes_total, 2),
        "expenses_total": round(expenses_total, 2),
        "balance_total": round(incomes_total - expenses_total, 2),
        "category_labels": category_labels,
        "category_values": category_values,
        "category_breakdown": category_breakdown,
        "category_total": category_total,
        "recent_transactions": recent_transactions,
    }


def build_transaction_query(user):
    query = Transaction.query.filter(Transaction.user_id == user.id)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    category_id = request.args.get("category_id")
    tipo = request.args.get("tipo")
    min_value = request.args.get("min_value")
    max_value = request.args.get("max_value")

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if category_id and category_id.isdigit():
        query = query.filter(Transaction.category_id == int(category_id))
    if tipo in ["income", "expense"]:
        query = query.filter(Transaction.type == tipo)
    if min_value:
        try:
            query = query.filter(Transaction.amount >= float(min_value.replace(',', '.')))
        except ValueError:
            pass
    if max_value:
        try:
            query = query.filter(Transaction.amount <= float(max_value.replace(',', '.')))
        except ValueError:
            pass

    return query.order_by(Transaction.date.desc())


@app.route("/transacoes/adicionar", methods=["POST"])
def adicionar_transacao():
    user = get_current_user()
    category_id = request.form.get("category_id")
    tipo = request.form.get("tipo")
    amount_text = request.form.get("amount", "").strip().replace(',', '.')
    date_text = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    if not category_id or not tipo or not amount_text or not date_text:
        flash("Preencha todos os campos obrigatórios para adicionar a transação.", "error")
        return redirect(url_for("transacoes"))

    try:
        amount = float(amount_text)
    except ValueError:
        flash("Informe um valor válido para a transação.", "error")
        return redirect(url_for("transacoes"))

    category = Category.query.get(category_id)
    if category is None:
        flash("Selecione uma categoria válida.", "error")
        return redirect(url_for("transacoes"))

    try:
        tx_date = date.fromisoformat(date_text)
    except ValueError:
        flash("Informe uma data válida para a transação.", "error")
        return redirect(url_for("transacoes"))

    transaction = Transaction(
        user_id=user.id,
        category_id=category.id,
        type=tipo,
        amount=amount,
        date=tx_date,
        description=description,
    )
    db.session.add(transaction)
    db.session.commit()

    flash("Transação adicionada com sucesso.", "success")
    return redirect(url_for("transacoes"))


@app.route("/")
def home():
    return redirect(url_for("dashboard"))


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
    user = get_current_user()
    dashboard_data = build_dashboard_data(user)
    return render_template(
        "dashboard.html",
        user_name=user.name,
        dashboard_data=dashboard_data,
    )


@app.route("/transacoes")
def transacoes():
    user = get_current_user()
    categories = Category.query.order_by(Category.name).all()
    query = build_transaction_query(user)
    transactions = query.all()
    return render_template(
        "transacoes.html",
        user_name=user.name,
        categories=categories,
        transactions=transactions,
        filters={
            "start_date": request.args.get("start_date", ""),
            "end_date": request.args.get("end_date", ""),
            "category_id": request.args.get("category_id", ""),
            "tipo": request.args.get("tipo", "all"),
            "min_value": request.args.get("min_value", ""),
            "max_value": request.args.get("max_value", ""),
        },
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth"))


with app.app_context():
    db.create_all()
    user = get_default_user()
    create_default_categories()


if __name__ == "__main__":
    app.run(debug=True)
