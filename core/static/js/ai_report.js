document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('scoreChart');
    if (!ctx) return;

    // データ取得
    let score = 0;
    let averageScore = 0;
    const chartDataElement = document.getElementById('chart-data');
    if (chartDataElement) {
        try {
            const data = JSON.parse(chartDataElement.textContent);
            score = data.score;
            averageScore = data.average_score;
        } catch (e) {
            console.warn('chart data parse error:', e);
        }
    }

    new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['あなたのスコア', '平均スコア'],
            datasets: [{
                label: 'エコスコア',
                data: [score, averageScore],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(209, 213, 219, 0.8)'
                ],
                borderRadius: 8,
                barPercentage: 0.5,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: '#f3f4f6', drawBorder: false }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
});
