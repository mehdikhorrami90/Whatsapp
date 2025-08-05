document.addEventListener("DOMContentLoaded", () => {
    const { username, isAuthenticated } = window.userData || {};

    if (!isAuthenticated || !username) {
        alert("Please login first");
        window.location.href = '/login';
        return;
    }

    const socket = io();
    let currentRoom = 'general';

    // DOM Elements
    const chat = document.getElementById("chat");
    const messageInput = document.getElementById("message");
    const sendBtn = document.getElementById("send");

    const contactList = document.getElementById("contact-list");
    const contactInput = document.getElementById("new-contact");
    const addContactBtn = document.getElementById("add-contact");

    const currentRoomDisplay = document.getElementById("current-room");
    const roomInput = document.getElementById("room-input");
    const changeBtn = document.getElementById("change-room-btn");
    const confirmBtn = document.getElementById("confirm-room-btn");

    // --- Room UI ---
    changeBtn.addEventListener('click', () => {
        roomInput.style.display = 'inline';
        confirmBtn.style.display = 'inline';
        changeBtn.style.display = 'none';
        roomInput.focus();
    });

    confirmBtn.addEventListener('click', handleRoomChange);

    roomInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleRoomChange();
        }
    });

    async function handleRoomChange() {
        const newRoom = roomInput.value.trim() || 'general';
        if (newRoom === currentRoom) return;

        socket.emit('leave_room', { room: currentRoom });

        socket.emit('join', {
            username: username,
            room: newRoom
        });

        currentRoom = newRoom;
        currentRoomDisplay.textContent = newRoom;
        chat.innerHTML = '';
        await loadRoomMessages();

        // Reset input
        roomInput.style.display = 'none';
        confirmBtn.style.display = 'none';
        changeBtn.style.display = 'inline';
        roomInput.value = '';
    }

    // --- Join Room Initially ---
    socket.emit("join", { username, room: currentRoom });

    // --- Append Message to Chat ---
    function appendMessage(data) {
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

        if (messageData.username === username) {
            p.classList.add('own-message');
        }

        chat.appendChild(p);
        chat.scrollTop = chat.scrollHeight;
    }

    // --- Socket Events ---
    socket.on("message", (data) => {
        if (typeof data === 'string') {
            appendMessage({ username: 'System', message: data });
        } else {
            appendMessage(data);
        }
    });

    socket.on('message_history', (messages) => {
        messages.forEach(msg => appendMessage({
            username: msg.username,
            message: msg.content || msg.message,
            timestamp: msg.timestamp
        }));
    });

    socket.on("joined", loadContacts);

    // --- Send Message ---
    function sendMessage() {
        const msg = messageInput.value.trim();
        if (msg) {
            socket.emit("send_message", {
                username: username,
                message: msg
            });
            messageInput.value = "";
            messageInput.style.height = 'auto';
        }
    }

    sendBtn.onclick = sendMessage;

    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }

        // Auto-resize input
            setTimeout(() => {
                messageInput.style.height = 'auto';
            }, 0);
    });

    // --- Contacts ---
    async function loadContacts() {
        try {
            const res = await fetch(`/contacts/get_contacts/${username}`);
            if (!res.ok) throw new Error("Failed to load contacts");
            const contacts = await res.json();

            contactList.innerHTML = "";
            contacts.forEach(contact => {
                const li = document.createElement("li");
                li.textContent = contact;
                contactList.appendChild(li);
            });
        } catch (err) {
            console.error("Error loading contacts:", err);
            contactList.innerHTML = "<li class='error'>Unable to load contacts</li>";
        }
    }

    async function addContact() {
        const contact = contactInput.value.trim();
        if (!contact) return;

        const existingContacts = Array.from(contactList.querySelectorAll('li'));
        if (existingContacts.some(li => li.textContent === contact)) {
            alert('Contact already exists');
            return;
        }

        try {
            const csrfToken = document.querySelector("[name='csrf_token']")?.value;
            if (!csrfToken) throw new Error("Missing CSRF token");

            const response = await fetch("/contacts/add_contact", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({ contact_name: contact })
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.message || "Failed to add contact");
            }

            const li = document.createElement("li");
            li.textContent = contact;
            contactList.appendChild(li);
            contactInput.value = "";
        } catch (err) {
            console.error("Error adding contact:", err);
            alert(err.message);
        }
    }

    addContactBtn.onclick = addContact;

    contactInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") addContact();
    });

    // --- Load messages for current room ---
    async function loadRoomMessages() {
        try {
            const response = await fetch(`/api/rooms/messages?room=${encodeURIComponent(currentRoom)}`);
            if (!response.ok) throw new Error("Failed to load messages");
            const messages = await response.json();

            chat.innerHTML = '';
            messages.forEach(msg => appendMessage({
                username: msg.username,
                message: msg.content || msg.message,
                timestamp: msg.timestamp
            }));
        } catch (err) {
            console.error("Error loading messages:", err);
            chat.innerHTML = "<p>Error loading messages</p>";
        }
    }

    // Initial contact list
    loadContacts();
});
