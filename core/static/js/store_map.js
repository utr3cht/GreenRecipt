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
            // 現在地がない場合、再度取得を試みる
            if (navigator.geolocation) {
                alert('現在地を取得中です...');
                navigator.geolocation.getCurrentPosition(
                    function(pos) {
                        onGeoSuccess(pos);
                    },
                    function(err) {
                        onGeoError(err);
                    },
                    geoOptions
                );
            } else {
                alert('お使いのブラウザは位置情報をサポートしていません。');
            }
        }
    }
    
    // 旧 watchPosition ブロックを削除 (initブロックに統合済み)
    
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
    // イベントリスナー設定
    const keywordInput = document.getElementById('keyword-input');
    if (keywordInput) keywordInput.addEventListener('input', filterMarkers);
    
    const categorySelect = document.getElementById('category-select');
    if (categorySelect) categorySelect.addEventListener('change', filterMarkers);

    const filterButton = document.getElementById('filter-button');
    if (filterButton) filterButton.addEventListener('click', filterMarkers);

    // 位置情報取得のオプション設定
    // スマホの個体差（GPS起動の遅さなど）に対応するため、タイムアウトを長めに設定
    const geoOptions = {
        enableHighAccuracy: true, // 高精度を要求
        timeout: 15000,           // 15秒（以前は5秒だったが、GPS測位に時間がかかる端末に対応）
        maximumAge: 10000         // 10秒以内のキャッシュを許容
    };

    function onGeoSuccess(pos) {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        const acc = pos.coords.accuracy;
        
        // 初回のみ移動、または大きく動いた場合のみ移動するロジックは維持
        if (!currentPosition) {
            currentPosition = [lat, lon];
            showCurrentLocation(lat, lon, acc);
            map.setView([lat, lon], 14, { animate: true });
            // 初回取得成功のフィードバック（必要なら）
            // console.log(`位置情報取得成功: 精度 ${acc}m`);
        } else {
            // 移動更新
            if (Math.abs(currentPosition[0] - lat) > 0.00005 || Math.abs(currentPosition[1] - lon) > 0.00005) {
                currentPosition = [lat, lon];
                showCurrentLocation(lat, lon, acc);
            }
        }
    }

    function onGeoError(err) {
        console.warn('位置情報取得エラー:', err);
        let errorMsg = '現在地を取得できませんでした。';
        switch(err.code) {
            case err.PERMISSION_DENIED:
                errorMsg = '位置情報の利用が許可されていません。設定をご確認ください。';
                break;
            case err.POSITION_UNAVAILABLE:
                errorMsg = '位置情報が利用できません。電波状況の良い場所で再度お試しください。';
                break;
            case err.TIMEOUT:
                errorMsg = '位置情報の取得がタイムアウトしました。';
                break;
        }
        // ユーザーに通知（頻繁に出ないように制御するか、初回のみAlertなどが望ましいが、デバッグのため表示）
        // ただし、watchPositionのエラーは頻発する可能性があるため、コンソールまたはToast通知がベター。
        // ここでは、ユーザーが明示的に現在地ボタンを押したわけではない自動取得のエラーなので、
        // 控えめにコンソールに出すか、一度だけ表示するなどの工夫が必要。
        // 今回は「スマホによって個体差がある」とのことで、原因特定のため明確にエラーを出す。
        if (!currentPosition) { // まだ一度も取れていない場合のみ通知
             alert(errorMsg + ` (Code: ${err.code}, Message: ${err.message})`);
        }
    }

    // 初回取得（getCurrentPositionはタイムアウトまで待つ）
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            onGeoSuccess,
            onGeoError, // 初回のエラーは表示する
            geoOptions
        );

        // 継続監視
        const watchId = navigator.geolocation.watchPosition(
            onGeoSuccess,
            function(err) {
                console.warn('位置情報監視エラー:', err);
                 // 監視中のエラーはAlertを出さない（うっとうしいため）
            },
            geoOptions
        );
    } else {
        alert('お使いのブラウザは位置情報をサポートしていません。');
    }
    
    setTimeout(function(){ map.invalidateSize(); }, 200);
});
