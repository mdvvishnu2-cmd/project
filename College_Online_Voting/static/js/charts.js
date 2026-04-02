// CIVITAS — Results Chart

document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('resultChart');
    if (!canvas || typeof chartData === 'undefined') return;

    const goldPalette = [
        'rgba(201,168,76,0.85)',
        'rgba(232,201,109,0.75)',
        'rgba(245,233,200,0.65)',
        'rgba(156,124,40,0.75)',
        'rgba(180,150,60,0.7)',
    ];

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: chartData.labels,
            datasets: [{
                data: chartData.votes,
                backgroundColor: goldPalette,
                borderColor: 'rgba(10,15,30,0.8)',
                borderWidth: 2,
                hoverOffset: 6,
            }]
        },
        options: {
            responsive: true,
            cutout: '62%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#9ca3af',
                        font: { size: 11, family: 'DM Sans' },
                        padding: 12,
                        usePointStyle: true,
                    }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.label}: ${ctx.raw} votes`
                    }
                }
            }
        }
    });

    // Animate result bars
    setTimeout(() => {
        document.querySelectorAll('.result-bar-fill').forEach(bar => {
            bar.style.transition = 'width 1.2s cubic-bezier(0.16, 1, 0.3, 1)';
            bar.style.width = bar.dataset.width || '0%';
        });
    }, 200);
});