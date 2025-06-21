from flask import Blueprint, jsonify, request
import json
import os

bp = Blueprint('contacts', __name__)
CONTACTS_FILE = 'contacts.json'


def load_contacts():
    if not os.path.exists(CONTACTS_FILE):
        return []
    with open(CONTACTS_FILE, 'r') as f:
        return json.load(f)


def save_contacts(data):
    with open(CONTACTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


@bp.route('/get_contacts/<username>')
def get_contacts(username):
    contacts = load_contacts()
    for user in contacts:
        if user['username'] == username:
            return jsonify(user['saved_contacts'])
    return jsonify([])


@bp.route('/add_contact', methods=['POST'])
def add_contact():
    data = request.json
    username = data.get('username')
    contact_name = data.get('contact_name')

    contacts = load_contacts()
    for user in contacts:
        if user['username'] == username:
            if contact_name not in user['saved_contacts']:
                user['saved_contacts'].append(contact_name)
            save_contacts(contacts)
            return jsonify(success=True)

    contacts.append({
        'username': username,
        'saved_contacts': [contact_name]
    })
    save_contacts(contacts)
    return jsonify(success=True)
