let timerX = null;

// /* ---- Station Search ---- */
// async function searchStations() {
//     const q = document.getElementById("searchStation").value;
//     const box = document.getElementById("station-results");
//     if (!q || q.length < 2) {
//         box.innerHTML = "";
//         return;
//     }

//     if (timerX) clearTimeout(timerX);
//     timerX = setTimeout(async () => {
//         const res = await fetch(`/api/search/station?q=${encodeURIComponent(q)}`);
//         const data = await res.json();
//         box.innerHTML = "";

//         (data.results || []).forEach(st => {
//             box.innerHTML += `
//                 <a class="list-group-item list-group-item-action"
//                    href="/station/${st.id}">📍 ${st.name}</a>`;
//         });
//     }, 250);
// }

/* ---- River Search ---- */
async function searchRivers() {
    const q = document.getElementById("searchRiver").value;
    const box = document.getElementById("river-results");

    if (!q || q.length < 2) {
        box.innerHTML = "";
        return;
    }

    const res = await fetch(`/api/search/river?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    box.innerHTML = "";

    (data.results || []).forEach(rv => {
        box.innerHTML += `
            <a class="list-group-item list-group-item-action"
               href="/river/${encodeURIComponent(rv.name)}">🌊 ${rv.name}</a>`;
    });
}


/* ---- State Search ---- */
async function searchStates() {
    const q = document.getElementById("searchState").value;
    const box = document.getElementById("state-results");

    if (!q || q.length < 2) {
        box.innerHTML = "";
        return;
    }

    const res = await fetch(`/api/search/state?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    box.innerHTML = "";

    (data.results || []).forEach(st => {
        box.innerHTML += `
            <a class="list-group-item list-group-item-action"
               href="/state/${encodeURIComponent(st.name)}">
               ${st.name}
            </a>`;
    });
}
