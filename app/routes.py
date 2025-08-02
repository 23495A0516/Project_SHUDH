from flask import Blueprint, render_template, request

main = Blueprint('main', __name__)

@main.route('/')
def welcome():
    return render_template('welcome.html')

@main.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        # Process login (you can add authentication logic here)
        username = request.form.get('username')
        password = request.form.get('password')
        # Temporary logic
        if username == 'admin' and password == 'admin123':
            return "Login Successful!"
        else:
            return "Invalid Credentials", 401

    return render_template('login_admin.html')


@main.route('/login_officer')
def login_officer():
    return render_template('login_officer.html')

@main.route('/login_offender')
def login_offender():
    return render_template('login_offender.html')