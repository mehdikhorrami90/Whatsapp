from flask import Blueprint, request, jsonify, session
from models import db, User, Contact

bp = Blueprint('contacts', __name__)


@bp.route('/get_contacts')
def get_contacts():
    """Get contacts for the currently logged-in user"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    username = session['username']  # Get username from session
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify([])

    contacts = [c.contact_name for c in user.contacts]
    return jsonify(contacts)


@bp.route('/add_contact', methods=['POST'])
def add_contact():
    """Add a new contact for the current user"""
    if 'username' not in session:
        return jsonify(success=False, message="Unauthorized"), 401

    data = request.get_json()

    if not data:
        return jsonify({'error': 'Invalid request data'}), 400

    contact_name = data.get('contact_name')
    if not contact_name:
        return jsonify({'error': 'Contact name is required'}), 400

    username = session['username']  # Get username from session
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Check for duplicates
    existing = Contact.query.filter_by(
        user_id=user.id,
        contact_name=contact_name
    ).first()

    if existing:
        return jsonify({'success': True})

    try:
        contact = Contact(user_id=user.id, contact_name=contact_name)
        db.session.add(contact)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500