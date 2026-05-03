// app.js — Sonata frontend logic

function escapeApostrophe(text) {
    return (text || '').split("'").join("\\'");
}

function pickImage(song) {
    return song.presigned_url || song.image_url || '';
}

function buildMusicId(song) {
    return `${song.artist}#${song.title}#${song.year}#${song.album || ''}`;
}

function makeSongCard(song, actionType) {
    const card = document.createElement('div');
    card.className = 'song-card';

    const imgSrc = pickImage(song);
    const safeTitle = escapeApostrophe(song.title);
    const safeArtist = escapeApostrophe(song.artist);
    const safeAlbum = escapeApostrophe(song.album || '');
    const safeImageKey = escapeApostrophe(song.image_s3_key || '');
    const safeMusicId = escapeApostrophe(song.music_id || buildMusicId(song));

    const imgTag = imgSrc
        ? `<img class="card-img" src="${imgSrc}" alt="${song.artist}" onerror="this.style.display='none'">`
        : `<div class="card-img placeholder">♪</div>`;

    const btnClass = actionType === 'subscribe' ? 'subscribe' : 'remove';
    const btnLabel = actionType === 'subscribe' ? '+ Subscribe' : '✕ Remove';

    const btnAction = actionType === 'subscribe'
        ? `addSubscription('${safeTitle}','${safeArtist}','${song.year}','${safeAlbum}','${safeImageKey}')`
        : `removeSubscription('${safeMusicId}')`;

    card.innerHTML = `
        ${imgTag}
        <div class="card-body">
            <div class="card-title">${song.title}</div>
            <div class="card-artist">${song.artist}</div>
            <div class="card-meta">${song.year}${song.album ? ' · ' + song.album : ''}</div>
            <button class="card-btn ${btnClass}" onclick="${btnAction}">${btnLabel}</button>
        </div>
    `;
    return card;
}

function showSkeletons(container, count = 4) {
    container.innerHTML = '';
    for (let i = 0; i < count; i++) {
        container.innerHTML += `
            <div class="skeleton">
                <div class="skeleton-img"></div>
                <div class="skeleton-body">
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line short"></div>
                </div>
            </div>`;
    }
}

function showStatus(el, text, type = 'info') {
    el.textContent = text;
    el.className = `status-msg ${type}`;
    el.style.display = 'block';
}

function hideStatus(el) {
    el.style.display = 'none';
}

window.onload = function() {
    const email = sessionStorage.getItem('userEmail');
    if (!email) {
        window.location.href = 'login.html';
        return;
    }

    const usernameEl = document.getElementById('display-username');
    if (usernameEl) usernameEl.textContent = email.split('@')[0];

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            sessionStorage.removeItem('userEmail');
            window.location.href = 'login.html';
        });
    }

    loadSubscriptions(email);
};

async function loadSubscriptions(email) {
    const listEl = document.getElementById('subscription-list');
    const msgEl = document.getElementById('sub-message');
    const countEl = document.getElementById('sub-count');

    showSkeletons(listEl, 4);
    hideStatus(msgEl);

    try {
        const ts = Date.now();
        const res = await fetch(`${API_BASE_URL}/subscriptions?email=${encodeURIComponent(email)}&t=${ts}`);
        const data = await res.json();

        listEl.innerHTML = '';

        if (!data.subscriptions || data.subscriptions.length === 0) {
            if (countEl) countEl.textContent = '';
            listEl.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <div class="empty-icon">♫</div>
                    <h3>Your library is empty</h3>
                    <p>Search for songs above and subscribe to build your collection.</p>
                </div>`;
            return;
        }

        if (countEl) {
            countEl.textContent = `${data.subscriptions.length} track${data.subscriptions.length !== 1 ? 's' : ''}`;
        }

        data.subscriptions.forEach(song => {
            listEl.appendChild(makeSongCard(song, 'remove'));
        });

    } catch (err) {
        listEl.innerHTML = '';
        showStatus(msgEl, 'Failed to load your library. Please refresh.', 'error');
        console.error(err);
    }
}

window.removeSubscription = async function(music_id) {
    const email = sessionStorage.getItem('userEmail');

    try {
        const res = await fetch(API_BASE_URL + '/subscriptions', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, music_id })
        });

        if (res.ok) {
            loadSubscriptions(email);
        } else {
            alert('Failed to remove subscription.');
        }
    } catch (err) {
        console.error(err);
    }
};

document.getElementById('query-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const title = document.getElementById('q-title').value.trim();
    const artist = document.getElementById('q-artist').value.trim();
    const year = document.getElementById('q-year').value.trim();
    const album = document.getElementById('q-album').value.trim();

    const resultsSection = document.getElementById('results-section');
    const resultsEl = document.getElementById('query-results');
    const msgEl = document.getElementById('query-message');
    const countEl = document.getElementById('results-count');

    if (!title && !artist && !year && !album) {
        resultsSection.style.display = 'block';
        resultsEl.innerHTML = '';
        showStatus(msgEl, 'Please fill in at least one field to search.', 'info');
        countEl.textContent = '';
        return;
    }

    resultsSection.style.display = 'block';
    hideStatus(msgEl);
    showSkeletons(resultsEl, 4);
    countEl.textContent = 'Searching…';

    setTimeout(() => resultsSection.scrollIntoView({ behavior: 'smooth' }), 80);

    const params = new URLSearchParams();
    if (title) params.append('title', title);
    if (artist) params.append('artist', artist);
    if (year) params.append('year', year);
    if (album) params.append('album', album);

    try {
        const res = await fetch(`${API_BASE_URL}/songs?${params}`);
        const data = await res.json();

        resultsEl.innerHTML = '';

        if (!data.songs || data.songs.length === 0 ||
            (data.message && data.message.includes('No result'))) {
            countEl.textContent = '0 results';
            showStatus(msgEl, 'No result is retrieved. Please query again', 'info');
            return;
        }

        countEl.textContent = `${data.songs.length} result${data.songs.length !== 1 ? 's' : ''}`;

        data.songs.forEach((song, i) => {
            const card = makeSongCard(song, 'subscribe');
            card.style.animationDelay = (i * 0.04) + 's';
            resultsEl.appendChild(card);
        });

    } catch (err) {
        resultsEl.innerHTML = '';
        showStatus(msgEl, 'Error connecting to the search service.', 'error');
        countEl.textContent = '';
        console.error(err);
    }
});

window.addSubscription = async function(title, artist, year, album, image_s3_key) {
    const email = sessionStorage.getItem('userEmail');

    try {
        const res = await fetch(API_BASE_URL + '/subscriptions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email,
                title,
                artist,
                year,
                album,
                image_s3_key
            })
        });

        if (res.ok) {
            loadSubscriptions(email);
            document.getElementById('library-section').scrollIntoView({ behavior: 'smooth' });
        } else {
            const data = await res.json();
            alert('Failed to subscribe: ' + (data.error || data.message || 'Unknown error'));
        }
    } catch (err) {
        alert('Error subscribing to song.');
        console.error(err);
    }
};