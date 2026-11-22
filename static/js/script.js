document.addEventListener("DOMContentLoaded", function () {
    // Tanggal pada topbar
    const dateElement = document.getElementById("currentDate");

    if (dateElement) {
        dateElement.textContent = new Date().toLocaleDateString("id-ID", {
            day: "2-digit",
            month: "short",
            year: "numeric"
        });
    }

    // Toggle sidebar untuk perangkat kecil
    const menuToggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("sidebar");

    if (menuToggle && sidebar) {
        menuToggle.addEventListener("click", function () {
            sidebar.classList.toggle("show");
        });
    }
});

const chartTextColor = "#8794ad";
const chartGridColor = "rgba(148, 163, 184, 0.10)";

function createChartOptions(titleText = "") {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            intersect: false,
            mode: "index"
        },
        plugins: {
            legend: {
                labels: {
                    color: chartTextColor,
                    usePointStyle: true,
                    boxWidth: 8,
                    padding: 18,
                    font: {
                        family: "DM Sans",
                        size: 10
                    }
                }
            },
            tooltip: {
                backgroundColor: "#202c43",
                titleColor: "#ffffff",
                bodyColor: "#dce5f5",
                borderColor: "rgba(148, 163, 184, .2)",
                borderWidth: 1,
                padding: 11
            },
            title: {
                display: false,
                text: titleText
            }
        },
        scales: {
            x: {
                ticks: {
                    color: chartTextColor,
                    maxTicksLimit: 10,
                    font: { size: 10 }
                },
                grid: {
                    color: chartGridColor
                }
            },
            y: {
                beginAtZero: true,
                ticks: {
                    color: chartTextColor,
                    font: { size: 10 }
                },
                grid: {
                    color: chartGridColor
                }
            }
        }
    };
}

function renderDemandChart(labels, values) {
    const canvas = document.getElementById("demandChart");

    if (!canvas || !labels.length) return;

    new Chart(canvas, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Permintaan Harian",
                data: values,
                borderColor: "#8b7cff",
                backgroundColor: "rgba(139, 124, 255, .12)",
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: true,
                tension: 0.35
            }]
        },
        options: createChartOptions()
    });
}

function findValue(row, possibleNames) {
    if (!row) return undefined;

    const keys = Object.keys(row);
    const normalized = {};

    keys.forEach(key => {
        normalized[key.toLowerCase().replace(/[^a-z0-9]/g, "")] = row[key];
    });

    for (const name of possibleNames) {
        const key = name.toLowerCase().replace(/[^a-z0-9]/g, "");
        if (normalized[key] !== undefined) {
            return normalized[key];
        }
    }

    return undefined;
}

function renderSimulationChart(rows) {
    const canvas = document.getElementById("simulationChart");

    if (!canvas || !rows || !rows.length) return;

    const labels = rows.map((row, index) =>
        findValue(row, ["Date", "Period", "Day", "Step"]) ?? (index + 1)
    );

    const stockValues = rows.map(row =>
        Number(findValue(row, [
            "Ending Stock",
            "ending_stock",
            "Stock",
            "Inventory",
            "Remaining Stock"
        ]) ?? 0)
    );

    const demandValues = rows.map(row =>
        Number(findValue(row, ["Demand", "demand"]) ?? 0)
    );

    new Chart(canvas, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Stok Akhir",
                    data: stockValues,
                    borderColor: "#4c9cff",
                    backgroundColor: "rgba(76, 156, 255, .08)",
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.3
                },
                {
                    label: "Permintaan",
                    data: demandValues,
                    borderColor: "#f5a64a",
                    backgroundColor: "rgba(245, 166, 74, .08)",
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.3
                }
            ]
        },
        options: createChartOptions()
    });
}

function renderComparisonChart(rows) {
    const canvas = document.getElementById("comparisonChart");

    if (!canvas || !rows || !rows.length) return;

    const labels = rows.map(row =>
        findValue(row, ["Method", "Metode", "Strategy", "Policy"]) ?? "Metode"
    );

    const costs = rows.map(row =>
        Number(findValue(row, ["Total Cost", "total_cost", "Cost", "Biaya"]) ?? 0)
    );

    const fillRates = rows.map(row =>
        Number(findValue(row, ["Fill Rate", "fill_rate"]) ?? 0)
    );

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Total Biaya (£)",
                    data: costs,
                    backgroundColor: "rgba(139, 124, 255, .75)",
                    borderRadius: 6,
                    yAxisID: "y"
                },
                {
                    label: "Fill Rate (%)",
                    data: fillRates,
                    backgroundColor: "rgba(41, 201, 139, .75)",
                    borderRadius: 6,
                    yAxisID: "y1"
                }
            ]
        },
        options: {
            ...createChartOptions(),
            scales: {
                x: {
                    ticks: { color: chartTextColor },
                    grid: { color: chartGridColor }
                },
                y: {
                    beginAtZero: true,
                    position: "left",
                    title: {
                        display: true,
                        text: "Biaya (£)",
                        color: chartTextColor
                    },
                    ticks: { color: chartTextColor },
                    grid: { color: chartGridColor }
                },
                y1: {
                    beginAtZero: true,
                    max: 100,
                    position: "right",
                    title: {
                        display: true,
                        text: "Fill Rate (%)",
                        color: chartTextColor
                    },
                    ticks: { color: chartTextColor },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}

function renderTrainingChart(rows) {
    const canvas = document.getElementById("trainingChart");

    if (!canvas || !rows || !rows.length) return;

    const labels = rows.map((row, index) =>
        findValue(row, ["Episode", "episode", "Iteration"]) ?? (index + 1)
    );

    const rewards = rows.map(row =>
        Number(findValue(row, ["Reward", "reward", "Total Reward", "total_reward"]) ?? 0)
    );

    new Chart(canvas, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Reward",
                data: rewards,
                borderColor: "#29c98b",
                backgroundColor: "rgba(41, 201, 139, .10)",
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.25
            }]
        },
        options: createChartOptions()
    });
}