const statusMessage = document.getElementById("statusMessage");
const alertButton = document.getElementById("alertButton");
const coordsDisplay = document.getElementById("coordsDisplay");
const lastAlertDisplay = document.getElementById("lastAlertDisplay");
const historyTableBody = document.getElementById("historyTableBody");
const refreshHistory = document.getElementById("refreshHistory");
const trackingToggle = document.getElementById("trackingToggle");
const statusIndicator = document.getElementById("statusIndicator");
const themeToggle = document.getElementById("themeToggle");
const startTrackingBtn = document.getElementById("startTrackingBtn");
const stopTrackingBtn = document.getElementById("stopTrackingBtn");
const trackingStatus = document.getElementById("trackingStatus");
const contactEmailInput = document.getElementById("contactEmail");
const contactPhoneInput = document.getElementById("contactPhone");
const deliveryWarning = document.getElementById("deliveryWarning");
const contactNameInput = document.getElementById("contactName");
const addContactBtn = document.getElementById("addContactBtn");
const contactsTable = document.getElementById("contactsTable");

let map;
let marker;
let alertLayer;
let liveMarker;
let trackingPath;
let watchId = null;
let currentPosition = null;
let liveTrackingInterval = null;
let trackingActive = false;

const sirenAudio = document.getElementById("sirenAudio");

const setStatus = (message) => {
  if (!statusMessage) return;
  statusMessage.textContent = message;
};

const setDeliveryWarning = (message = "") => {
  if (!deliveryWarning) return;
  deliveryWarning.textContent = message;
};

const renderContacts = (contacts) => {
  if (!contactsTable) return;
  if (!contacts.length) {
    contactsTable.innerHTML = '<tr class="empty-row"><td colspan="3">No contacts added.</td></tr>';
    return;
  }

  contactsTable.innerHTML = contacts
    .map(
      (contact) => `
        <tr>
          <td>${contact.name || "-"}</td>
          <td>${contact.email || ""}</td>
          <td>${contact.phone || ""}</td>
        </tr>
      `
    )
    .join("");
};

const loadContacts = async () => {
  const response = await fetch("/get_contacts");
  const contacts = await response.json();
  renderContacts(contacts || []);
};

const addContact = async () => {
  const name = contactNameInput ? contactNameInput.value.trim() : "";
  const email = contactEmailInput ? contactEmailInput.value.trim() : "";
  const phone = contactPhoneInput ? contactPhoneInput.value.trim() : "";

  if (!name) {
    setDeliveryWarning("Name is required to add a contact.");
    return;
  }

  if (!email && !phone) {
    setDeliveryWarning("Add at least an email or phone.");
    return;
  }

  const response = await fetch("/add_contact", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, phone }),
  });

  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const data = await response.json();
      setDeliveryWarning(data.message || "Unable to add contact.");
    } else {
      setDeliveryWarning("Unable to add contact.");
    }
    return;
  }

  if (contactNameInput) contactNameInput.value = "";
  if (contactEmailInput) contactEmailInput.value = "";
  if (contactPhoneInput) contactPhoneInput.value = "";
  setDeliveryWarning("Contact added successfully.");
  await loadContacts();
};

const setIndicator = (mode) => {
  if (!statusIndicator) return;
  if (mode === "emergency") {
    statusIndicator.textContent = "Emergency Mode";
    statusIndicator.classList.remove("safe");
    statusIndicator.classList.add("emergency");
  } else {
    statusIndicator.textContent = "Safe Mode";
    statusIndicator.classList.remove("emergency");
    statusIndicator.classList.add("safe");
  }
};

const initTheme = () => {
  const savedTheme = localStorage.getItem("sea-theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
};

const toggleTheme = () => {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("sea-theme", next);
};

const initMap = () => {
  const mapContainer = document.getElementById("map");
  if (!mapContainer) return;
  map = L.map("map").setView([37.7749, -122.4194], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  marker = L.marker([37.7749, -122.4194]).addTo(map);
  alertLayer = L.layerGroup().addTo(map);
  liveMarker = L.marker([37.7749, -122.4194]).addTo(map);
  trackingPath = L.polyline([], { color: "#23c883", weight: 3 }).addTo(map);
};

const updateMap = (lat, lng) => {
  if (!map || !marker) return;
  marker.setLatLng([lat, lng]);
  map.setView([lat, lng], 15, { animate: true });
};

const updateLiveMarker = (lat, lng) => {
  if (!map || !liveMarker) return;
  liveMarker.setLatLng([lat, lng]);
  map.setView([lat, lng], 15, { animate: true });
};

const updateTrackingPath = (points) => {
  if (!trackingPath) return;
  trackingPath.setLatLngs(points);
};

const updateAlertMarkers = (alerts) => {
  if (!map || !alertLayer) return;
  alertLayer.clearLayers();
  alerts.forEach((alert) => {
    const lat = parseFloat(alert.latitude);
    const lng = parseFloat(alert.longitude);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return;
    const popup = `${alert.timestamp}<br/>${alert.latitude}, ${alert.longitude}`;
    L.marker([lat, lng]).bindPopup(popup).addTo(alertLayer);
  });
  if (alerts.length) {
    const latest = alerts[0];
    const lat = parseFloat(latest.latitude);
    const lng = parseFloat(latest.longitude);
    if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
      map.setView([lat, lng], 14, { animate: true });
    }
  }
};

const addAlertMarker = (alert) => {
  if (!map || !alertLayer || !alert) return;
  const lat = parseFloat(alert.latitude);
  const lng = parseFloat(alert.longitude);
  if (Number.isNaN(lat) || Number.isNaN(lng)) return;
  const popup = `${alert.timestamp}<br/>${alert.latitude}, ${alert.longitude}`;
  L.marker([lat, lng]).bindPopup(popup).addTo(alertLayer);
  map.setView([lat, lng], 15, { animate: true });
};

const updateCoords = (lat, lng) => {
  if (coordsDisplay) {
    coordsDisplay.textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  }
};

const updateLastAlert = (timestamp, lat, lng) => {
  if (lastAlertDisplay) {
    lastAlertDisplay.textContent = `${timestamp} | ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  }
};

const playSiren = () => {
  // Web Audio API siren keeps the project asset-free.
  if (!window.AudioContext) return;
  const audioContext = new AudioContext();
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();

  oscillator.type = "sawtooth";
  oscillator.frequency.setValueAtTime(440, audioContext.currentTime);
  oscillator.frequency.exponentialRampToValueAtTime(880, audioContext.currentTime + 1.2);
  gain.gain.setValueAtTime(0.0001, audioContext.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.6, audioContext.currentTime + 0.4);
  gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + 2);

  oscillator.connect(gain);
  gain.connect(audioContext.destination);
  oscillator.start();
  oscillator.stop(audioContext.currentTime + 2);
};

const getLocation = () =>
  new Promise((resolve, reject) => {
    // High accuracy is requested for emergency use.
    if (!navigator.geolocation) {
      reject(new Error("Geolocation is not supported."));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => resolve(pos),
      (err) => reject(err),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  });

const sendAlert = async (lat, lng, contactEmail, contactPhone) => {
  const response = await fetch("/send_alert", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      latitude: lat,
      longitude: lng,
      contact_email: contactEmail,
      contact_phone: contactPhone,
    }),
  });

  let data;
  const contentType = response.headers.get("content-type");

  if (contentType && contentType.includes("application/json")) {
    data = await response.json();
  } else {
    const text = await response.text();
    throw new Error("Server error: " + text);
  }

  if (!response.ok) {
    throw new Error(data.message || "Alert failed");
  }

  return data;
};


const renderHistory = (alerts) => {
  if (!historyTableBody) return;
  if (!alerts.length) {
    historyTableBody.innerHTML = '<tr class="empty-row"><td colspan="4">No alerts yet.</td></tr>';
    return;
  }

  historyTableBody.innerHTML = alerts
    .map(
      (alert) => `
        <tr>
          <td>#${alert.id}</td>
          <td>${alert.latitude}</td>
          <td>${alert.longitude}</td>
          <td>${alert.timestamp}</td>
        </tr>
      `
    )
    .join("");
};

const fetchHistory = async () => {
  const response = await fetch("/get_alerts");
  const data = await response.json();
  const alerts = data.alerts || [];
  renderHistory(alerts);
  updateAlertMarkers(alerts);
};

const fetchTrackingHistory = async () => {
  const response = await fetch("/get_tracking_history");
  const data = await response.json();
  const locations = data.locations || [];
  const points = locations
    .map((loc) => [parseFloat(loc.latitude), parseFloat(loc.longitude)])
    .filter((pair) => pair.every((value) => !Number.isNaN(value)));

  if (points.length) {
    const [lat, lng] = points[0];
    updateLiveMarker(lat, lng);
  }

  updateTrackingPath(points.slice().reverse());
};

const startTracking = () => {
  if (!navigator.geolocation) {
    setStatus("Geolocation is not supported in this browser.");
    return;
  }

  if (watchId !== null) return;

  watchId = navigator.geolocation.watchPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords;
      currentPosition = { latitude, longitude };
      updateCoords(latitude, longitude);
      updateMap(latitude, longitude);
      setStatus("Tracking live location...");
    },
    () => {
      setStatus("Unable to track location.");
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
  );
};

const stopTracking = () => {
  if (watchId === null) return;
  navigator.geolocation.clearWatch(watchId);
  watchId = null;
  setStatus("Tracking stopped.");
};

const setTrackingStatus = (active) => {
  trackingActive = active;
  if (!trackingStatus) return;
  trackingStatus.textContent = active ? "Tracking ON" : "Tracking OFF";
  trackingStatus.classList.toggle("active", active);
};

const sendLiveLocation = async (lat, lng) => {
  const response = await fetch("/update_location", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ latitude: lat, longitude: lng }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.message || "Live tracking failed.");
  }

  return response.json();
};

const startLiveTracking = () => {
  if (!navigator.geolocation) {
    setStatus("Geolocation is not supported in this browser.");
    return;
  }

  if (liveTrackingInterval) return;
  setTrackingStatus(true);

  const tick = async () => {
    try {
      const pos = await getLocation();
      const { latitude, longitude } = pos.coords;
      currentPosition = { latitude, longitude };
      updateCoords(latitude, longitude);
      updateLiveMarker(latitude, longitude);
      const result = await sendLiveLocation(latitude, longitude);
      await fetchTrackingHistory();
    } catch (error) {
      setStatus(error.message || "Unable to update live tracking.");
    }
  };

  tick();
  liveTrackingInterval = setInterval(tick, 5000);
};

const stopLiveTracking = () => {
  if (!liveTrackingInterval) return;
  clearInterval(liveTrackingInterval);
  liveTrackingInterval = null;
  setTrackingStatus(false);
};

const handleAlert = async () => {
  setStatus("Getting location...");
  setDeliveryWarning("");
  alertButton.classList.add("alerting");
  setIndicator("emergency");
  playSiren();

  try {
    const pos = await getLocation();
    const { latitude, longitude } = pos.coords;
    currentPosition = { latitude, longitude };
    updateCoords(latitude, longitude);
    updateMap(latitude, longitude);
    setStatus("Sending alert...");

    const result = await sendAlert(latitude, longitude, "", "");
    if (result.demo_mode) {
      setStatus("Demo mode: Alert simulated successfully.");
    } else {
      setStatus(result.message || "Alert sent successfully.");
    }
    if (Array.isArray(result.delivery_results)) {
      setStatus(`Alert sent to ${result.delivery_results.length} emergency contacts`);
    }
    updateLastAlert(result.alert.timestamp, latitude, longitude);
    addAlertMarker(result.alert);
    startLiveTracking();
    await fetchHistory();
  } catch (error) {
    setStatus(error.message || "Unable to send alert.");
    setDeliveryWarning("Delivery failed. Please verify email/SMS settings.");
  } finally {
    alertButton.classList.remove("alerting");
    setTimeout(() => setIndicator("safe"), 4000);
  }
};

if (alertButton) {
  alertButton.addEventListener("click", handleAlert);
}

if (refreshHistory) {
  refreshHistory.addEventListener("click", fetchHistory);
}

if (trackingToggle) {
  trackingToggle.addEventListener("change", (event) => {
    if (event.target.checked) {
      startTracking();
    } else {
      stopTracking();
    }
  });
}

if (startTrackingBtn) {
  startTrackingBtn.addEventListener("click", startLiveTracking);
}

if (stopTrackingBtn) {
  stopTrackingBtn.addEventListener("click", stopLiveTracking);
}

if (addContactBtn) {
  addContactBtn.addEventListener("click", addContact);
}

if (themeToggle) {
  themeToggle.addEventListener("click", toggleTheme);
}

initTheme();
initMap();
fetchHistory();
fetchTrackingHistory();
loadContacts();
setTrackingStatus(false);
