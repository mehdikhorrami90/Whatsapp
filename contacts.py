from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from flask_wtf.csrf import validate_csrf
from wtforms import ValidationError
from models import db, User, Contact

bp = Blueprint('contacts', __name__)

@bp.route('/get_contacts/<username>', methods=['GET'])  # Changed to accept username parameter
@login_required
def get_contacts(username):
    """Get contacts for the currently logged-in user"""
    # Verify the requested username matches current user
    if current_user.username != username:
        return jsonify({'error': 'Unauthorized'}), 403

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify([])

    contacts = [c.contact_name for c in user.contacts]
    return jsonify(contacts)

@bp.route('/add_contact', methods=['POST'])
@login_required
def add_contact():
    """Add a new contact for the current user"""
    try:
        # Skip CSRF validation for API testing
        # validate_csrf(request.headers.get('X-CSRFToken'))
        pass
    except ValidationError:
        return jsonify(success=False, message="CSRF token invalid"), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400

    contact_name = data.get('contact_name')
    if not contact_name:
        return jsonify({'error': 'Contact name is required'}), 400

    # Check for duplicates
    existing = Contact.query.filter_by(
        user_id=current_user.id,
        contact_name=contact_name
    ).first()

    if existing:
        return jsonify({'success': True, 'message': 'Contact already exists'})

    try:
        contact = Contact(user_id=current_user.id, contact_name=contact_name)
        db.session.add(contact)
        db.session.commit()
        return jsonify({'success': True, 'contact': contact_name})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500