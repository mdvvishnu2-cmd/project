from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from config import Config
import os
import random
import string
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_voter_id():
    return 'VTR-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'voter_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def log_action(action, performed_by, details='', ip=''):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO audit_log (action, performed_by, details, ip_address) VALUES (%s, %s, %s, %s)",
                (action, performed_by, details, ip))
    mysql.connection.commit()
    cur.close()

# ─── Public Routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as total FROM voters")
    voter_count = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM candidates WHERE is_active = TRUE")
    candidate_count = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM votes")
    vote_count = cur.fetchone()['total']
    cur.execute("SELECT *, NOW() >= start_date AND NOW() <= end_date AS is_voting_open, NOW() >= release_date AS is_result_released FROM elections WHERE is_active = TRUE LIMIT 1")
    election = cur.fetchone()
    cur.close()
    return render_template('index.html',
                           voter_count=voter_count,
                           candidate_count=candidate_count,
                           vote_count=vote_count,
                           election=election)

# ─── Voter Auth ────────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'voter_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        register_number = request.form.get('register_number', '').strip()
        department = request.form.get('department', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        date_of_birth = request.form.get('date_of_birth', '')

        errors = []
        if not full_name: errors.append('Full name is required.')
        if not register_number: errors.append('Register number is required.')
        if not department: errors.append('Department is required.')
        if len(password) < 8: errors.append('Password must be at least 8 characters.')
        if password != confirm_password: errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html', form_data=request.form)

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM voters WHERE register_number = %s", (register_number,))
        if cur.fetchone():
            flash('Register number already registered. Please login.', 'warning')
            cur.close()
            return render_template('register.html', form_data=request.form)

        voter_id = generate_voter_id()
        password_hash = generate_password_hash(password)

        cur.execute("""
            INSERT INTO voters (full_name, register_number, department, voter_id, password_hash, phone, date_of_birth, is_verified)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
        """, (full_name, register_number, department, voter_id, password_hash, phone, date_of_birth or None))
        mysql.connection.commit()
        cur.close()

        log_action('VOTER_REGISTERED', full_name, f'Reg No: {register_number}', request.remote_addr)
        flash(f'Registration successful! Your Voter ID is <strong>{voter_id}</strong>. Please save it.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form_data={})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'voter_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        register_number = request.form.get('register_number', '').strip()
        password = request.form.get('password', '')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM voters WHERE register_number = %s", (register_number,))
        voter = cur.fetchone()

        if voter and check_password_hash(voter['password_hash'], password):
            if not voter['is_verified']:
                flash('Your account is pending verification.', 'warning')
                cur.close()
                return redirect(url_for('login'))

            session['voter_id'] = voter['id']
            session['voter_name'] = voter['full_name']
            session['voter_code'] = voter['voter_id']
            session['has_voted'] = voter['has_voted']

            cur.execute("UPDATE voters SET last_login = NOW() WHERE id = %s", (voter['id'],))
            mysql.connection.commit()
            cur.close()

            log_action('VOTER_LOGIN', voter['full_name'], '', request.remote_addr)
            flash(f'Welcome back, {voter["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            cur.close()

    return render_template('login.html')


@app.route('/logout')
def logout():
    voter_name = session.get('voter_name', 'Unknown')
    session.clear()
    log_action('VOTER_LOGOUT', voter_name, '', request.remote_addr)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if 'voter_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        register_number = request.form.get('register_number', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if len(new_password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('forgot_password.html')
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('forgot_password.html')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM voters WHERE register_number = %s", (register_number,))
        voter = cur.fetchone()

        if voter:
            password_hash = generate_password_hash(new_password)
            cur.execute("UPDATE voters SET password_hash = %s WHERE id = %s", (password_hash, voter['id']))
            mysql.connection.commit()
            log_action('VOTER_PASSWORD_RESET', register_number, '', request.remote_addr)
            flash('Password updated successfully. Please login with your new password.', 'success')
            cur.close()
            return redirect(url_for('login'))
        else:
            flash('Register number not found.', 'danger')
            cur.close()

    return render_template('forgot_password.html')


# ─── Voter Dashboard ───────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM voters WHERE id = %s", (session['voter_id'],))
    voter = cur.fetchone()
    cur.execute("SELECT *, NOW() >= start_date AND NOW() <= end_date AS is_voting_open, NOW() >= release_date AS is_result_released FROM elections WHERE is_active = TRUE LIMIT 1")
    election = cur.fetchone()
    cur.execute("SELECT * FROM candidates WHERE is_active = TRUE ORDER BY name")
    candidates = cur.fetchall()
    cur.close()
    return render_template('dashboard.html', voter=voter, election=election, candidates=candidates)


@app.route('/vote', methods=['GET', 'POST'])
@login_required
def vote():
    cur = mysql.connection.cursor()
    cur.execute("SELECT has_voted FROM voters WHERE id = %s", (session['voter_id'],))
    voter = cur.fetchone()

    if voter['has_voted']:
        flash('You have already cast your vote.', 'warning')
        cur.close()
        return redirect(url_for('dashboard'))

    cur.execute("SELECT *, NOW() >= start_date AND NOW() <= end_date AS is_voting_open FROM elections WHERE is_active = TRUE LIMIT 1")
    election = cur.fetchone()
    
    if not election or not election['is_voting_open']:
        flash('Voting is currently closed.', 'warning')
        cur.close()
        return redirect(url_for('dashboard'))

    cur.execute("SELECT * FROM candidates WHERE is_active = TRUE ORDER BY name")
    candidates = cur.fetchall()

    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        if not candidate_id:
            flash('Please select a candidate.', 'danger')
            cur.close()
            return render_template('vote.html', candidates=candidates, election=election)

        # Verify candidate exists
        cur.execute("SELECT * FROM candidates WHERE id = %s AND is_active = TRUE", (candidate_id,))
        candidate = cur.fetchone()
        if not candidate:
            flash('Invalid candidate selection.', 'danger')
            cur.close()
            return render_template('vote.html', candidates=candidates, election=election)

        # Cast vote
        cur.execute("""
            INSERT INTO votes (voter_id, candidate_id, election_id, ip_address)
            VALUES (%s, %s, %s, %s)
        """, (session['voter_id'], candidate_id, election['id'], request.remote_addr))
        cur.execute("UPDATE voters SET has_voted = TRUE WHERE id = %s", (session['voter_id'],))
        mysql.connection.commit()

        session['has_voted'] = True
        log_action('VOTE_CAST', session['voter_name'], f'Candidate ID: {candidate_id}', request.remote_addr)
        flash(f'Your vote for <strong>{candidate["name"]}</strong> has been recorded!', 'success')
        cur.close()
        return redirect(url_for('dashboard'))

    cur.close()
    return render_template('vote.html', candidates=candidates, election=election)


@app.route('/result')
def result():
    cur = mysql.connection.cursor()
    cur.execute("SELECT *, NOW() >= release_date AS is_result_released FROM elections WHERE is_active = TRUE LIMIT 1")
    election = cur.fetchone()
    
    if not election or not election['is_result_released']:
        flash('Election results are not yet released.', 'warning')
        cur.close()
        return redirect(url_for('index'))

    cur.execute("""
        SELECT c.id, c.name, c.party, c.photo, c.position,
               COUNT(v.id) as vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.id = v.candidate_id
        WHERE c.is_active = TRUE
        GROUP BY c.id
        ORDER BY vote_count DESC
    """)
    results = cur.fetchall()
    cur.execute("SELECT COUNT(*) as total FROM votes")
    total_votes = cur.fetchone()['total']
    cur.close()

    for r in results:
        r['percentage'] = round((r['vote_count'] / total_votes * 100), 1) if total_votes > 0 else 0

    has_voted = False
    if 'voter_id' in session:
        has_voted = session.get('has_voted', False)

    return render_template('result.html', results=results, total_votes=total_votes,
                           election=election, has_voted=has_voted)


@app.route('/admin/result')
@admin_required
def admin_result():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM elections WHERE is_active = TRUE LIMIT 1")
    election = cur.fetchone()
    cur.execute("""
        SELECT c.id, c.name, c.party, c.photo, c.position,
               COUNT(v.id) as vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.id = v.candidate_id
        WHERE c.is_active = TRUE
        GROUP BY c.id
        ORDER BY vote_count DESC
    """)
    results = cur.fetchall()
    cur.execute("SELECT COUNT(*) as total FROM votes")
    total_votes = cur.fetchone()['total']
    cur.close()

    for r in results:
        r['percentage'] = round((r['vote_count'] / total_votes * 100), 1) if total_votes > 0 else 0

    return render_template('result.html', results=results, total_votes=total_votes,
                           election=election, has_voted=True)


# ─── Admin Routes ──────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cur.fetchone()

        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_id'] = admin['id']
            session['admin_name'] = admin['username']
            cur.execute("UPDATE admins SET last_login = NOW() WHERE id = %s", (admin['id'],))
            mysql.connection.commit()
            cur.close()
            log_action('ADMIN_LOGIN', username, '', request.remote_addr)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
            cur.close()

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    admin_name = session.get('admin_name', '')
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    log_action('ADMIN_LOGOUT', admin_name, '', request.remote_addr)
    return redirect(url_for('admin_login'))


@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def admin_forgot_password():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if len(new_password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('admin_forgot_password.html')
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('admin_forgot_password.html')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM admins WHERE username = %s", (username,))
        admin = cur.fetchone()

        if admin:
            password_hash = generate_password_hash(new_password)
            cur.execute("UPDATE admins SET password_hash = %s WHERE id = %s", (password_hash, admin['id']))
            mysql.connection.commit()
            log_action('ADMIN_PASSWORD_RESET', username, '', request.remote_addr)
            flash('Password updated successfully. Please login with your new password.', 'success')
            cur.close()
            return redirect(url_for('admin_login'))
        else:
            flash('Username not found.', 'danger')
            cur.close()

    return render_template('admin_forgot_password.html')


@app.route('/admin/election', methods=['GET', 'POST'])
@admin_required
def admin_election():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        release_date = request.form.get('release_date')
        
        cur.execute("""
            UPDATE elections SET 
                title = %s, description = %s, 
                start_date = %s, end_date = %s, release_date = %s
            WHERE is_active = TRUE
        """, (title, description, start_date, end_date, release_date))
        mysql.connection.commit()
        log_action('ELECTION_UPDATED', session.get('admin_name', 'admin'), f'Updated election schedule: {title}', request.remote_addr)
        flash('Election settings updated successfully.', 'success')
        
    cur.execute("SELECT * FROM elections WHERE is_active = TRUE LIMIT 1")
    election = cur.fetchone()
    cur.close()
    return render_template('admin_election.html', election=election)


@app.route('/admin/election/publish', methods=['POST'])
@admin_required
def publish_results():
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE elections SET release_date = NOW() 
        WHERE is_active = TRUE
    """)
    mysql.connection.commit()
    cur.close()
    
    log_action('RESULTS_PUBLISHED', session.get('admin_name', 'admin'), 'Results published manually', request.remote_addr)
    flash('Results have been published and are now visible to students.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as total FROM voters")
    voter_count = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM voters WHERE has_voted = TRUE")
    voted_count = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM candidates WHERE is_active = TRUE")
    candidate_count = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM votes")
    vote_count = cur.fetchone()['total']
    cur.execute("""
        SELECT c.name, c.party, c.photo, COUNT(v.id) as vote_count
        FROM candidates c LEFT JOIN votes v ON c.id = v.candidate_id
        WHERE c.is_active = TRUE GROUP BY c.id ORDER BY vote_count DESC
    """)
    candidate_results = cur.fetchall()
    cur.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 20")
    logs = cur.fetchall()
    cur.execute("""
        SELECT v.*, c.name as voted_for 
        FROM voters v
        LEFT JOIN votes vo ON v.id = vo.voter_id
        LEFT JOIN candidates c ON vo.candidate_id = c.id
        ORDER BY v.registered_at DESC
    """)
    all_voters = cur.fetchall()
    
    cur.execute("SELECT *, NOW() >= release_date AS is_result_released FROM elections WHERE is_active = TRUE LIMIT 1")
    election = cur.fetchone()
    cur.close()

    turnout = round((voted_count / voter_count * 100), 1) if voter_count > 0 else 0
    return render_template('admin_dashboard.html',
                           voter_count=voter_count, voted_count=voted_count,
                           candidate_count=candidate_count, vote_count=vote_count,
                           candidate_results=candidate_results, logs=logs,
                           all_voters=all_voters, turnout=turnout, election=election)


@app.route('/admin/candidates')
@admin_required
def manage_candidates():
    cur = mysql.connection.cursor()
    cur.execute("SELECT c.*, COUNT(v.id) as vote_count FROM candidates c LEFT JOIN votes v ON c.id = v.candidate_id GROUP BY c.id ORDER BY c.created_at DESC")
    candidates = cur.fetchall()
    cur.close()
    return render_template('manage_candidate.html', candidates=candidates)


@app.route('/admin/candidates/add', methods=['GET', 'POST'])
@admin_required
def add_candidate():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        party = request.form.get('party', '').strip()
        position = request.form.get('position', '').strip()
        bio = request.form.get('bio', '').strip()
        manifesto = request.form.get('manifesto', '').strip()
        photo_filename = None

        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
                photo_filename = unique_name

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO candidates (name, party, position, bio, photo, manifesto)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, party, position, bio, photo_filename, manifesto))
        mysql.connection.commit()
        cur.close()

        log_action('CANDIDATE_ADDED', session['admin_name'], f'Candidate: {name}', request.remote_addr)
        flash(f'Candidate <strong>{name}</strong> added successfully!', 'success')
        return redirect(url_for('manage_candidates'))

    return render_template('add_candidate.html')


@app.route('/admin/candidates/toggle/<int:candidate_id>')
@admin_required
def toggle_candidate(candidate_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT name, is_active FROM candidates WHERE id = %s", (candidate_id,))
    candidate = cur.fetchone()
    if candidate:
        new_status = not candidate['is_active']
        cur.execute("UPDATE candidates SET is_active = %s WHERE id = %s", (new_status, candidate_id))
        mysql.connection.commit()
        action = 'activated' if new_status else 'deactivated'
        log_action('CANDIDATE_TOGGLED', session['admin_name'], f'{candidate["name"]} {action}', request.remote_addr)
        flash(f'Candidate {action} successfully.', 'success')
    cur.close()
    return redirect(url_for('manage_candidates'))


@app.route('/admin/candidates/edit/<int:candidate_id>', methods=['GET', 'POST'])
@admin_required
def edit_candidate(candidate_id):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        party = request.form.get('party', '').strip()
        position = request.form.get('position', '').strip()
        bio = request.form.get('bio', '').strip()
        manifesto = request.form.get('manifesto', '').strip()
        
        cur.execute("SELECT photo FROM candidates WHERE id = %s", (candidate_id,))
        existing_candidate = cur.fetchone()
        photo_filename = existing_candidate['photo'] if existing_candidate else None

        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
                photo_filename = unique_name

        cur.execute("""
            UPDATE candidates 
            SET name = %s, party = %s, position = %s, bio = %s, photo = %s, manifesto = %s
            WHERE id = %s
        """, (name, party, position, bio, photo_filename, manifesto, candidate_id))
        mysql.connection.commit()

        log_action('CANDIDATE_EDITED', session['admin_name'], f'Candidate: {name}', request.remote_addr)
        flash(f'Candidate <strong>{name}</strong> updated successfully!', 'success')
        cur.close()
        return redirect(url_for('manage_candidates'))

    cur.execute("SELECT * FROM candidates WHERE id = %s", (candidate_id,))
    candidate = cur.fetchone()
    cur.close()
    
    if not candidate:
        flash('Candidate not found.', 'danger')
        return redirect(url_for('manage_candidates'))
        
    return render_template('edit_candidate.html', candidate=candidate)


@app.route('/admin/candidates/delete/<int:candidate_id>', methods=['POST'])
@admin_required
def delete_candidate(candidate_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT name FROM candidates WHERE id = %s", (candidate_id,))
    candidate = cur.fetchone()
    if candidate:
        cur.execute("DELETE FROM candidates WHERE id = %s", (candidate_id,))
        mysql.connection.commit()
        log_action('CANDIDATE_DELETED', session['admin_name'], f'Candidate: {candidate["name"]}', request.remote_addr)
        flash('Candidate deleted.', 'success')
    cur.close()
    return redirect(url_for('manage_candidates'))


# ─── API Endpoints ─────────────────────────────────────────────────────────────

@app.route('/api/results')
def api_results():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.name, c.party, COUNT(v.id) as votes
        FROM candidates c LEFT JOIN votes v ON c.id = v.candidate_id
        WHERE c.is_active = TRUE GROUP BY c.id ORDER BY votes DESC
    """)
    results = cur.fetchall()
    cur.execute("SELECT COUNT(*) as total FROM votes")
    total = cur.fetchone()['total']
    cur.close()
    return jsonify({'results': results, 'total_votes': total})


# ─── Error Handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html'), 500


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)
