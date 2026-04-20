import io
import calendar
import os
from datetime import date, datetime, timedelta
from functools import wraps
from urllib.parse import quote_plus
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, case
from dotenv import load_dotenv
from fpdf import FPDF
from werkzeug.security import generate_password_hash, check_password_hash

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
        
        # Criar autenticação padrão
        auth = Autenticacao(
            usuario_id=user.id,
            email="demo@financetrack.local",
            senha_hash=generate_password_hash("password123")
        )
        db.session.add(auth)
        db.session.commit()
    return user


class User(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False, unique=True)
    transactions = db.relationship("Transaction", back_populates="user")
    categories = db.relationship("Category", back_populates="user")


class Category(db.Model):
    __tablename__ = "categorias"
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_categoria_usuario_nome"),)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    user = db.relationship("User", back_populates="categories")
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


class Relatorio(db.Model):
    __tablename__ = "relatorios"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    periodo_inicio = db.Column(db.Date, nullable=False)
    periodo_fim = db.Column(db.Date, nullable=False)
    total_receitas = db.Column(db.Float, nullable=False)
    total_despesas = db.Column(db.Float, nullable=False)
    saldo = db.Column(db.Float, nullable=False)
    arquivo_nome = db.Column(db.String(200), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    usuario = db.relationship("User", backref="relatorios")


class Autenticacao(db.Model):
    __tablename__ = "autenticacao"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, unique=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario = db.relationship("User", backref="autenticacao_rel")


def format_periodo_por_extenso(data_obj):
    meses = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }
    return f"{meses[data_obj.month]} {data_obj.year}"


def gerar_pdf_relatorio(user, transactions, period_start, period_end, arquivo_nome=None):
    incomes_total = sum(tx.amount for tx in transactions if tx.type == "income")
    expenses_total = sum(tx.amount for tx in transactions if tx.type == "expense")
    balance_total = incomes_total - expenses_total

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Relatório Financeiro", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Usuário: {user.name}", ln=True)
    pdf.cell(0, 8, f"Período: {period_start.strftime('%d/%m/%Y')} - {period_end.strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 8, f"Gerado em: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC", ln=True)
    pdf.ln(6)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Resumo", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"Receitas: R$ {incomes_total:.2f}".replace('.', ','), ln=True)
    pdf.cell(0, 6, f"Despesas: R$ {expenses_total:.2f}".replace('.', ','), ln=True)
    pdf.cell(0, 6, f"Saldo: R$ {balance_total:.2f}".replace('.', ','), ln=True)
    pdf.ln(8)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Transações", ln=True)
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(30, 7, "Data", 1, 0, 'C', True)
    pdf.cell(50, 7, "Categoria", 1, 0, 'C', True)
    pdf.cell(30, 7, "Tipo", 1, 0, 'C', True)
    pdf.cell(35, 7, "Valor", 1, 0, 'C', True)
    pdf.cell(0, 7, "Descrição", 1, 1, 'C', True)
    pdf.set_font("Arial", "", 10)

    for tx in transactions:
        pdf.cell(30, 7, tx.date.strftime('%d/%m/%Y'), 1)
        pdf.cell(50, 7, tx.category.name[:30], 1)
        pdf.cell(30, 7, "Receita" if tx.type == "income" else "Despesa", 1)
        pdf.cell(35, 7, f"R$ {tx.amount:.2f}".replace('.', ','), 1)
        pdf.multi_cell(0, 7, tx.description or "", 1)

    if arquivo_nome is None:
        arquivo_nome = f"Relatório {format_periodo_por_extenso(period_start)}.pdf"
    return arquivo_nome, pdf.output(dest='S').encode('latin1')


def get_monthly_report_cards(user):
    month_rows = (
        db.session.query(
            db.func.year(Transaction.date).label("year"),
            db.func.month(Transaction.date).label("month"),
        )
        .filter(Transaction.user_id == user.id)
        .group_by(db.func.year(Transaction.date), db.func.month(Transaction.date))
        .order_by(db.desc(db.func.year(Transaction.date)), db.desc(db.func.month(Transaction.date)))
        .all()
    )

    existing_reports = {
        (rel.periodo_inicio.year, rel.periodo_inicio.month): rel
        for rel in Relatorio.query.filter_by(usuario_id=user.id).all()
    }

    report_cards = []
    for month_row in month_rows:
        year = int(month_row.year)
        month = int(month_row.month)
        period_start = date(year, month, 1)
        period_end = date(year, month, calendar.monthrange(year, month)[1])
        existing = existing_reports.get((year, month))
        arquivo_nome = (
            existing.arquivo_nome
            if existing
            else f"Relatório {format_periodo_por_extenso(period_start)}.pdf"
        )

        report_cards.append({
            "year": year,
            "month": month,
            "label": f"Relatório {format_periodo_por_extenso(period_start)}",
            "subtitle": f"Transações de {format_periodo_por_extenso(period_start)}",
            "arquivo_nome": arquivo_nome,
            "periodo_inicio": period_start,
            "periodo_fim": period_end,
            "relatorio_id": existing.id if existing else None,
        })

    return report_cards


def create_default_categories():
    default_names = ["Salário", "Lazer", "Alimentação", "Transporte", "Saúde", "Serviços", "Moradia"]
    existing = {category.name for category in Category.query.filter(Category.user_id.is_(None)).all()}
    for name in default_names:
        if name not in existing:
            db.session.add(Category(name=name, user_id=None))
    db.session.commit()


def ensure_category_schema():
    """Ensure the categorias table has user_id column and proper constraints."""
    try:
        inspector = db.inspect(db.engine)
        columns = [column["name"] for column in inspector.get_columns("categorias")]
        if "user_id" not in columns:
            db.session.execute(text("ALTER TABLE categorias ADD COLUMN user_id INT NULL"))
            db.session.commit()
    except Exception:
        pass


def cleanup_test_categories():
    """Remove test categories that have no transactions."""
    try:
        for category in Category.query.filter(Category.name.ilike("%teste%")).all():
            if not category.transactions:
                db.session.delete(category)
        db.session.commit()
    except Exception:
        pass




def get_current_user():
    if "user_id" not in session:
        return None

    user = User.query.get(session["user_id"])
    if user is None:
        session.clear()
        return None
    return user


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth"))
        user = User.query.get(session["user_id"])
        if user is None:
            session.clear()
            return redirect(url_for("auth"))
        return view(*args, **kwargs)
    return wrapped_view


def build_dashboard_data(user, period="month", selected_month=None, selected_year=None):
    today = date.today()
    month_labels_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

    if period == "year":
        try:
            year = int(selected_year)
        except (TypeError, ValueError):
            year = today.year
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        labels = month_labels_pt
        period_description = f"Ano {year}"
        transactions = (
            Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
            )
            .order_by(Transaction.date)
            .all()
        )
        incomes_by_period = [0.0] * 12
        expenses_by_period = [0.0] * 12
        for tx in transactions:
            index = tx.date.month - 1
            if tx.type == "income":
                incomes_by_period[index] += tx.amount
            else:
                expenses_by_period[index] += tx.amount

    elif period == "all":
        transactions = (
            Transaction.query.filter(Transaction.user_id == user.id)
            .order_by(Transaction.date)
            .all()
        )
        if transactions:
            start_year = transactions[0].date.year
            end_year = today.year
            labels = [str(year) for year in range(start_year, end_year + 1)]
            incomes_by_period = [0.0] * len(labels)
            expenses_by_period = [0.0] * len(labels)
            for tx in transactions:
                index = tx.date.year - start_year
                if tx.type == "income":
                    incomes_by_period[index] += tx.amount
                else:
                    expenses_by_period[index] += tx.amount
            period_description = "Geral"
        else:
            labels = [str(today.year)]
            incomes_by_period = [0.0]
            expenses_by_period = [0.0]
            period_description = "Geral"

    else:
        try:
            year, month = map(int, selected_month.split("-")) if selected_month else (today.year, today.month)
        except (TypeError, ValueError):
            year = today.year
            month = today.month
        days = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, days)
        labels = [f"{day:02d}" for day in range(1, days + 1)]
        period_description = f"{month_labels_pt[month - 1]} {year}"
        transactions = (
            Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
            )
            .order_by(Transaction.date)
            .all()
        )
        incomes_by_period = [0.0] * days
        expenses_by_period = [0.0] * days
        for tx in transactions:
            index = tx.date.day - 1
            if 0 <= index < days:
                if tx.type == "income":
                    incomes_by_period[index] += tx.amount
                else:
                    expenses_by_period[index] += tx.amount

    balance_by_period = []
    balance_total = 0.0
    for i in range(len(incomes_by_period)):
        balance_total += incomes_by_period[i] - expenses_by_period[i]
        balance_by_period.append(round(balance_total, 2))

    incomes_total = sum(incomes_by_period)
    expenses_total = sum(expenses_by_period)

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
        "incomes": [round(value, 2) for value in incomes_by_period],
        "expenses": [round(value, 2) for value in expenses_by_period],
        "balances": balance_by_period,
        "incomes_total": round(incomes_total, 2),
        "expenses_total": round(expenses_total, 2),
        "balance_total": round(incomes_total - expenses_total, 2),
        "category_labels": category_labels,
        "category_values": category_values,
        "category_breakdown": category_breakdown,
        "category_total": category_total,
        "recent_transactions": recent_transactions,
        "period_description": period_description,
    }


def build_transaction_query(user):
    query = Transaction.query.filter(Transaction.user_id == user.id)
    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()
    category_ids = request.args.getlist("category_id")
    tipo = request.args.get("tipo")
    min_value = (request.args.get("min_value") or "").strip()
    max_value = (request.args.get("max_value") or "").strip()
    sort_by = request.args.get("sort_by")
    sort_dir = request.args.get("sort_dir")

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    valid_category_ids = [int(cid) for cid in category_ids if cid.isdigit()]
    if valid_category_ids:
        query = query.filter(Transaction.category_id.in_(valid_category_ids))
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

    # Apply sorting
    if sort_by and sort_dir:
        if sort_by == "data":
            if sort_dir == "crescente":
                query = query.order_by(Transaction.date.asc())
            elif sort_dir == "decrescente":
                query = query.order_by(Transaction.date.desc())
        elif sort_by == "valor":
            signed_amount = case(
                (Transaction.type == "expense", -Transaction.amount),
                else_=Transaction.amount,
            )
            if sort_dir == "crescente":
                query = query.order_by(signed_amount.asc())
            elif sort_dir == "decrescente":
                query = query.order_by(signed_amount.desc())
    else:
        # Default ordering by date descending
        query = query.order_by(Transaction.date.desc())

    return query


@app.route("/transacoes/adicionar", methods=["POST"])
@login_required
def adicionar_transacao():
    user = get_current_user()
    category_id = request.form.get("category_id")
    new_category_name = request.form.get("new_category", "").strip()
    tipo = request.form.get("tipo")
    amount_text = request.form.get("amount", "").strip().replace(',', '.')
    date_text = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    if not tipo or not amount_text or not date_text:
        flash("Preencha todos os campos obrigatórios para adicionar a transação.", "error")
        return redirect(url_for("transacoes"))

    try:
        amount = float(amount_text)
    except ValueError:
        flash("Informe um valor válido para a transação.", "error")
        return redirect(url_for("transacoes"))

    category = None
    if new_category_name:
        category = Category.query.filter(
            Category.name == new_category_name,
            (Category.user_id.is_(None)) | (Category.user_id == user.id),
        ).first()
        if category is None:
            category = Category(name=new_category_name, user_id=user.id)
            db.session.add(category)
            db.session.flush()
    elif category_id and category_id.isdigit():
        category = Category.query.filter(
            Category.id == int(category_id),
            (Category.user_id.is_(None)) | (Category.user_id == user.id),
        ).first()

    if category is None:
        flash("Selecione ou crie uma categoria válida.", "error")
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


@app.route("/transacoes/editar/<int:transaction_id>", methods=["POST"])
@login_required
def editar_transacao(transaction_id):
    user = get_current_user()
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=user.id).first()
    if transaction is None:
        flash("Transação não encontrada.", "error")
        return redirect(url_for("transacoes"))

    category_id = request.form.get("category_id")
    new_category_name = request.form.get("new_category", "").strip()
    tipo = request.form.get("tipo")
    amount_text = request.form.get("amount", "").strip().replace(',', '.')
    date_text = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    if not tipo or not amount_text or not date_text:
        flash("Preencha todos os campos obrigatórios para editar a transação.", "error")
        return redirect(url_for("transacoes"))

    try:
        amount = float(amount_text)
    except ValueError:
        flash("Informe um valor válido para a transação.", "error")
        return redirect(url_for("transacoes"))

    category = None
    if new_category_name:
        category = Category.query.filter(
            Category.name == new_category_name,
            (Category.user_id.is_(None)) | (Category.user_id == user.id),
        ).first()
        if category is None:
            category = Category(name=new_category_name, user_id=user.id)
            db.session.add(category)
            db.session.flush()
    elif category_id and category_id.isdigit():
        category = Category.query.filter(
            Category.id == int(category_id),
            (Category.user_id.is_(None)) | (Category.user_id == user.id),
        ).first()

    if category is None:
        flash("Selecione ou crie uma categoria válida.", "error")
        return redirect(url_for("transacoes"))

    try:
        tx_date = date.fromisoformat(date_text)
    except ValueError:
        flash("Informe uma data válida para a transação.", "error")
        return redirect(url_for("transacoes"))

    transaction.category_id = category.id
    transaction.type = tipo
    transaction.amount = amount
    transaction.date = tx_date
    transaction.description = description
    db.session.commit()

    flash("Transação atualizada com sucesso.", "success")
    return redirect(url_for("transacoes"))


@app.route("/transacoes/excluir/<int:transaction_id>", methods=["POST"])
@login_required
def excluir_transacao(transaction_id):
    user = get_current_user()
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=user.id).first()
    if transaction is None:
        flash("Transação não encontrada.", "error")
        return redirect(url_for("transacoes"))

    db.session.delete(transaction)
    db.session.commit()
    flash("Transação excluída com sucesso.", "success")
    return redirect(url_for("transacoes"))


@app.route("/relatorios")
@login_required
def relatorios():
    user = get_current_user()
    relatorios_gerados = get_monthly_report_cards(user)

    return render_template(
        "relatorios.html",
        user_name=user.name,
        relatorios_gerados=relatorios_gerados,
    )


@app.route("/relatorios/download/<int:relatorio_id>")
@login_required
def download_relatorio(relatorio_id):
    user = get_current_user()
    rel = Relatorio.query.filter_by(id=relatorio_id, usuario_id=user.id).first()
    if rel is None:
        flash("Relatório não encontrado.", "error")
        return redirect(url_for("relatorios"))

    transactions = (
        Transaction.query.filter(
            Transaction.user_id == user.id,
            Transaction.date >= rel.periodo_inicio,
            Transaction.date <= rel.periodo_fim,
        )
        .order_by(Transaction.date)
        .all()
    )

    arquivo_nome, pdf_bytes = gerar_pdf_relatorio(user, transactions, rel.periodo_inicio, rel.periodo_fim)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=arquivo_nome,
    )


@app.route("/relatorios/download/<int:year>/<int:month>")
@login_required
def download_relatorio_mes(year, month):
    user = get_current_user()
    try:
        period_start = date(year, month, 1)
    except ValueError:
        flash("Período inválido para download do relatório.", "error")
        return redirect(url_for("relatorios"))

    period_end = date(year, month, calendar.monthrange(year, month)[1])
    transactions = (
        Transaction.query.filter(
            Transaction.user_id == user.id,
            Transaction.date >= period_start,
            Transaction.date <= period_end,
        )
        .order_by(Transaction.date)
        .all()
    )

    if not transactions:
        flash("Nenhuma transação encontrada para este mês.", "error")
        return redirect(url_for("relatorios"))

    incomes_total = sum(tx.amount for tx in transactions if tx.type == "income")
    expenses_total = sum(tx.amount for tx in transactions if tx.type == "expense")
    balance_total = incomes_total - expenses_total

    arquivo_nome = f"Relatório {format_periodo_por_extenso(period_start)}.pdf"
    arquivo_nome, pdf_bytes = gerar_pdf_relatorio(user, transactions, period_start, period_end, arquivo_nome)

    rel = Relatorio.query.filter_by(
        usuario_id=user.id,
        periodo_inicio=period_start,
        periodo_fim=period_end,
    ).first()

    if rel is None:
        rel = Relatorio(
            usuario_id=user.id,
            periodo_inicio=period_start,
            periodo_fim=period_end,
            total_receitas=incomes_total,
            total_despesas=expenses_total,
            saldo=balance_total,
            arquivo_nome=arquivo_nome,
        )
        db.session.add(rel)
    else:
        rel.total_receitas = incomes_total
        rel.total_despesas = expenses_total
        rel.saldo = balance_total
        rel.arquivo_nome = arquivo_nome

    db.session.commit()

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=arquivo_nome,
    )


@app.route("/relatorios/baixar", methods=["POST"])
@login_required
def baixar_relatorio():
    user = get_current_user()
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")

    try:
        period_start = date.fromisoformat(start_date)
        period_end = date.fromisoformat(end_date)
    except (TypeError, ValueError):
        flash("Período inválido para gerar o relatório.", "error")
        return redirect(url_for("relatorios"))

    transactions = (
        Transaction.query.filter(
            Transaction.user_id == user.id,
            Transaction.date >= period_start,
            Transaction.date <= period_end,
        )
        .order_by(Transaction.date)
        .all()
    )

    incomes_total = sum(tx.amount for tx in transactions if tx.type == "income")
    expenses_total = sum(tx.amount for tx in transactions if tx.type == "expense")
    balance_total = incomes_total - expenses_total

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Relatório Financeiro", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Usuário: {user.name}", ln=True)
    pdf.cell(0, 8, f"Período: {period_start.strftime('%d/%m/%Y')} - {period_end.strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 8, f"Gerado em: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC", ln=True)
    pdf.ln(6)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Resumo", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"Receitas: R$ {incomes_total:.2f}".replace('.', ','), ln=True)
    pdf.cell(0, 6, f"Despesas: R$ {expenses_total:.2f}".replace('.', ','), ln=True)
    pdf.cell(0, 6, f"Saldo: R$ {balance_total:.2f}".replace('.', ','), ln=True)
    pdf.ln(8)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Transações", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(30, 7, "Data", 1, 0, 'C', True)
    pdf.cell(55, 7, "Categoria", 1, 0, 'C', True)
    pdf.cell(30, 7, "Tipo", 1, 0, 'C', True)
    pdf.cell(35, 7, "Valor", 1, 0, 'C', True)
    pdf.cell(0, 7, "Descrição", 1, 1, 'C', True)

    for tx in transactions:
        pdf.cell(30, 7, tx.date.strftime('%d/%m/%Y'), 1)
        pdf.cell(55, 7, tx.category.name[:30], 1)
        pdf.cell(30, 7, "Receita" if tx.type == "income" else "Despesa", 1)
        pdf.cell(35, 7, f"R$ {tx.amount:.2f}".replace('.', ','), 1)
        pdf.multi_cell(0, 7, tx.description or "", 1)

    arquivo_nome = f"relatorio_{user.name.lower().replace(' ', '_')}_{period_start.strftime('%Y%m')}.pdf"
    relatorio = Relatorio(
        usuario_id=user.id,
        periodo_inicio=period_start,
        periodo_fim=period_end,
        total_receitas=incomes_total,
        total_despesas=expenses_total,
        saldo=balance_total,
        arquivo_nome=arquivo_nome,
    )
    db.session.add(relatorio)
    db.session.commit()

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=arquivo_nome,
    )


@app.route("/configuracoes", methods=["GET", "POST"])
@login_required
def configuracoes():
    user = get_current_user()

    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "edit_profile":
            new_name = request.form.get("name", "").strip()
            if not new_name:
                flash("O nome não pode ser vazio.", "error")
                return redirect(url_for("configuracoes"))
            
            user.name = new_name
            session["user_name"] = new_name
            db.session.commit()
            flash("Perfil atualizado com sucesso.", "success")
            return redirect(url_for("configuracoes"))

        if action == "change_password":
            old_password = request.form.get("old_password", "").strip()
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()

            if not old_password or not new_password or not confirm_password:
                flash("Preencha todos os campos para alterar a senha.", "error")
                return redirect(url_for("configuracoes"))

            auth = Autenticacao.query.filter_by(usuario_id=user.id).first()
            if not auth or not check_password_hash(auth.senha_hash, old_password):
                flash("Senha atual incorreta.", "error")
                return redirect(url_for("configuracoes"))

            if new_password != confirm_password:
                flash("As novas senhas não coincidem.", "error")
                return redirect(url_for("configuracoes"))

            if len(new_password) < 6:
                flash("A nova senha deve ter no mínimo 6 caracteres.", "error")
                return redirect(url_for("configuracoes"))

            auth.senha_hash = generate_password_hash(new_password)
            db.session.commit()
            flash("Senha alterada com sucesso.", "success")
            return redirect(url_for("configuracoes"))

        if action == "delete_account":
            current_password = request.form.get("current_password", "").strip()
            confirm_phrase = request.form.get("confirm_phrase", "").strip()

            if not current_password or confirm_phrase != "EXCLUIR":
                flash("Senha e confirmação são necessárias para excluir a conta.", "error")
                return redirect(url_for("configuracoes"))

            auth = Autenticacao.query.filter_by(usuario_id=user.id).first()
            if not auth or not check_password_hash(auth.senha_hash, current_password):
                flash("Senha atual incorreta.", "error")
                return redirect(url_for("configuracoes"))

            Transaction.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            Relatorio.query.filter_by(usuario_id=user.id).delete(synchronize_session=False)
            Autenticacao.query.filter_by(usuario_id=user.id).delete(synchronize_session=False)
            User.query.filter_by(id=user.id).delete(synchronize_session=False)
            db.session.commit()
            session.clear()
            flash("Sua conta foi excluída com sucesso.", "success")
            return redirect(url_for("auth"))

    auth = Autenticacao.query.filter_by(usuario_id=user.id).first()
    email = auth.email if auth else user.email

    return render_template(
        "configuracoes.html",
        user_name=user.name,
        user=user,
        email=email,
    )


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("auth"))


@app.route("/auth", methods=["GET", "POST"])
def auth():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    active_tab = request.args.get("tab", "login")

    if request.method == "POST":
        action = request.form.get("action")
        if action == "login":
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()

            if not email or not password:
                flash("Preencha e-mail e senha para entrar.", "error")
            else:
                auth_record = Autenticacao.query.filter_by(email=email).first()
                if auth_record is None or not check_password_hash(auth_record.senha_hash, password):
                    flash("E-mail ou senha incorretos.", "error")
                else:
                    session["user_id"] = auth_record.usuario_id
                    session["user_name"] = auth_record.usuario.name
                    return redirect(url_for("dashboard"))

        if action == "register":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()

            if not name or not email or not password:
                flash("Preencha todos os campos para criar sua conta.", "error")
                active_tab = "register"
            else:
                if Autenticacao.query.filter_by(email=email).first() is not None or User.query.filter_by(email=email).first() is not None:
                    flash("Este e-mail já está em uso.", "error")
                    active_tab = "register"
                else:
                    user = User(name=name, email=email)
                    db.session.add(user)
                    db.session.flush()

                    auth_record = Autenticacao(
                        usuario_id=user.id,
                        email=email,
                        senha_hash=generate_password_hash(password),
                    )
                    db.session.add(auth_record)
                    db.session.commit()

                    session["user_id"] = user.id
                    session["user_name"] = user.name
                    flash("Conta criada com sucesso.", "success")
                    return redirect(url_for("dashboard"))

    return render_template("auth.html", active_tab=active_tab)


@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    period = request.args.get("period", "month")
    selected_month = request.args.get("selected_month", date.today().strftime("%Y-%m"))
    selected_year = request.args.get("selected_year", str(date.today().year))
    dashboard_data = build_dashboard_data(
        user,
        period=period,
        selected_month=selected_month,
        selected_year=selected_year,
    )
    return render_template(
        "dashboard.html",
        user_name=user.name,
        dashboard_data=dashboard_data,
        filter_period=period,
        selected_month=selected_month,
        selected_year=selected_year,
        current_year=date.today().year,
    )


@app.route("/transacoes")
@login_required
def transacoes():
    user = get_current_user()
    categories = Category.query.filter(
        (Category.user_id.is_(None)) | (Category.user_id == user.id)
    ).order_by(Category.name).all()
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
            "date_range": request.args.get("date_range", "month"),
            "category_id": request.args.getlist("category_id"),
            "tipo": request.args.get("tipo", "all"),
            "min_value": request.args.get("min_value", ""),
            "max_value": request.args.get("max_value", ""),
            "sort_by": request.args.get("sort_by", ""),
            "sort_dir": request.args.get("sort_dir", ""),
        },
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth"))


with app.app_context():
    db.create_all()
    ensure_category_schema()
    user = get_default_user()
    create_default_categories()
    cleanup_test_categories()


if __name__ == "__main__":
    app.run(debug=True)
