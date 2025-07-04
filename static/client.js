document.addEventListener("DOMContentLoaded", () => {
    // Check if user is logged in
    const { username, isAuthenticated } = window.userData || {};

    if (!isAuthenticated || !username) {
        alert("Please login first");
        window.location.href = '/login';
        return;
    }

    const socket = io();
    const chat = document.getElementById("chat");
    const messageInput = document.getElementById("message");
    const sendBtn = document.getElementById("send");
    const contactList = document.getElementById("contact-list");
    const contactInput = document.getElementById("new-contact");
    const addContactBtn = document.getElementById("add-contact");

    // Join chat room
    const room = prompt("Enter room name:") || 'general';
    socket.emit("join", { username, room });

    // Message handling
    function appendMessage(data) {
        // Ensure data has the expected structure
        const messageData = {
            username: data?.username || 'Unknown',
            message: data?.message || data?.content || '',
            timestamp: data?.timestamp || new Date().toISOString()
        };

        const p = document.createElement("p");
        const time = new Date(messageData.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });

        p.innerHTML = `
            <span class="message-time">[${time}]</span>
            <strong>${messageData.username}:</strong>
            ${messageData.message}
        `;

        // Add visual distinction for user's own messages
        if (messageData.username === username) {
            p.classList.add('own-message');
        }

        chat.appendChild(p);
        chat.scrollTop = chat.scrollHeight;
    }

    // Message history handler
    socket.on('message_history', (messages) => {
        messages.forEach(msg => {
            appendMessage({
                username: msg.username,
                message: msg.content || msg.message,
                timestamp: msg.timestamp
            });
        });
    });

    // Real-time message handler
    socket.on("message", (data) => {
        if (typeof data === 'string') {
            // Handle legacy string messages
            appendMessage({
                username: 'System',
                message: data
            });
        } else {
            // Handle proper message objects
            appendMessage(data);
        }
    });

    // Message sending
    function sendMessage() {
        const msg = messageInput.value.trim();
        if (msg) {
            socket.emit("send_message", {
                username: username,
                message: msg
            });
            messageInput.value = "";
        }
    }

    sendBtn.onclick = sendMessage;
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendMessage();
    });

    // Contact management
    async function loadContacts() {
        try {
            const res = await fetch('/get_contacts');
            if (!res.ok) throw new Error("Failed to load contacts");
            const contacts = await res.json();

            contactList.innerHTML = "";
            contacts.forEach(contact => {
                const li = document.createElement("li");
                li.textContent = contact;
                li.addEventListener('click', () => {
                    // Optional: Implement contact click functionality
                });
                contactList.appendChild(li);
            });
        } catch (err) {
            console.error("Error loading contacts:", err);
            contactList.innerHTML = "<li class='error'>Unable to load contacts</li>";
        }
    }

    socket.on("joined", loadContacts);

    // Add new contact
    async function addContact() {
        const contact = contactInput.value.trim();
        if (!contact) return;

        // Client-side duplicate check
        const existingContacts = Array.from(contactList.querySelectorAll('li'));
        if (existingContacts.some(li => li.textContent === contact)) {
            alert('Contact already exists');
            return;
        }

        try {
            const csrfToken = document.querySelector("[name='csrf_token']")?.value;
            if (!csrfToken) throw new Error("Missing CSRF token");

            const response = await fetch("/add_contact", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({ contact_name: contact })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || "Failed to add contact");
            }

            if (data.success) {
                const li = document.createElement("li");
                li.textContent = contact;
                contactList.appendChild(li);
                contactInput.value = "";
            } else {
                alert(data.message || "Contact not added");
            }
        } catch (err) {
            console.error("Error adding contact:", err);
            alert(err.message);
        }
    }

    addContactBtn.onclick = addContact;
    contactInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") addContact();
    });

    // Initial load
    loadContacts();
});