/* ═══════════════════════════════════════════════════════════════════
   RTLS Indoor Asset Locator — Search-First Client Engine
   Search, Contextual Neighborhood Map & Real-Time Indoor Navigation
   ═══════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    // ── Topology & Constants ──────────────────────────────────────────
    const ROOM_NODES = {
        "Room A (ICU Bedroom 1)":     { id: "room_a", short: "Room A (ICU)",       x: 0.28, y: 0.30, color: "#89b4fa" },
        "Room B (Patient Bedroom 2)": { id: "room_b", short: "Room B (Patient)",   x: 0.72, y: 0.30, color: "#a6e3a1" },
        "Room C (Medical Station)":   { id: "room_c", short: "Room C (Medical)",   x: 0.28, y: 0.70, color: "#fab387" },
        "Room D (Emergency Ward)":    { id: "room_d", short: "Room D (Emergency)", x: 0.72, y: 0.70, color: "#f38ba8" },
    };

    const ADJACENCY = {
        "Room A (ICU Bedroom 1)":     ["Room B (Patient Bedroom 2)", "Room C (Medical Station)"],
        "Room B (Patient Bedroom 2)": ["Room A (ICU Bedroom 1)", "Room D (Emergency Ward)"],
        "Room C (Medical Station)":   ["Room A (ICU Bedroom 1)", "Room D (Emergency Ward)"],
        "Room D (Emergency Ward)":    ["Room B (Patient Bedroom 2)", "Room C (Medical Station)"],
    };

    // ── Application State ──────────────────────────────────────────────
    let state = {
        userRoom: "Room A (ICU Bedroom 1)",
        searchQuery: "",
        activeFilter: "all",
        searchResults: [],
        nearbyAssets: [],
        allAssets: [],
        liveTags: {},
        wsConnected: false,
        selectedAsset: null,
    };

    let ws = null;
    let searchDebounceTimer = null;

    // ── DOM Elements ───────────────────────────────────────────────────
    const userRoomSelect = document.getElementById("userRoomSelect");
    const searchInput = document.getElementById("searchInput");
    const searchClearBtn = document.getElementById("searchClearBtn");
    const filterChips = document.querySelectorAll(".chip");
    const searchResultsSection = document.getElementById("searchResultsSection");
    const searchResultsTitle = document.getElementById("searchResultsTitle");
    const searchResultsCount = document.getElementById("searchResultsCount");
    const searchResultsList = document.getElementById("searchResultsList");
    const defaultDashboard = document.getElementById("defaultDashboard");
    const nearbyList = document.getElementById("nearbyList");
    const nearbyCount = document.getElementById("nearbyCount");
    const wsStatusPill = document.getElementById("wsStatusPill");
    const wsStatusText = document.getElementById("wsStatusText");
    const alertBanner = document.getElementById("alertBanner");
    const alertMessage = document.getElementById("alertMessage");
    const alertDismiss = document.getElementById("alertDismiss");
    
    // Canvas Map
    const mapCanvas = document.getElementById("contextMapCanvas");
    const ctx = mapCanvas ? mapCanvas.getContext("2d") : null;

    // Modal
    const modalOverlay = document.getElementById("assetModalOverlay");
    const modalCloseBtn = document.getElementById("modalCloseBtn");
    const modalIcon = document.getElementById("modalIcon");
    const modalTitle = document.getElementById("modalTitle");
    const modalDept = document.getElementById("modalDept");
    const modalRoom = document.getElementById("modalRoom");
    const modalProximity = document.getElementById("modalProximity");
    const modalLastSeen = document.getElementById("modalLastSeen");
    const modalType = document.getElementById("modalType");
    const modalMac = document.getElementById("modalMac");
    const modalCoords = document.getElementById("modalCoords");
    const modalRouteStep = document.getElementById("modalRouteStep");

    // ── Initialization ─────────────────────────────────────────────────
    function init() {
        // Event Listeners
        userRoomSelect.addEventListener("change", (e) => {
            state.userRoom = e.target.value;
            onUserRoomChanged();
        });

        searchInput.addEventListener("input", (e) => {
            state.searchQuery = e.target.value;
            if (state.searchQuery.trim().length > 0) {
                searchClearBtn.classList.remove("hidden");
            } else {
                searchClearBtn.classList.add("hidden");
            }
            debounceSearch();
        });

        searchClearBtn.addEventListener("click", () => {
            searchInput.value = "";
            state.searchQuery = "";
            searchClearBtn.classList.add("hidden");
            performSearch();
        });

        filterChips.forEach((chip) => {
            chip.addEventListener("click", () => {
                filterChips.forEach((c) => c.classList.remove("active"));
                chip.classList.add("active");
                state.activeFilter = chip.dataset.filter;
                performSearch();
            });
        });

        alertDismiss.addEventListener("click", () => {
            alertBanner.classList.add("hidden");
        });

        modalCloseBtn.addEventListener("click", closeModal);
        modalOverlay.addEventListener("click", (e) => {
            if (e.target === modalOverlay) closeModal();
        });

        window.addEventListener("resize", resizeMapCanvas);

        // Initial Data Fetch
        fetchNearbyAssets();
        connectWebSocket();
        resizeMapCanvas();
        requestAnimationFrame(renderMapLoop);
    }

    // ── Search Logic ───────────────────────────────────────────────────
    function debounceSearch() {
        if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(performSearch, 150);
    }

    async function performSearch() {
        const query = state.searchQuery.trim();

        if (!query && state.activeFilter === "all") {
            // Show default neighborhood dashboard
            searchResultsSection.classList.add("hidden");
            defaultDashboard.classList.remove("hidden");
            fetchNearbyAssets();
            return;
        }

        // Show Search Results view
        defaultDashboard.classList.add("hidden");
        searchResultsSection.classList.remove("hidden");

        try {
            let url = `/api/search?q=${encodeURIComponent(query)}&user_room=${encodeURIComponent(state.userRoom)}`;
            const res = await fetch(url);
            if (!res.ok) throw new Error("Search request failed");
            const data = await res.json();

            let results = data.results || [];

            // Apply category filter if active
            if (state.activeFilter !== "all") {
                results = results.filter(
                    (r) => r.asset.type === state.activeFilter
                );
            }

            state.searchResults = results;
            renderSearchResults(query, results);
        } catch (err) {
            console.error("Search error:", err);
            searchResultsList.innerHTML = `<p class="section-desc">Search failed. Server offline?</p>`;
        }
    }

    function renderSearchResults(query, results) {
        searchResultsTitle.textContent = query
            ? `Search Results for "${query}"`
            : `Filtered Assets (${state.activeFilter})`;
        searchResultsCount.textContent = `${results.length} found`;

        if (results.length === 0) {
            searchResultsList.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-dim);">
                    <div style="font-size: 32px; margin-bottom: 8px;">🔎</div>
                    <p style="font-weight: 600;">No assets found matching your query.</p>
                    <p style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Try searching for "ECG", "Printer", "John", "Wheelchair", or "ICU".</p>
                </div>`;
            return;
        }

        let html = "";
        results.forEach((r) => {
            const a = r.asset;
            const proxClass =
                r.distance_rooms === 0
                    ? "same-room"
                    : r.distance_rooms === 1
                    ? "adjacent"
                    : "far";

            const proxText =
                r.distance_rooms === 0
                    ? "📍 Same room"
                    : r.distance_rooms === 1
                    ? "🚶 Adjacent room"
                    : `🚶 ${r.distance_rooms} rooms away`;

            const lastSeenText = r.last_seen_seconds
                ? `${r.last_seen_seconds}s ago`
                : "Active";

            html += `
                <div class="result-card" data-asset-id="${a.id}">
                    <div class="result-header">
                        <div class="result-icon">${r.icon || "📦"}</div>
                        <div class="result-main">
                            <div class="result-name">${a.name}</div>
                            <div class="result-dept">${a.department || a.type} • Floor ${a.floor || 1}</div>
                        </div>
                    </div>
                    <div class="result-details">
                        <div class="detail-row">
                            <span class="lbl">Location:</span>
                            <span class="val highlight">${r.live_room || a.room}</span>
                        </div>
                        <div class="detail-row">
                            <span class="lbl">Proximity:</span>
                            <span class="val"><span class="proximity-tag ${proxClass}">${proxText}</span></span>
                        </div>
                        <div class="detail-row">
                            <span class="lbl">Last seen:</span>
                            <span class="val">${lastSeenText}</span>
                        </div>
                    </div>
                    <button class="route-btn" onclick="window.openAssetModal('${a.id}')">
                        🗺️ SHOW ROUTE & DETAILS
                    </button>
                </div>`;
        });

        searchResultsList.innerHTML = html;
    }

    // ── Nearby Assets Fetching ─────────────────────────────────────────
    async function fetchNearbyAssets() {
        try {
            const url = `/api/nearby?room=${encodeURIComponent(state.userRoom)}&max_distance=2`;
            const res = await fetch(url);
            if (!res.ok) return;
            const data = await res.json();
            state.nearbyAssets = data.nearby || [];
            renderNearbyList(state.nearbyAssets);
        } catch (err) {
            console.error("Nearby assets fetch error:", err);
        }
    }

    function renderNearbyList(items) {
        nearbyCount.textContent = items.length;

        if (items.length === 0) {
            nearbyList.innerHTML = `<p class="section-desc">No assets nearby.</p>`;
            return;
        }

        let html = "";
        items.forEach((r) => {
            const a = r.asset;
            const proxClass =
                r.distance_rooms === 0
                    ? "same-room"
                    : r.distance_rooms === 1
                    ? "adjacent"
                    : "far";

            html += `
                <div class="nearby-item" onclick="window.openAssetModal('${a.id}')">
                    <div class="item-icon">${r.icon || "📦"}</div>
                    <div class="item-info">
                        <div class="item-name">${a.name}</div>
                        <div class="item-location">${r.live_room || a.room}</div>
                    </div>
                    <span class="proximity-tag ${proxClass}">${r.proximity_label}</span>
                </div>`;
        });
        nearbyList.innerHTML = html;
    }

    function onUserRoomChanged() {
        fetchNearbyAssets();
        if (state.searchQuery.trim().length > 0) {
            performSearch();
        }
    }

    // ── Contextual Local Map Canvas Renderer ───────────────────────────
    function resizeMapCanvas() {
        if (!mapCanvas) return;
        const rect = mapCanvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        mapCanvas.width = rect.width * dpr;
        mapCanvas.height = rect.height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function renderMapLoop() {
        if (mapCanvas && ctx) {
            drawContextualMap();
        }
        requestAnimationFrame(renderMapLoop);
    }

    function drawContextualMap() {
        const w = mapCanvas.parentElement.clientWidth;
        const h = mapCanvas.parentElement.clientHeight;

        ctx.clearRect(0, 0, w, h);

        // Draw background grid
        ctx.strokeStyle = "#313244";
        ctx.lineWidth = 0.5;
        const step = 30;
        for (let x = 0; x < w; x += step) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, h);
            ctx.stroke();
        }
        for (let y = 0; y < h; y += step) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        // Draw Room Connections (Corridor connections between adjacent rooms)
        ctx.strokeStyle = "#45475a";
        ctx.lineWidth = 4;
        ctx.setLineDash([6, 6]);

        Object.entries(ADJACENCY).forEach(([roomName, adjRooms]) => {
            const r1 = ROOM_NODES[roomName];
            if (!r1) return;
            adjRooms.forEach((adjName) => {
                const r2 = ROOM_NODES[adjName];
                if (!r2) return;
                ctx.beginPath();
                ctx.moveTo(r1.x * w, r1.y * h);
                ctx.lineTo(r2.x * w, r2.y * h);
                ctx.stroke();
            });
        });
        ctx.setLineDash([]);

        // Draw Room Nodes
        Object.entries(ROOM_NODES).forEach(([roomName, node]) => {
            const cx = node.x * w;
            const cy = node.y * h;
            const isUserRoom = roomName === state.userRoom;
            const isAdjacent = ADJACENCY[state.userRoom]?.includes(roomName);

            const cardW = 150;
            const cardH = 90;
            const rx = cx - cardW / 2;
            const ry = cy - cardH / 2;

            // Box styling based on user proximity
            if (isUserRoom) {
                ctx.fillStyle = "#181825";
                ctx.strokeStyle = "#89b4fa";
                ctx.lineWidth = 3;
                ctx.shadowColor = "rgba(137,180,250,0.4)";
                ctx.shadowBlur = 15;
            } else if (isAdjacent) {
                ctx.fillStyle = "#181825";
                ctx.strokeStyle = "#a6e3a1";
                ctx.lineWidth = 2;
                ctx.shadowBlur = 0;
            } else {
                ctx.fillStyle = "#181825";
                ctx.strokeStyle = "#45475a";
                ctx.lineWidth = 1;
                ctx.shadowBlur = 0;
            }

            // Rounded rectangle room card
            drawRoundedRect(ctx, rx, ry, cardW, cardH, 10);
            ctx.fill();
            ctx.stroke();
            ctx.shadowBlur = 0;

            // Room Title
            ctx.font = "bold 13px Inter, sans-serif";
            ctx.fillStyle = isUserRoom
                ? "#89b4fa"
                : isAdjacent
                ? "#a6e3a1"
                : "#a6adc8";
            ctx.textAlign = "center";
            ctx.fillText(node.short, cx, ry + 22);

            // YOU indicator badge if user is here
            if (isUserRoom) {
                ctx.fillStyle = "#89b4fa";
                ctx.font = "bold 10px Inter, sans-serif";
                ctx.fillText("📍 YOU ARE HERE", cx, ry + 38);
            }

            // Count assets in this room
            const assetsInRoom = state.nearbyAssets.filter(
                (item) => (item.live_room || item.asset.room) === roomName
            );

            // Draw asset icons inside room node
            ctx.font = "12px Inter, sans-serif";
            ctx.fillStyle = "#cdd6f4";
            const iconsStr = assetsInRoom
                .map((i) => i.icon || "📦")
                .slice(0, 5)
                .join(" ");
            ctx.fillText(
                iconsStr || (isUserRoom ? "Empty" : "No items"),
                cx,
                ry + (isUserRoom ? 62 : 54)
            );

            if (assetsInRoom.length > 5) {
                ctx.font = "9px Inter, sans-serif";
                ctx.fillStyle = "#6c7086";
                ctx.fillText(`+${assetsInRoom.length - 5} more`, cx, ry + 76);
            }
        });

        // Draw live tag position overlays inside rooms if available
        Object.values(state.liveTags).forEach((tag) => {
            if (!tag.position) return;
            const roomName = tag.room || tag.position.room;
            const node = ROOM_NODES[roomName];
            if (!node) return;

            // Offset tag slightly inside the room box
            const cx = node.x * w + (tag.position.x % 2 - 1) * 20;
            const cy = node.y * h + (tag.position.y % 2 - 1) * 20;

            ctx.beginPath();
            ctx.arc(cx, cy, 6, 0, Math.PI * 2);
            ctx.fillStyle = "#f38ba8";
            ctx.fill();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.5;
            ctx.stroke();
        });
    }

    function drawRoundedRect(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }

    // ── Asset Detail Modal & Route Guidance ────────────────────────────
    window.openAssetModal = async function (assetId) {
        try {
            const res = await fetch(`/api/assets/${assetId}`);
            if (!res.ok) throw new Error("Asset not found");
            const assetData = await res.json();
            state.selectedAsset = assetData;

            modalIcon.textContent = getIconForType(assetData.type);
            modalTitle.textContent = assetData.name;
            modalDept.textContent = assetData.department || assetData.type;
            
            const currentRoom = assetData.live_room || assetData.room || "Unknown";
            modalRoom.textContent = currentRoom;
            modalType.textContent = assetData.type;
            modalMac.textContent = assetData.ble_mac || "Not assigned";

            if (assetData.last_seen_seconds !== undefined) {
                modalLastSeen.textContent = `${assetData.last_seen_seconds}s ago (Live)`;
            } else {
                modalLastSeen.textContent = "Offline / Static";
            }

            if (assetData.live_position) {
                modalCoords.textContent = `(${assetData.live_position.x}m, ${assetData.live_position.y}m) GDOP: ${assetData.live_position.gdop}`;
            } else {
                modalCoords.textContent = "—";
            }

            // Proximity & Route Step Guidance
            const isSameRoom = currentRoom === state.userRoom;
            if (isSameRoom) {
                modalProximity.textContent = "📍 Same Room as You";
                modalProximity.className = "detail-val highlight";
                modalRouteStep.innerHTML = `
                    <div style="color: var(--green); font-weight:600;">
                        ✓ This asset is right here in your current room (<strong>${state.userRoom}</strong>).
                    </div>`;
            } else {
                const isAdj = ADJACENCY[state.userRoom]?.includes(currentRoom);
                if (isAdj) {
                    modalProximity.textContent = "🚶 1 Room Away (Adjacent)";
                    modalProximity.className = "detail-val";
                    modalRouteStep.innerHTML = `
                        <div>1. Exit <strong>${state.userRoom}</strong> into main corridor.</div>
                        <div>2. Walk straight to adjacent <strong>${currentRoom}</strong>.</div>
                        <div>3. Asset <strong>${assetData.name}</strong> is inside.</div>`;
                } else {
                    modalProximity.textContent = "🚶 2 Rooms Away";
                    modalProximity.className = "detail-val";
                    modalRouteStep.innerHTML = `
                        <div>1. Exit <strong>${state.userRoom}</strong> into corridor.</div>
                        <div>2. Pass nearby connecting wing.</div>
                        <div>3. Enter <strong>${currentRoom}</strong> to locate <strong>${assetData.name}</strong>.</div>`;
                }
            }

            modalOverlay.classList.remove("hidden");
        } catch (err) {
            console.error("Modal error:", err);
        }
    };

    function closeModal() {
        modalOverlay.classList.add("hidden");
        state.selectedAsset = null;
    }

    function getIconForType(type) {
        const map = {
            medical_equipment: "🩺",
            mobility: "♿",
            staff: "👤",
            patient: "🏥",
            office_equipment: "🖨️",
            supply_cart: "🛒",
        };
        return map[type] || "📦";
    }

    // ── WebSocket Real-Time Listener ───────────────────────────────────
    function connectWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            ws = new WebSocket(wsUrl);
            ws.onopen = () => {
                state.wsConnected = true;
                wsStatusPill.className = "status-pill connected";
                wsStatusText.textContent = "Live";
            };

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.event === "position_update" && msg.data) {
                        if (msg.data.tags) {
                            state.liveTags = msg.data.tags;
                        }
                        if (msg.data.alert) {
                            showAlertBanner(msg.data.alert);
                        }
                    }
                } catch (e) {
                    console.warn("WS parse error:", e);
                }
            };

            ws.onclose = () => {
                state.wsConnected = false;
                wsStatusPill.className = "status-pill disconnected";
                wsStatusText.textContent = "Offline";
                setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = () => {
                state.wsConnected = false;
            };
        } catch (e) {
            console.warn("WS connect fail:", e);
        }
    }

    function showAlertBanner(alert) {
        if (!alert || !alert.message) return;
        alertMessage.textContent = `[${alert.patient || "ALERT"}] ${alert.message}`;
        alertBanner.classList.remove("hidden");
    }

    // Initialize on DOM Ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
