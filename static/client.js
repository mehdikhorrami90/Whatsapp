document.addEventListener("DOMContentLoaded", () => {
    const { username, isAuthenticated } = window.userData || {};
    let currentRoom = null;

    if (!isAuthenticated || !username) {
        alert("Please login first");
        window.location.href = '/login';
        return;
    }

    const socket = io();
    const chat = document.getElementById("chat");
    const messageInput = document.getElementById("message");
    const sendBtn = document.getElementById("send");

    // Room handling functions
    function joinRoom(roomId, roomName) {
        if (currentRoom) {
            socket.emit('leave_room', { room: currentRoom });
        }
        socket.emit('join_room', {
            room: roomId,
            username: username
        });
        currentRoom = roomId;
        document.getElementById("current-room-name").textContent = roomName;
        loadRoomMessages(roomId);
    }

    async function loadRoomMessages(roomId) {
        try {
            const response = await fetch(`/api/rooms/${roomId}/messages`);
            if (!response.ok) throw new Error("Failed to load messages");
            const messages = await response.json();

            chat.innerHTML = '';
            messages.forEach(msg => appendMessage(msg));
        } catch (err) {
            console.error("Error loading messages:", err);
            chat.innerHTML = "<p>Error loading messages</p>";
        }
    }

    // Message handling
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

    // Message sending
    function sendMessage() {
        const msg = messageInput.value.trim();
        if (msg && currentRoom) {
            socket.emit("send_message", {
                room: currentRoom,
                username: username,
                message: msg
            });
            messageInput.value = "";
        }
    }

    // Socket event handlers
    socket.on('message', (data) => {
        if (data.room === currentRoom) {
            appendMessage(data);
        }
    });

    socket.on('message_history', (messages) => {
        messages.forEach(msg => {
            appendMessage({
                username: msg.username,
                message: msg.content || msg.message,
                timestamp: msg.timestamp
            });
        });
    });

    // Event listeners
    sendBtn.onclick = sendMessage;
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendMessage();
    });

    // Initialize by joining the first room if we're on a room page
    if (window.location.pathname.startsWith('/room/')) {
        const roomId = window.location.pathname.split('/')[2];
        const roomName = document.getElementById("current-room-name").textContent;
        joinRoom(roomId, roomName);
    }
});