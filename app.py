from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import session
from sqlalchemy import or_

app = Flask(__name__)
app.secret_key = 'mysecretkey123' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trek.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

# ---------------- MODELS ----------------

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Trek(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    trek_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    location = db.Column(db.String(100))
    difficulty = db.Column(db.String(20))

    assign_staff = db.Column(db.Integer)   # future me foreign key bana sakta hai

    duration = db.Column(db.Integer)
    status = db.Column(db.String(20))

    available_slots = db.Column(db.Integer)
    description = db.Column(db.Text)

    def __repr__(self):
        return f"<Trek {self.trek_name}>"

 

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    approved = db.Column(db.Boolean, default=False)  # admin approve karega
    rejected = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)        


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    phone = db.Column(db.String(20))

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'))
    user = db.relationship('User', backref='bookings')   # 👈 must
    trek = db.relationship('Trek', backref='bookings') 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
# ---------------- DB CREATE ----------------

with app.app_context():
    db.create_all()

    admin = Admin.query.filter_by(email="admin@gmail.com").first()

    if not admin:
        db.session.add(Admin(email="admin@gmail.com", password="1234"))
        db.session.commit()
        print("Admin created!")
    else:
        print("Admin already exists!")

# ---------------- LOGIN ----------------

@app.route('/admin_login', methods=['POST'])
def admin_login():
    email = request.form.get('email')
    password = request.form.get('password')

    admin = Admin.query.filter_by(email=email, password=password).first()

    if admin:
        session['admin_id'] = admin.id
        session['email'] = admin.email   # ✅ yaha name store kiya

        return redirect(url_for('admin_dashboard'))
    else:
        return "Invalid email or password"

# ---------------- ADMIN PAGES ----------------
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

 
@app.route('/admin/dashboard')
def admin_dashboard():

    total_treks = Trek.query.count()
    total_users = User.query.count()
    total_staff = Staff.query.count()
    total_bookings = Booking.query.count()
    bookings = Booking.query.all()
    users = User.query.all()
    latest_treks = Trek.query.order_by(Trek.id.desc()).limit(5).all()
    latest_users = User.query.order_by(User.id.desc()).limit(5).all()
    staffs = Staff.query.all()
    return render_template(
        "admin/admin_dash.html",
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings,
        bookings=bookings,
        staffs=staffs,
        users=users
        
    )
 
@app.route('/admin/treks')
def admin_treks():
    search = request.args.get('search')

    if search:
        treks = Trek.query.filter(
            Trek.trek_name.ilike(f"%{search}%") |
            Trek.location.ilike(f"%{search}%") |
            Trek.difficulty.ilike(f"%{search}%")
        ).all()
    else:
        treks = Trek.query.all()
    all_treks = Trek.query.all()
    return render_template("admin/admin_treks.html", treks=treks)

@app.route('/admin/staff')
def admin_staff():
    page = request.args.get('page', 1, type=int)

    staff = Staff.query.paginate(page=page, per_page=5)

    # ✅ counts logic
    pending_count = Staff.query.filter_by(approved=False, rejected=False).count()
    approved_count = Staff.query.filter_by(approved=True).count()
    blacklist_count = Staff.query.filter_by(rejected=True).count()
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search')

    query = Staff.query

    if search:
        query = query.filter(
            Staff.name.ilike(f"%{search}%") |
            Staff.email.ilike(f"%{search}%")
        )

    staff = query.paginate(page=page, per_page=5)
    return render_template(
        'admin/admin_staff.html',
        staff=staff,
        pending_count=pending_count,
        approved_count=approved_count,
        blacklist_count=blacklist_count
    )

@app.route('/admin/users')
def admin_users():
    search = request.args.get('search')

    if search:
        users = User.query.filter(
            User.name.ilike(f"%{search}%")
        ).all()
    else:
        users = User.query.all()
    return render_template('admin/admin_users.html', users=users)

@app.route('/admin/bookings')
def admin_bookings():
    search = request.args.get('search')

    query = Booking.query.join(User).join(Trek)

    if search:
        query = query.filter(or_(
            User.name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            Trek.trek_name.ilike(f"%{search}%")
        ))

    bookings = query.all()
    return render_template('admin/admin_bookings.html', bookings=bookings)




# --------------Add New Trek-------------

@app.route('/admin/add_trek', methods=['GET', 'POST'])
def add_trek():

    # ✅ Approved staff fetch karo
    staff_list = Staff.query.filter_by(approved=True).all()

    if request.method == 'POST':

        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        trek = Trek(
            trek_name=request.form.get('trek_name'),
            start_date=start_date,
            end_date=end_date,
            location=request.form.get('location'),
            difficulty=request.form.get('difficulty'),
            assign_staff=int(request.form.get('assign_staff')), # staff id save hoga
            available_slots=int(request.form.get('available_slots')),
            duration=int(request.form.get('duration')),
            status=request.form.get('status'),
            description=request.form.get('description')
        )

        db.session.add(trek)
        db.session.commit()

        return redirect('/admin/treks')

      
    return render_template('admin/add_trek.html', staff_list=staff_list)
 

@app.route('/edit_trek/<int:id>', methods=['GET', 'POST'])
def edit_trek(id):
    trek = Trek.query.get_or_404(id)

    if request.method == 'POST':
        trek.trek_name = request.form.get('trek_name')
        trek.location = request.form.get('location')
        trek.difficulty = request.form.get('difficulty')
        trek.duration = request.form.get('duration')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        trek.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        trek.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        db.session.commit()
        return redirect('/admin/dashboard')   # apna dashboard route daal dena

    return render_template('admin/edit_trek.html', trek=trek)


@app.route('/delete_trek/<int:id>', methods=['POST'])
def delete_trek(id):
    trek = Trek.query.get_or_404(id)

    db.session.delete(trek)
    db.session.commit()

    return redirect('/admin/dashboard')


@app.route('/staff/register', methods=['GET', 'POST'])
def staff_register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not name or not email or not password:
            return "All fields are required!"

        existing = Staff.query.filter_by(email=email).first()
        if existing:
            return "Email already exists!"

        new_staff = Staff(name=name, email=email)
        new_staff.set_password(password)

        db.session.add(new_staff)
        db.session.commit()

        return redirect('/staff/login')   # better flow

    return render_template('dashboard.html')

@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        staff = Staff.query.filter_by(email=email).first()
         
        if not staff:
            return "Invalid email!"

        if not staff.check_password(password):
            return "Wrong password!"

        if not staff.approved:
            return "Wait for admin approval!"

        session['staff_id'] = staff.id
        session['staff_name'] = staff.name
        return redirect('/staff/dashboard')

    return render_template('dashboard.html')

@app.route('/staff/dashboard')
def staff_dashboard():
    if 'staff_id' not in session:
        return redirect('/staff/login')

    staff_id = int(session.get('staff_id'))
    treks = Trek.query.filter_by(assign_staff=staff_id).all()
    total_treks = len(treks)
    open_treks = Trek.query.filter_by(
        assign_staff=staff_id, status="Open"
    ).count()

    bookings = Booking.query.join(Trek).filter(
        Trek.assign_staff == staff_id
    ).all()
    total_participants = len(bookings)

    bookings = Booking.query.join(Booking.trek).filter(
    Trek.assign_staff == staff_id
    ).all()

    return render_template(
        'staff/staff-dashboard.html',
        treks=treks,
        bookings=bookings,
        total_treks=total_treks,
        open_treks=open_treks,
        total_participants=total_participants
    )



@app.route('/staff/my-treks')
def staff_my_treks():
    if 'staff_id' not in session:
        return redirect('/staff/login')

    staff_id = session['staff_id']
    treks = Trek.query.filter_by(assign_staff=staff_id).all()

    return render_template('staff/my_treks.html', treks=treks)

@app.route('/staff/update_trek/<int:id>', methods=['POST'])
def update_trek(id):
    if 'staff_id' not in session:
        return redirect('/staff/login')

    trek = Trek.query.get(id)

    if trek.assign_staff != session['staff_id']:
        return "Unauthorized "

    trek.available_slots = int(request.form.get('available_slots'))
    trek.status = request.form.get('status')

    db.session.commit()

    return redirect('/staff/my-treks')


@app.route('/staff/participants')
def staff_participants():
    if 'staff_id' not in session:
        return redirect('/staff/login')

    staff_id = session['staff_id']

    # Sirf us staff ke trek ke bookings
    bookings = Booking.query.join(Trek).filter(Trek.assign_staff == staff_id).all()

    return render_template('staff/participants.html', bookings=bookings)


@app.route('/staff/treks')
def staff_treks():
    if 'staff_id' not in session:
        return redirect('/staff/login')

    staff_id = session['staff_id']

    treks = Trek.query.filter_by(assign_staff=staff_id).all()

    return render_template('staff/staff_dashboard.html', treks=treks)




@app.route('/approve_staff/<int:id>')
def approve_staff(id):
    staff = Staff.query.get_or_404(id)

    staff.approved = True
    staff.rejected = False  

    db.session.commit()

    return redirect('/admin/staff')

@app.route('/reject_staff/<int:id>')
def reject_staff(id):
    staff = Staff.query.get_or_404(id)

    staff.approved = False
    staff.rejected = True  

    db.session.commit()

    return redirect('/admin/staff')

@app.route('/register_user', methods=['POST'])
def register_user():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    phone = request.form.get('phone')

    # Check existing user
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Email already registered!', 'danger')
        return redirect('/')

    # Create user
    new_user = User(
        name=name,
        email=email,
        phone=phone
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    flash('Registration Successful! Please login.', 'success')
    return redirect('/')


# LOGIN
@app.route("/user/login", methods=["POST"])
def user_login():
    email = request.form.get("email")
    password = request.form.get("password")


    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        session['user_id'] = user.id
        session['user_name'] = user.name

        return redirect("/user/dashboard")
    else:
        flash("Invalid email or password", "danger")
        return redirect("/")




# DASHBOARD
@app.route("/user/dashboard")
def user_dashboard():

    if "user_id" not in session:
        return redirect("/user/login")

    user_id = session.get("user_id")

    user = User.query.get(user_id)
    difficulty = request.args.get("difficulty")
    location = request.args.get("location")

  
    query = Trek.query

    # 🔹 Apply filters
    if difficulty:
        query = query.filter(Trek.difficulty == difficulty)

    if location:
        query = query.filter(Trek.location == location)
    treks = query.all()
    bookings = Booking.query.filter_by(user_id=user_id).all()
    total_treks = len(treks)
    open_treks = Trek.query.filter_by(status="Open").count()
    total_participants = len(bookings)
    locations = db.session.query(Trek.location).distinct().all()
    locations = [l[0] for l in locations]

    return render_template(
        "user/user_dashboard.html",
        user=user,
        treks=treks,
        bookings=bookings,
        total_treks=total_treks,
        open_treks=open_treks,
        total_participants=total_participants,
        locations=locations
    )

@app.route('/book_trek', methods=['POST'])
def book_trek():
    user_id = session.get('user_id')

    if not user_id:
        return "Login required "

    booking = Booking(
        user_id=user_id,
        trek_id=int(request.form.get('trek_id'))
    )

    db.session.add(booking)
    db.session.commit()

    return redirect('/user/dashboard')


@app.route('/browse_treks')
def browse_treks():
    treks = Trek.query.all()
    return render_template('user/browse_trek.html', treks=treks)


@app.route('/my_bookings')
def my_bookings():
    user_id = session.get('user_id')
    bookings = Booking.query.filter_by(user_id=user_id).all()
    return render_template('user/my_booking.html', bookings=bookings)


@app.route('/booking_history')
def booking_history():
    user_id = session.get('user_id')
    bookings = Booking.query.filter_by(user_id=user_id).all()
    return render_template('user/history.html', bookings=bookings)    


@app.route('/logout')
def logout():
    role = session.get('role')   # logout se pehle role le lo

    session.clear()

    if role == 'admin':
        return redirect('/')
    elif role == 'staff':
        return redirect('/')
    else:
        return redirect('/') 
# ---------------- RUN ----------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)