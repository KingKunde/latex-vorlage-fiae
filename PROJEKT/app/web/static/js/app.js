const toastViewport = document.getElementById("toast-viewport");

function showToast(message, level = "info", duration = 5000) {
    if (!toastViewport || !message) {
        return;
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${level}`;

    const text = document.createElement("div");
    text.textContent = message;

    const close = document.createElement("button");
    close.type = "button";
    close.setAttribute("aria-label", "Schließen");
    close.textContent = "x";
    close.addEventListener("click", () => toast.remove());

    toast.append(text, close);
    toastViewport.appendChild(toast);

    window.setTimeout(() => {
        toast.remove();
    }, duration);
}

function validatePasswordStrength(password) {
    if (password.length < 12) {
        return "Passwort muss mindestens 12 Zeichen lang sein.";
    }
    if (password.toLowerCase() === password || password.toUpperCase() === password) {
        return "Passwort muss Groß- und Kleinbuchstaben enthalten.";
    }
    if (!/[0-9]/.test(password)) {
        return "Passwort muss mindestens eine Zahl enthalten.";
    }
    if (!/[^A-Za-z0-9]/.test(password)) {
        return "Passwort muss mindestens ein Sonderzeichen enthalten.";
    }
    return null;
}

document.querySelectorAll("[data-password-validate]").forEach((input) => {
    input.addEventListener("blur", () => {
        const value = input.value.trim();
        if (!value) {
            return;
        }
        const error = validatePasswordStrength(value);
        if (error) {
            showToast(error, "info");
        }
    });
});

const { error = "", info = "" } = document.body.dataset;

if (error) {
    showToast(error, "error");
}

if (info) {
    showToast(info, "info");
}
