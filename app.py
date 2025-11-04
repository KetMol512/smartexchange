from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from datetime import datetime
import os

app = Flask(__name__, static_folder='.', template_folder='.')
app.config['SECRET_KEY'] = 'смените-на-свой-секрет-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'exchange.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# === МОДЕЛИ ===
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(10), unique=True)
    from_currency = db.Column(db.String(10))
    to_currency = db.Column(db.String(10))
    amount_from = db.Column(db.Float)
    amount_to = db.Column(db.Float)
    wallet = db.Column(db.String(100))
    email = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Rate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(10))
    to_currency = db.Column(db.String(10))
    rate = db.Column(db.Float)
    __table_args__ = (db.UniqueConstraint('from_currency', 'to_currency'),)

class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# === АДМИН ===
class Admin(UserMixin):
    def get_id(self): return '1'

@login_manager.user_loader
def load_user(user_id): return Admin() if user_id == '1' else None

# === МАРШРУТЫ ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == 'admin123':  # ← СМЕНИ НА СВОЙ!
            login_user(Admin())
            return redirect('/admin')
        flash('Неверный пароль', 'error')
    return '''
    <style>
      body { background:#0b1220; color:#fff; font-family:Arial; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
      .box { background:rgba(18,26,44,0.96); padding:40px; border-radius:24px; box-shadow:0 0 30px #09d6f844; width:320px; text-align:center; }
      input, button { width:100%; padding:12px; margin:10px 0; border-radius:13px; border:none; font-size:16px; }
      input { background:rgba(21,28,45,0.8); color:#fff; }
      button { background:linear-gradient(90deg,#09d6f8,#00cc66); color:#fff; font-weight:bold; cursor:pointer; }
    </style>
    <div class="box">
      <h2 style="background:linear-gradient(90deg,#09d6f8,#fbbf24);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">SmartExchange</h2>
      <form method="post">
        <input type="password" name="password" placeholder="Пароль" required>
        <button type="submit">Войти</button>
      </form>
      <p style="color:#ff8888;">{{ get_flashed_messages()|join }}</p>
    </div>
    '''

@app.route('/admin')
@login_required
def admin():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    rates = Rate.query.all()
    logs = AdminLog.query.order_by(AdminLog.timestamp.desc()).limit(50).all()

    status_map = {'pending': 'В обработке', 'completed': 'Выполнено', 'rejected': 'Отклонено'}

    html = '''
    <style>
      body { margin:0; background:#0b1220; color:#f1f5f9; font-family:Arial; min-height:100vh; }
      .container { max-width:1100px; margin:40px auto; padding:30px; background:rgba(18,26,44,0.96); border-radius:24px; box-shadow:0 0 30px #09d6f844; }
      .brand { font-size:2.5rem; text-align:center; margin-bottom:20px; background:linear-gradient(90deg,#09d6f8,#fbbf24);-webkit-background-clip:text;-webkit-text-fill-color:transparent; }
      .tabs { display:flex; gap:10px; margin-bottom:20px; }
      .tab { background:rgba(21,28,45,0.8); color:#bae6fd; padding:10px 18px; border-radius:13px; border:1px solid #1e293b; cursor:pointer; }
      .tab.active { background:#09d6f8; color:#fff; }
      table { width:100%; border-collapse:collapse; }
      th { background:rgba(21,28,45,0.9); padding:12px; color:#ffb300; }
      td { padding:10px; border-bottom:1px solid #1e293b; }
      .status { padding:5px 10px; border-radius:8px; font-size:13px; }
      .pending { background:#fbbf2444; color:#fbbf24; }
      .completed { background:#00cc6644; color:#00cc66; }
      .rejected { background:#ff444444; color:#ff6666; }
      select, button { padding:8px; margin:3px; border-radius:8px; border:1px solid #1e293b; background:rgba(21,28,45,0.8); color:#fff; }
      button { background:linear-gradient(90deg,#09d6f8,#00cc66); cursor:pointer; }
      .logout { position:fixed; top:20px; right:20px; background:#ff4444; color:#fff; padding:10px 16px; border-radius:12px; text-decoration:none; }
    </style>
    <a href="/admin/logout" class="logout">Выйти</a>
    <div class="container">
      <h1 class="brand">Админ-панель</h1>
      <div class="tabs">
        <div class="tab active" onclick="openTab('orders')">Заявки ({{orders}})</div>
        <div class="tab" onclick="openTab('rates')">Курсы</div>
        <div class="tab" onclick="openTab('logs')">Логи</div>
      </div>

      <div id="orders">
        <table><tr><th>ID</th><th>Отдаёт</th><th>Получает</th><th>Кошелёк</th><th>Email</th><th>Статус</th><th>Действие</th></tr>
    '''
    for o in orders:
        html += f'''
        <tr>
          <td>#{o.order_id}</td>
          <td>{o.from_currency} {o.amount_from}</td>
          <td>{o.to_currency} {o.amount_to}</td>
          <td style="font-size:12px;word-break:break-all;">{o.wallet}</td>
          <td>{o.email}</td>
          <td><span class="status {o.status}">{status_map[o.status]}</span></td>
          <td>
            <form method="post" action="/admin/update/{o.id}" style="display:inline;">
              <select name="status" onchange="this.form.submit()">
                <option value="pending" {'selected' if o.status=='pending' else ''}>В обработке</option>
                <option value="completed" {'selected' if o.status=='completed' else ''}>Выполнено</option>
                <option value="rejected" {'selected' if o.status=='rejected' else ''}>Отклонено</option>
              </select>
            </form>
          </td>
        </tr>
        '''
    html += '''
        </table></div>
        <div id="rates" style="display:none;">
          <form method="post" action="/admin/rate">
            <input name="from" placeholder="От" style="width:80px;">
            <input name="to" placeholder="К" style="width:80px;">
            <input name="rate" type="number" step="0.000001" placeholder="Курс">
            <button>Сохранить</button>
          </form>
          <table style="margin-top:20px;">
            <tr><th>От</th><th>К</th><th>Курс</th></tr>
    '''
    for r in rates:
        html += f'<tr><td>{r.from_currency}</td><td>{r.to_currency}</td><td>{r.rate}</td></tr>'
    html += '''
          </table>
        </div>
        <div id="logs" style="display:none;">
    '''
    for log in logs:
        html += f'<div style="padding:8px; border-bottom:1px solid #333;"><small>{log.timestamp.strftime("%H:%M %d.%m")} — {log.action}</small></div>'
    html += '''
        </div>
      </div>
      <script>
        function openTab(tab) {
          document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
          document.querySelectorAll('#orders, #rates, #logs').forEach(d => d.style.display = 'none');
          event.target.classList.add('active');
          document.getElementById(tab).style.display = 'block';
        }
      </script>
    '''
    return html

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect('/')

@app.route('/admin/update/<int:order_id>', methods=['POST'])
@login_required
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form['status']
    old = order.status
    order.status = new_status
    db.session.commit()
    db.session.add(AdminLog(action=f"Заявка #{order.order_id}: {old} → {new_status}"))
    db.session.commit()
    return redirect('/admin')

@app.route('/admin/rate', methods=['POST'])
@login_required
def update_rate():
    rate = Rate.query.filter_by(
        from_currency=request.form['from'],
        to_currency=request.form['to']
    ).first()
    if rate:
        rate.rate = float(request.form['rate'])
    else:
        db.session.add(Rate(
            from_currency=request.form['from'],
            to_currency=request.form['to'],
            rate=float(request.form['rate'])
        ))
    db.session.commit()
    db.session.add(AdminLog(action=f"Курс {request.form['from']}→{request.form['to']} = {request.form['rate']}"))
    db.session.commit()
    return redirect('/admin')

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    data = request.json
    rate = Rate.query.filter_by(from_currency=data['from'], to_currency=data['to']).first()
    if not rate:
        base = {'USDT':1, 'BTC':29000}
        rate_val = base.get(data['from'], 1) / base.get(data['to'], 1)
    else:
        rate_val = rate.rate
    return jsonify({'result': round(float(data['amount']) * rate_val, 6)})

@app.route('/api/submit', methods=['POST'])
def api_submit():
    import random, string
    data = request.json
    order_id = ''.join(random.choices(string.digits, k=6))
    order = Order(
        order_id=order_id,
        from_currency=data['from'],
        to_currency=data['to'],
        amount_from=data['amount'],
        amount_to=data['result'],
        wallet=data['wallet'],
        email=data['email']
    )
    db.session.add(order)
    db.session.commit()
    return jsonify({'order_id': order_id})

# === ИНИЦИАЛИЗАЦИЯ ===
with app.app_context():
    db.create_all()
    if not Rate.query.first():
        for f, t, r in [('BTC','USDT',29000), ('USDT','BTC',1/29000)]:
            db.session.add(Rate(from_currency=f, to_currency=t, rate=r))
        db.session.commit()


