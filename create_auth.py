from app import db, Autenticacao, User, app
from werkzeug.security import generate_password_hash

app.app_context().push()

# Obter o primeiro usuário
user = User.query.first()

if user:
    # Verificar se já existe autenticação
    existing_auth = Autenticacao.query.filter_by(usuario_id=user.id).first()
    
    if not existing_auth:
        # Criar novo registro de autenticação
        auth = Autenticacao(
            usuario_id=user.id,
            email=user.email,
            senha_hash=generate_password_hash("password123")
        )
        db.session.add(auth)
        db.session.commit()
        print(f"✓ Registro de autenticação criado para {user.name} ({user.email})")
        print(f"  Senha: password123")
    else:
        print(f"✓ Registro de autenticação já existe para {user.name}")
