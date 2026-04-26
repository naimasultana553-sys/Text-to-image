const API_BASE = ""; // Same origin since we're serving from FastAPI

const state = {
    token: localStorage.getItem("token"),
    user: null,
    isLogin: true,
    resetStep: 1, // 1: Email, 2: Code/New Password
    theme: localStorage.getItem("theme") || "dark-mode"
};

// DOM Elements
const authView = document.getElementById("auth-view");
const dashboardView = document.getElementById("dashboard-view");
const resetView = document.getElementById("reset-view");
const authForm = document.getElementById("auth-form");
const resetForm = document.getElementById("reset-form");
const tabLogin = document.getElementById("tab-login");
const tabSignup = document.getElementById("tab-signup");
const forgotLink = document.getElementById("forgot-link");
const backToLogin = document.getElementById("back-to-login");
const authError = document.getElementById("auth-error");
const resetError = document.getElementById("reset-error");
const resetStatus = document.getElementById("reset-status");
const resetFields = document.getElementById("reset-fields");
const resetSubmit = document.getElementById("reset-submit");
const logoutBtn = document.getElementById("logout-btn");
const generateBtn = document.getElementById("generate-btn");
const promptInput = document.getElementById("prompt-input");
const styleSelect = document.getElementById("style-select");
const loadingContainer = document.getElementById("loading-container");
const imageResult = document.getElementById("image-result");
const generatedImg = document.getElementById("generated-img");
const downloadBtn = document.getElementById("download-btn");
const historyGrid = document.getElementById("history-grid");
const userEmailSpan = document.getElementById("user-email");
const themeToggles = [document.getElementById("theme-toggle-auth"), document.getElementById("theme-toggle-nav")];

// Initialize
async function init() {
    applyTheme();
    if (state.token) {
        const success = await fetchUser();
        if (success) {
            showView("dashboard");
            loadHistory();
        } else {
            showView("auth");
        }
    } else {
        showView("auth");
    }
}

function applyTheme() {
    document.body.classList.remove("dark-mode", "light-mode");
    document.body.classList.add(state.theme);
}

themeToggles.forEach(btn => {
    if (btn) {
        btn.addEventListener("click", () => {
            state.theme = state.theme === "dark-mode" ? "light-mode" : "dark-mode";
            localStorage.setItem("theme", state.theme);
            applyTheme();
        });
    }
});

function showView(view) {
    authView.classList.add("hidden");
    dashboardView.classList.add("hidden");
    resetView.classList.add("hidden");
    
    if (view === "auth") {
        authView.classList.remove("hidden");
    } else if (view === "dashboard") {
        dashboardView.classList.remove("hidden");
    } else if (view === "reset") {
        resetView.classList.remove("hidden");
    }
}

// Auth Logic
tabLogin.addEventListener("click", () => {
    state.isLogin = true;
    tabLogin.classList.add("active");
    tabSignup.classList.remove("active");
});

tabSignup.addEventListener("click", () => {
    state.isLogin = false;
    tabSignup.classList.add("active");
    tabLogin.classList.remove("active");
});

forgotLink.addEventListener("click", () => {
    state.resetStep = 1;
    resetFields.classList.add("hidden");
    resetSubmit.textContent = "Send Code";
    resetStatus.textContent = "Enter your email to receive a code.";
    showView("reset");
});

backToLogin.addEventListener("click", () => showView("auth"));

authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    authError.textContent = "";

    try {
        if (state.isLogin) {
            const formData = new FormData();
            formData.append("username", email);
            formData.append("password", password);

            const res = await fetch(`${API_BASE}/login`, {
                method: "POST",
                body: formData
            });

            if (!res.ok) throw new Error("Invalid email or password");
            
            const data = await res.json();
            state.token = data.access_token;
            localStorage.setItem("token", state.token);
        } else {
            const res = await fetch(`${API_BASE}/signup`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Signup failed");
            }
            
            // Auto login after signup
            state.isLogin = true;
            return authForm.dispatchEvent(new Event("submit"));
        }

        await fetchUser();
        showView("dashboard");
        loadHistory();
    } catch (err) {
        authError.textContent = err.message;
    }
});

// Reset Logic
resetForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("reset-email").value;
    resetError.textContent = "";

    if (state.resetStep === 1) {
        try {
            const res = await fetch(`${API_BASE}/forgot-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email })
            });
            
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Server error");
            
            state.resetStep = 2;
            resetFields.classList.remove("hidden");
            resetSubmit.textContent = "Reset Password";
            resetStatus.textContent = data.message;
        } catch (err) {
            resetError.textContent = `Error: ${err.message}`;
            console.error("Reset request failed:", err);
        }
    } else {
        const code = document.getElementById("reset-code").value;
        const newPassword = document.getElementById("new-password").value;
        
        try {
            const res = await fetch(`${API_BASE}/reset-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, code, new_password: newPassword })
            });
            
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Reset failed");
            }
            
            alert("Password updated! You can now log in.");
            showView("auth");
        } catch (err) {
            resetError.textContent = err.message;
        }
    }
});

async function fetchUser() {
    try {
        const res = await fetch(`${API_BASE}/me`, {
            headers: { "Authorization": `Bearer ${state.token}` }
        });
        if (!res.ok) throw new Error();
        state.user = await res.json();
        userEmailSpan.textContent = state.user.email;
        return true;
    } catch {
        state.token = null;
        localStorage.removeItem("token");
        return false;
    }
}

logoutBtn.addEventListener("click", () => {
    state.token = null;
    state.user = null;
    localStorage.removeItem("token");
    showView("auth");
});

// Generator Logic
generateBtn.addEventListener("click", async () => {
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    const style = styleSelect.value;
    const fullPrompt = style !== "none" ? `${prompt}, ${style} style` : prompt;

    generateBtn.disabled = true;
    loadingContainer.classList.remove("hidden");
    imageResult.classList.add("hidden");

    try {
        const res = await fetch(`${API_BASE}/generate`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${state.token}`
            },
            body: JSON.stringify({ prompt: fullPrompt, style })
        });

        if (!res.ok) throw new Error("Failed to generate image");

        const data = await res.json();
        
        // Create a promise that resolves when the image is loaded
        const imageLoadPromise = new Promise((resolve, reject) => {
            generatedImg.onload = () => resolve();
            generatedImg.onerror = () => reject(new Error("Failed to render image"));
            generatedImg.src = data.url;
        });

        downloadBtn.href = data.url;
        
        // Wait for the image to actually load before showing the result
        await imageLoadPromise;
        
        imageResult.classList.remove("hidden");
        loadHistory();
    } catch (err) {
        alert(err.message);
    } finally {
        generateBtn.disabled = false;
        loadingContainer.classList.add("hidden");
    }
});

async function loadHistory() {
    try {
        const res = await fetch(`${API_BASE}/history`, {
            headers: { "Authorization": `Bearer ${state.token}` }
        });
        const images = await res.json();
        
        historyGrid.innerHTML = images.map(img => `
            <div class="history-item glass">
                <img src="${img.url}" alt="${img.prompt}" loading="lazy">
                <div class="history-overlay">
                    <p>${img.prompt}</p>
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("History error:", err);
    }
}

init();
