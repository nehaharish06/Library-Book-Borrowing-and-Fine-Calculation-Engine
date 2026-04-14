function showAlert(msg) {
    alert(msg);
}

function sendMail(userId) {
    const email = document.getElementById(`email_${userId}`).value;

    fetch(`/send_mail/${userId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: `email=${encodeURIComponent(email)}`
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            alert("✅ " + data.message);
        } else {
            alert("❌ Error: " + data.message);
        }
    })
    .catch(err => {
        alert("❌ Something went wrong");
        console.error(err);
    });
}

function sendBulk() {
    if (!confirm("Are you sure you want to send all emails?")) return;

    fetch('/send_bulk', {
        method: 'POST'
    })
    .then(res => res.json())
    .then(data => {
        alert(`✅ Bulk Email Completed

Sent: ${data.sent}
Failed: ${data.failed}`);
    })
    .catch(err => {
        alert("❌ Bulk email failed");
        console.error(err);
    });
}

function printPDF(userId) {
    const url = `/download/receipt_${userId}.pdf`;

    // Open PDF in new tab
    const win = window.open(url, '_blank');

    // Wait for PDF to load, then trigger print
    win.onload = function () {
        win.print();
    };
}