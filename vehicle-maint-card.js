const CARD_VERSION = "0.3.0";

class VehicleMaintCard extends HTMLElement {
  setConfig(config) {
    if (!config || (!config.entity_prefix && !Array.isArray(config.entities))) {
      throw new Error("Set entity_prefix or provide an entities list");
    }

    this._config = {
      vehicle_name: "Vehicle Maintenance",
      due_miles: 500,
      soon_miles: 1500,
      upcoming_miles: 6000,
      show_all: false,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    const count = this._maintenanceEntities().length;
    return Math.max(3, Math.ceil(count * 0.8) + 2);
  }

  _maintenanceEntities() {
    if (!this._hass || !this._config) return [];

    const configured = Array.isArray(this._config.entities)
      ? this._config.entities
      : Object.keys(this._hass.states).filter((entityId) =>
          entityId.startsWith(`sensor.${this._config.entity_prefix}_`) &&
          entityId.endsWith("_miles_remaining")
        );

    return configured
      .map((entityId) => this._hass.states[entityId])
      .filter((stateObj) => stateObj && Number.isFinite(Number(stateObj.state)))
      .sort((left, right) => Number(left.state) - Number(right.state));
  }

  _status(miles) {
    if (miles < 0) return "overdue";
    if (miles <= this._config.due_miles) return "due";
    if (miles <= this._config.soon_miles) return "soon";
    if (miles <= this._config.upcoming_miles) return "upcoming";
    return "okay";
  }

  _label(stateObj) {
    const name = stateObj.attributes.service_name || stateObj.attributes.friendly_name;
    if (name) return name;

    const prefix = this._config.entity_prefix
      ? `sensor.${this._config.entity_prefix}_`
      : "sensor.";
    return stateObj.entity_id
      .replace(prefix, "")
      .replace(/_miles_remaining$/, "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (character) => character.toUpperCase());
  }

  _mileageText(miles) {
    const formatted = Math.abs(miles).toLocaleString();
    if (miles < 0) return `${formatted} mi overdue`;
    if (miles === 0) return "Due now";
    return `${formatted} mi remaining`;
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _openMoreInfo(entityId) {
    const event = new Event("hass-more-info", { bubbles: true, composed: true });
    event.detail = { entityId };
    this.dispatchEvent(event);
  }

  _callScript(entityId) {
    if (!this._hass || !entityId?.startsWith("script.")) return;
    this._hass.callService("script", "turn_on", { entity_id: entityId });
  }

  _render() {
    if (!this._config || !this._hass) return;

    const allEntities = this._maintenanceEntities();
    const visibleEntities = this._config.show_all
      ? allEntities
      : allEntities.filter(
          (stateObj) => Number(stateObj.state) <= this._config.upcoming_miles
        );
    const counts = allEntities.reduce(
      (result, stateObj) => {
        result[this._status(Number(stateObj.state))] += 1;
        return result;
      },
      { overdue: 0, due: 0, soon: 0, upcoming: 0, okay: 0 }
    );

    const odometerState = this._config.odometer_entity
      ? this._hass.states[this._config.odometer_entity]
      : undefined;
    const odometer = odometerState && Number.isFinite(Number(odometerState.state))
      ? `${Number(odometerState.state).toLocaleString()} mi`
      : "Odometer unavailable";

    const rows = visibleEntities.length
      ? visibleEntities.map((stateObj) => {
          const miles = Number(stateObj.state);
          const status = this._status(miles);
          const dueMileage = stateObj.attributes.next_due_mileage;
          const secondary = dueMileage !== undefined && dueMileage !== null
            ? `Due at ${Number(dueMileage).toLocaleString()} mi`
            : this._mileageText(miles);
          return `
            <button class="service-row" data-entity="${this._escape(stateObj.entity_id)}">
              <span class="service-icon ${status}">
                <ha-icon icon="${this._escape(stateObj.attributes.icon || "mdi:wrench-outline")}"></ha-icon>
              </span>
              <span class="service-copy">
                <span class="service-name">${this._escape(this._label(stateObj))}</span>
                <span class="service-secondary">${this._escape(secondary)}</span>
              </span>
              <span class="mileage ${status}">${this._escape(this._mileageText(miles))}</span>
            </button>`;
        }).join("")
      : `<div class="empty">No maintenance is due within ${this._config.upcoming_miles.toLocaleString()} mi.</div>`;

    const syncButton = this._config.sync_script
      ? `<button class="sync" type="button"><ha-icon icon="mdi:refresh"></ha-icon> Sync</button>`
      : "";

    this.innerHTML = `
      <style>
        vehicle-maint-card { display: block; }
        vehicle-maint-card ha-card { overflow: hidden; border-radius: 24px; }
        .hero { display: flex; align-items: center; gap: 14px; padding: 22px; background: linear-gradient(135deg, color-mix(in srgb, var(--primary-color) 16%, var(--ha-card-background)), var(--ha-card-background) 70%); }
        .hero-icon { display: grid; place-items: center; width: 52px; height: 52px; border-radius: 18px; color: var(--primary-color); background: color-mix(in srgb, var(--primary-color) 18%, transparent); }
        .hero-icon ha-icon { --mdc-icon-size: 30px; }
        .hero-copy { flex: 1; min-width: 0; }
        .title { display: block; font-size: 1.25rem; font-weight: 600; }
        .odometer { display: block; margin-top: 3px; color: var(--secondary-text-color); }
        button { font: inherit; }
        .sync { display: flex; align-items: center; gap: 5px; border: 0; border-radius: 18px; padding: 9px 12px; color: var(--primary-color); background: color-mix(in srgb, var(--primary-color) 14%, transparent); cursor: pointer; }
        .chips { display: flex; gap: 8px; padding: 14px 18px; overflow-x: auto; border-bottom: 1px solid var(--divider-color); }
        .chip { flex: 0 0 auto; border-radius: 14px; padding: 6px 10px; font-size: .82rem; font-weight: 600; background: var(--secondary-background-color); }
        .chip.overdue { color: var(--error-color); }
        .chip.due { color: var(--warning-color, #ff9800); }
        .chip.soon { color: #d89b00; }
        .section-title { padding: 16px 20px 7px; font-size: 1.05rem; font-weight: 600; }
        .service-row { display: flex; width: 100%; min-height: 66px; align-items: center; gap: 13px; border: 0; border-top: 1px solid var(--divider-color); padding: 10px 18px; color: var(--primary-text-color); background: transparent; text-align: left; cursor: pointer; }
        .service-row:hover { background: color-mix(in srgb, var(--primary-color) 7%, transparent); }
        .service-icon { display: grid; flex: 0 0 38px; width: 38px; height: 38px; place-items: center; border-radius: 13px; background: var(--secondary-background-color); }
        .service-icon.overdue, .mileage.overdue { color: var(--error-color); }
        .service-icon.due, .mileage.due { color: var(--warning-color, #ff9800); }
        .service-icon.soon, .mileage.soon { color: #d89b00; }
        .service-icon.upcoming, .mileage.upcoming { color: var(--primary-color); }
        .service-icon.okay, .mileage.okay { color: var(--success-color, #4caf50); }
        .service-copy { display: flex; flex: 1; min-width: 0; flex-direction: column; }
        .service-name { overflow: hidden; font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
        .service-secondary { margin-top: 2px; color: var(--secondary-text-color); font-size: .8rem; }
        .mileage { flex: 0 0 auto; font-size: .86rem; font-weight: 600; text-align: right; }
        .empty { padding: 24px 20px; color: var(--secondary-text-color); text-align: center; }
        @media (max-width: 420px) { .mileage { max-width: 100px; } .hero { padding: 18px; } }
      </style>
      <ha-card>
        <div class="hero">
          <span class="hero-icon"><ha-icon icon="${this._escape(this._config.icon || "mdi:car")}"></ha-icon></span>
          <span class="hero-copy">
            <span class="title">${this._escape(this._config.vehicle_name)}</span>
            <span class="odometer">${this._escape(odometer)}</span>
          </span>
          ${syncButton}
        </div>
        <div class="chips">
          <span class="chip overdue">${counts.overdue} overdue</span>
          <span class="chip due">${counts.due} due</span>
          <span class="chip soon">${counts.soon + counts.upcoming} upcoming</span>
        </div>
        <div class="section-title">Maintenance</div>
        <div class="services">${rows}</div>
      </ha-card>`;

    this.querySelectorAll(".service-row").forEach((row) => {
      row.addEventListener("click", () => this._openMoreInfo(row.dataset.entity));
    });
    this.querySelector(".sync")?.addEventListener("click", () =>
      this._callScript(this._config.sync_script)
    );
  }
}

if (!customElements.get("vehicle-maint-card")) {
  customElements.define("vehicle-maint-card", VehicleMaintCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "vehicle-maint-card",
  name: "Vehicle Maintenance Card",
  description: "A vehicle-neutral mileage maintenance dashboard card.",
  preview: true,
});

console.info(`%c VEHICLE-MAINT-CARD %c v${CARD_VERSION} `, "color: white; background: #455a64; font-weight: 700;", "color: #455a64; background: white;");
