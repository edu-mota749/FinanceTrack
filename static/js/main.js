document.addEventListener("DOMContentLoaded", () => {
    const loginSection = document.getElementById("login-section");
    const registerSection = document.getElementById("register-section");
    const tabButtons = document.querySelectorAll(".tab-button");

    function setActiveTab(tab) {
        tabButtons.forEach((button) => {
            button.classList.toggle("active", button.dataset.target === tab);
        });
        loginSection.classList.toggle("active", tab === "login");
        registerSection.classList.toggle("active", tab === "register");
    }

    tabButtons.forEach((button) => {
        button.addEventListener("click", () => setActiveTab(button.dataset.target));
    });

    setActiveTab(window.selectedTab || "login");

    if (document.getElementById("lineChart")) {
        const lineCtx = document.getElementById("lineChart").getContext("2d");
        new Chart(lineCtx, {
            type: "line",
            data: {
                labels: ["01", "05", "10", "15", "20", "25", "30"],
                datasets: [
                    {
                        label: "Receitas",
                        data: [900, 2500, 3400, 4200, 5300, 6700, 7400],
                        borderColor: "#1c9a41",
                        backgroundColor: "rgba(28, 154, 65, 0.08)",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 0,
                    },
                    {
                        label: "Despesas",
                        data: [300, 1200, 2700, 3500, 4300, 5100, 4980],
                        borderColor: "#d63447",
                        backgroundColor: "rgba(214, 52, 71, 0.08)",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 0,
                    },
                    {
                        label: "Saldo Acumulado",
                        data: [600, 1300, 1300, 1300, 1000, 1600, 2440],
                        borderColor: "#fb923c",
                        borderDash: [8, 6],
                        backgroundColor: "rgba(251, 146, 60, 0.08)",
                        fill: false,
                        tension: 0.35,
                        pointRadius: 0,
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { grid: { color: "rgba(15, 33, 72, 0.08)" }, ticks: { beginAtZero: true } },
                },
            },
        });
    }

    if (document.getElementById("donutChart")) {
        const donutCtx = document.getElementById("donutChart").getContext("2d");
        new Chart(donutCtx, {
            type: "doughnut",
            data: {
                labels: ["Moradia", "Alimentação", "Educação", "Transporte", "Outros"],
                datasets: [{
                    data: [30, 25, 10, 10, 25],
                    backgroundColor: ["#1d4ed8", "#f59e0b", "#ef4444", "#2dd4bf", "#16a34a"],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                },
                cutout: "72%",
            },
        });
    }
});
