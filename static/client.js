document.addEventListener("DOMContentLoaded", () => {

    const socket = io();
    const room = prompt("Enter room name:");
    socket.emit("join", { username, room });

    const chat = document.getElementById("chat");
    const messageInput = document.getElementById("message");
    const sendBtn = document.getElementById("send");

    const contactList = document.getElementById("contact-list");
    const contactInput = document.getElementById("new-contact");
    const addContactBtn = document.getElementById("add-contact");

    function appendMessage(msg) {
        const p = document.createElement("p");
        p.textContent = msg;
        chat.appendChild(p);
        chat.scrollTop = chat.scrollHeight;
    }

    socket.on("message", appendMessage);

    sendBtn.onclick = () => {
        const msg = messageInput.value.trim();
        if (msg) {
            socket.emit("send_message", msg);
            messageInput.value = "";
        }
    };
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            sendBtn.click();
        }
    });


    socket.on("joined", () => {
        fetch(`/get_contacts/${username}`)
            .then(res => res.json())
            .then(contacts => {
                contactList.innerHTML = "";
                contacts.forEach(contact => {
                    const li = document.createElement("li");
                    li.textContent = contact;
                    contactList.appendChild(li);
                });
            });
    });

    addContactBtn.onclick = () => {
        const contact = contactInput.value.trim();
        if (!contact) return;
        fetch("/add_contact", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, contact_name: contact })
        })
        .then(() => {
            const li = document.createElement("li");
            li.textContent = contact;
            contactList.appendChild(li);
            contactInput.value = "";
        });
    };
    contactInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            addContactBtn.click();
        }
    });

});
