const db = firebase.firestore();

async function loadRaces() {
    const snap = await db.collection("races").get();
    let html = "";

    snap.forEach(doc => {
        const r = doc.data();
        html += `<option value="${doc.id}">${r.date} ${r.name}</option>`;
    });

    document.getElementById("race-select").innerHTML = html;
}

document.getElementById("go-btn").addEventListener("click", () => {
    const raceId = document.getElementById("race-select").value;
    window.location.href = `/admin/entry/edit?raceId=${raceId}`;
});

loadRaces();
