// CIVITAS — Vote selection logic

function selectCandidate(id, name) {
    // Deselect all
    document.querySelectorAll('.candidate-card').forEach(card => {
        card.classList.remove('selected');
    });

    // Select clicked
    const card = document.querySelector(`.candidate-card[data-id="${id}"]`);
    if (card) card.classList.add('selected');

    // Update hidden input
    document.getElementById('selectedCandidate').value = id;
    document.getElementById('candidateNameDisplay').textContent = name;

    // Show confirmation
    const confirm = document.getElementById('voteConfirm');
    confirm.style.display = 'block';
    confirm.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function clearSelection() {
    document.querySelectorAll('.candidate-card').forEach(card => card.classList.remove('selected'));
    document.getElementById('selectedCandidate').value = '';
    document.getElementById('voteConfirm').style.display = 'none';
}

// Prevent accidental back navigation after vote
window.addEventListener('pageshow', e => {
    if (e.persisted) window.location.reload();
});