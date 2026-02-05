document.addEventListener('DOMContentLoaded', function() {
    // データ取得
    var stores = [];
    const storesDataElement = document.getElementById('stores-data');
    if (storesDataElement) {
        try {
            stores = JSON.parse(storesDataElement.textContent);
        } catch (e) {
            console.warn('stores_json parse error:', e);
        }
    }

    // マップ初期化
    const mapElement = document.getElementById('map');
    if (!mapElement) return; // マップ要素がなければ終了

    var map = L.map('map', {
        zoomControl: false 
    }).setView([35.6895, 139.6917], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    
    L.control.zoom({ position: 'topright' }).addTo(map);
    
    let currentMarker = null;
    let currentCircle = null;
    let currentPosition = null;
    
    const currentLocationIcon = L.divIcon({
        html: '<div style="width:20px;height:20px;background:#22c55e;border:3px solid white;border-radius:50%;box-shadow:0 0 8px rgba(0,0,0,0.3);"></div>',
        className: 'current-loc-icon',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });

    function showCurrentLocation(lat, lon, accuracy) {
        if (currentMarker) map.removeLayer(currentMarker);
        if (currentCircle) map.removeLayer(currentCircle);
    
        currentMarker = L.marker([lat, lon], { icon: currentLocationIcon }).addTo(map);
        currentCircle = L.circle([lat, lon], {
            radius: accuracy,
            color: '#22c55e',
            fillColor: '#22c55e',
            fillOpacity: 0.15,
            weight: 1
        }).addTo(map);
    }
    
    function moveToCurrentLocation() {
        if (currentPosition) {
            map.flyTo(currentPosition, 16, { animate: true, duration: 0.8 });
        } else {
            alert('現在地を取得中です。少しお待ちください。');
        }
    }
    
    if (navigator.geolocation) {
        navigator.geolocation.watchPosition(
            function (pos) {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                const acc = pos.coords.accuracy;
                if (!currentPosition || Math.abs(currentPosition[0] - lat) > 0.00005 || Math.abs(currentPosition[1] - lon) > 0.00005) {
                    currentPosition = [lat, lon];
                    showCurrentLocation(lat, lon, acc);
                }
            },
            function (err) { console.warn('位置情報取得エラー:', err); },
            { enableHighAccuracy: true, maximumAge: 5000, timeout: 5000 }
        );
    }
    
    const LocateControl = L.Control.extend({
        options: { position: 'topright' },
        onAdd: function(map) {
            const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
            container.style.backgroundColor = 'white';
            container.style.width = '40px';
            container.style.height = '40px';
            container.style.display = 'flex';
            container.style.alignItems = 'center';
            container.style.justifyContent = 'center';
            container.style.cursor = 'pointer';
            container.style.borderRadius = '50%'; 
            container.style.marginBottom = '10px';
            container.style.boxShadow = '0 4px 6px rgba(0,0,0,0.15)';
            container.innerHTML = '<span style="font-size:20px;">📍</span>';
            container.title = "現在地へ移動";
            
            // onclick property assignment in JS is safe for CSP
            container.onclick = function(e){ e.preventDefault(); moveToCurrentLocation(); };
            
            L.DomEvent.disableClickPropagation(container);
            return container;
        }
    });
    map.addControl(new LocateControl());
    
    const storeIcon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    var markersLayer = L.layerGroup().addTo(map);

    function renderMarkers(filteredStores) {
        markersLayer.clearLayers();
        const categoryMap = { 'restaurant': '飲食店', 'retail': '小売店', 'service': 'サービス業', 'other': 'その他' };

        filteredStores.forEach(function (s) {
            if (s.fields.lat && s.fields.lng && s.fields.lat !== 0 && s.fields.lng !== 0) {
                var open_time = s.fields.open_time ? s.fields.open_time.substring(0, 5) : '';
                var close_time = s.fields.close_time ? s.fields.close_time.substring(0, 5) : '';
                var hours = (open_time && close_time) ? `${open_time} - ${close_time}` : '営業時間情報なし';
                var categoryLabel = categoryMap[s.fields.category] || s.fields.category;

                var popupContent = `
                        <div class="store-popup">
                            <div class="store-name">${s.fields.store_name}</div>
                            <div class="info-row"><span class="info-label">カテゴリ:</span> ${categoryLabel}</div>
                            <div class="info-row"><span class="info-label">住所:</span> ${s.fields.address}</div>
                            <div class="info-row"><span class="info-label">電話:</span> ${s.fields.tel || '－'}</div>
                            <div class="info-row"><span class="info-label">時間:</span> ${hours}</div>
                        </div>`;
                L.marker([s.fields.lat, s.fields.lng], {icon: storeIcon}).bindPopup(popupContent).addTo(markersLayer);
            }
        });
    }

    function filterMarkers() {
        const keywordInput = document.getElementById('keyword-input');
        const categorySelect = document.getElementById('category-select');
        
        const keyword = keywordInput ? keywordInput.value.toLowerCase() : '';
        const category = categorySelect ? categorySelect.value : '';
        
        const filtered = stores.filter(function(s) {
            const matchKeyword = !keyword || s.fields.store_name.toLowerCase().includes(keyword);
            const matchCategory = !category || s.fields.category === category;
            return matchKeyword && matchCategory;
        });
        renderMarkers(filtered);
    }

    function initAutocomplete() {
        const datalist = document.getElementById('store-names');
        if (!datalist) return;
        
        const uniqueNames = new Set(stores.map(s => s.fields.store_name));
        uniqueNames.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            datalist.appendChild(option);
        });
    }

    renderMarkers(stores);
    initAutocomplete();
    
    // イベントリスナー設定
    const keywordInput = document.getElementById('keyword-input');
    if (keywordInput) keywordInput.addEventListener('input', filterMarkers);
    
    const categorySelect = document.getElementById('category-select');
    if (categorySelect) categorySelect.addEventListener('change', filterMarkers);

    const filterButton = document.getElementById('filter-button');
    if (filterButton) filterButton.addEventListener('click', filterMarkers);

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function (pos) {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                currentPosition = [lat, lon];
                showCurrentLocation(lat, lon, pos.coords.accuracy);
                map.setView([lat, lon], 14, { animate: true });
            },
            function (err) { console.warn('初回位置取得エラー:', err); },
            { enableHighAccuracy: true, timeout: 5000 }
        );
    }
    
    setTimeout(function(){ map.invalidateSize(); }, 200);
});
