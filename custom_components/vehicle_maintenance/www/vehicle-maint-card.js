const CARD_VERSION = "0.4.0";
const DOMAIN = "vehicle_maintenance";

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;").replaceAll("'", "&#039;");

class VehicleMaintCard extends HTMLElement {
  static async getConfigElement() {
    return document.createElement("vehicle-maint-card-editor");
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this.config = { extend_miles: 1000, upcoming_miles: 6000, ...config };
    this.selectedService ||= "";
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  getCardSize() {
    return Math.max(4, this.serviceEntities().length + 3);
  }

  mainState() {
    return this._hass?.states[this.config?.main_entity];
  }

  serviceEntities() {
    const main = this.mainState();
    if (!main || !this._hass) return [];
    const entryId = main.attributes.entry_id;
    return Object.values(this._hass.states)
      .filter((entity) => entity.attributes.entry_id === entryId && entity.attributes.service_key)
      .filter((entity) => Number.isFinite(Number(entity.state)))
      .sort((left, right) => Number(left.state) - Number(right.state));
  }

  status(miles) {
    if (miles < 0) return "overdue";
    if (miles <= 500) return "due";
    if (miles <= 1500) return "soon";
    if (miles <= this.config.upcoming_miles) return "upcoming";
    return "okay";
  }

  mileageText(miles) {
    const value = Math.abs(miles).toLocaleString();
    if (miles < 0) return `${value} mi overdue`;
    if (miles === 0) return "Due now";
    return `${value} mi remaining`;
  }

  openMoreInfo(entityId) {
    const event = new Event("hass-more-info", { bubbles: true, composed: true });
    event.detail = { entityId };
    this.dispatchEvent(event);
  }

  async callAction(action) {
    const main = this.mainState();
    if (!main || !this.selectedService) return;
    const selected = this.serviceEntities().find(
      (entity) => entity.attributes.service_key === this.selectedService
    );
    const serviceName = selected?.attributes.service_name || "the selected service";
    const prompt = action === "log"
      ? `Log ${serviceName} at the current odometer mileage?`
      : `Extend ${serviceName} by ${Number(this.extendMiles).toLocaleString()} miles?`;
    if (!window.confirm(prompt)) return;
    const service = action === "log" ? "log_maintenance" : "extend_maintenance";
    const data = {
      entry_id: main.attributes.entry_id,
      service: this.selectedService,
    };
    if (action === "extend") data.miles = Number(this.extendMiles);
    await this._hass.callService(DOMAIN, service, data);
  }

  render() {
    if (!this.config || !this._hass) return;
    const main = this.mainState();
    if (!this.config.main_entity) {
      this.innerHTML = `<ha-card><div class="message">Open the visual editor and select a vehicle.</div></ha-card>`;
      return;
    }
    if (!main) {
      this.innerHTML = `<ha-card><div class="message">Vehicle entity unavailable: ${escapeHtml(this.config.main_entity)}</div></ha-card>`;
      return;
    }

    const entities = this.serviceEntities();
    if (!this.selectedService || !entities.some((entity) => entity.attributes.service_key === this.selectedService)) {
      this.selectedService = entities[0]?.attributes.service_key || "";
    }
    this.extendMiles = this.extendMiles || this.config.extend_miles;
    const visible = entities.filter((entity) => Number(entity.state) <= this.config.upcoming_miles);
    const counts = entities.reduce((result, entity) => {
      result[this.status(Number(entity.state))] += 1;
      return result;
    }, { overdue: 0, due: 0, soon: 0, upcoming: 0, okay: 0 });
    const odometerEntity = main.attributes.odometer_entity;
    const odometerState = this._hass.states[odometerEntity];
    const odometer = odometerState && Number.isFinite(Number(odometerState.state))
      ? `${Number(odometerState.state).toLocaleString()} mi`
      : "Odometer unavailable";
    const options = entities.map((entity) => `
      <option value="${escapeHtml(entity.attributes.service_key)}" ${entity.attributes.service_key === this.selectedService ? "selected" : ""}>
        ${escapeHtml(entity.attributes.service_name || entity.attributes.friendly_name)}
      </option>`).join("");
    const rows = visible.length ? visible.map((entity) => {
      const miles = Number(entity.state);
      const state = this.status(miles);
      return `<button class="row" data-entity="${escapeHtml(entity.entity_id)}">
        <span class="icon ${state}"><ha-icon icon="${escapeHtml(entity.attributes.icon || "mdi:wrench-outline")}"></ha-icon></span>
        <span class="copy"><b>${escapeHtml(entity.attributes.service_name || entity.attributes.friendly_name)}</b>
          <small>Due at ${Number(entity.attributes.next_due_mileage).toLocaleString()} mi</small></span>
        <span class="miles ${state}">${escapeHtml(this.mileageText(miles))}</span>
      </button>`;
    }).join("") : `<div class="message">No maintenance is due within ${this.config.upcoming_miles.toLocaleString()} mi.</div>`;

    this.innerHTML = `<style>
      vehicle-maint-card { display:block } ha-card { overflow:hidden; border-radius:24px }
      .hero { display:flex; align-items:center; gap:14px; padding:21px; background:linear-gradient(135deg,color-mix(in srgb,var(--primary-color) 16%,var(--ha-card-background)),var(--ha-card-background) 70%) }
      .car { display:grid;place-items:center;width:52px;height:52px;border-radius:18px;color:var(--primary-color);background:color-mix(in srgb,var(--primary-color) 18%,transparent) }.car ha-icon{--mdc-icon-size:30px}
      .title { flex:1 }.title b,.title small{display:block}.title b{font-size:1.25rem}.title small{margin-top:3px;color:var(--secondary-text-color)}
      .chips{display:flex;gap:8px;padding:13px 18px;border-bottom:1px solid var(--divider-color);overflow:auto}.chip{white-space:nowrap;padding:6px 10px;border-radius:14px;background:var(--secondary-background-color);font-size:.82rem;font-weight:600}.overdue{color:var(--error-color)}.due{color:var(--warning-color,#ff9800)}.soon{color:#d89b00}.upcoming{color:var(--primary-color)}.okay{color:var(--success-color,#4caf50)}
      h3{margin:0;padding:16px 20px 8px}.row{display:flex;align-items:center;gap:13px;width:100%;min-height:66px;padding:10px 18px;border:0;border-top:1px solid var(--divider-color);color:var(--primary-text-color);background:transparent;text-align:left;cursor:pointer}.row:hover{background:color-mix(in srgb,var(--primary-color) 7%,transparent)}
      .icon{display:grid;place-items:center;flex:0 0 38px;height:38px;border-radius:13px;background:var(--secondary-background-color)}.copy{display:flex;flex:1;min-width:0;flex-direction:column}.copy b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.copy small{margin-top:2px;color:var(--secondary-text-color)}.miles{font-size:.86rem;font-weight:600;text-align:right}
      .actions{margin:14px;padding:14px;border-radius:18px;background:var(--secondary-background-color)}.actions label{display:block;margin-bottom:6px;color:var(--secondary-text-color);font-size:.8rem}.controls{display:grid;grid-template-columns:minmax(0,1fr) 100px;gap:8px}.controls select{width:100%;min-height:42px;padding:0 10px;border:1px solid var(--divider-color);border-radius:12px;color:var(--primary-text-color);background:var(--card-background-color)}.buttons{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.buttons button{min-height:42px;border:0;border-radius:13px;font-weight:600;cursor:pointer}.log{color:var(--text-primary-color);background:var(--primary-color)}.extend{color:var(--primary-color);background:color-mix(in srgb,var(--primary-color) 15%,transparent)}.message{padding:24px;text-align:center;color:var(--secondary-text-color)}
      @media(max-width:420px){.miles{max-width:95px}.hero{padding:18px}.controls{grid-template-columns:1fr 90px}}
    </style><ha-card>
      <div class="hero"><span class="car"><ha-icon icon="mdi:car"></ha-icon></span><span class="title"><b>${escapeHtml(main.attributes.vehicle_name || main.attributes.friendly_name)}</b><small>${escapeHtml(odometer)}</small></span></div>
      <div class="chips"><span class="chip overdue">${counts.overdue} overdue</span><span class="chip due">${counts.due} due</span><span class="chip soon">${counts.soon + counts.upcoming} upcoming</span></div>
      <h3>Maintenance</h3><div>${rows}</div>
      <div class="actions"><label>Selected service</label><div class="controls"><select class="service">${options}</select><select class="amount"><option value="500">500 mi</option><option value="1000">1,000 mi</option><option value="2000">2,000 mi</option></select></div>
        <div class="buttons"><button class="log">Log maintenance</button><button class="extend">Extend maintenance</button></div></div>
    </ha-card>`;
    const amount = this.querySelector(".amount"); amount.value = String(this.extendMiles);
    this.querySelector(".service")?.addEventListener("change", (event) => { this.selectedService = event.target.value; });
    amount?.addEventListener("change", (event) => { this.extendMiles = Number(event.target.value); });
    this.querySelector(".log")?.addEventListener("click", () => this.callAction("log"));
    this.querySelector(".extend")?.addEventListener("click", () => this.callAction("extend"));
    this.querySelectorAll(".row").forEach((row) => row.addEventListener("click", () => this.openMoreInfo(row.dataset.entity)));
  }
}

class VehicleMaintCardEditor extends HTMLElement {
  setConfig(config) { this.config = { ...config }; this.render(); }
  set hass(hass) { this._hass = hass; this.render(); }

  changed(key, value) {
    this.config = { ...this.config, [key]: value };
    const event = new Event("config-changed", { bubbles: true, composed: true });
    event.detail = { config: this.config };
    this.dispatchEvent(event);
  }

  render() {
    if (!this._hass || !this.config) return;
    const vehicles = Object.values(this._hass.states).filter((entity) =>
      entity.attributes.integration === DOMAIN && entity.attributes.entry_id && !entity.attributes.service_key
    );
    this.innerHTML = `<style>.editor{display:grid;gap:16px;padding:8px 0}.field label{display:block;margin-bottom:6px;color:var(--secondary-text-color)}select,input{box-sizing:border-box;width:100%;min-height:44px;padding:0 10px;border:1px solid var(--divider-color);border-radius:8px;color:var(--primary-text-color);background:var(--card-background-color)}</style>
      <div class="editor"><div class="field"><label>Vehicle</label><select class="vehicle"><option value="">Select a vehicle</option>${vehicles.map((entity) => `<option value="${escapeHtml(entity.entity_id)}" ${entity.entity_id === this.config.main_entity ? "selected" : ""}>${escapeHtml(entity.attributes.vehicle_name || entity.attributes.friendly_name)}</option>`).join("")}</select></div>
      <div class="field"><label>Show maintenance within this many miles</label><input class="upcoming" type="number" min="1" value="${Number(this.config.upcoming_miles || 6000)}"></div>
      <div class="field"><label>Default extension miles</label><select class="extension"><option value="500">500</option><option value="1000">1,000</option><option value="2000">2,000</option></select></div></div>`;
    this.querySelector(".extension").value = String(this.config.extend_miles || 1000);
    this.querySelector(".vehicle").addEventListener("change", (event) => this.changed("main_entity", event.target.value));
    this.querySelector(".upcoming").addEventListener("change", (event) => this.changed("upcoming_miles", Number(event.target.value)));
    this.querySelector(".extension").addEventListener("change", (event) => this.changed("extend_miles", Number(event.target.value)));
  }
}

if (!customElements.get("vehicle-maint-card")) customElements.define("vehicle-maint-card", VehicleMaintCard);
if (!customElements.get("vehicle-maint-card-editor")) customElements.define("vehicle-maint-card-editor", VehicleMaintCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({ type: "vehicle-maint-card", name: "Vehicle Maintenance Card", description: "Configure and manage standardized vehicle maintenance.", preview: true });
console.info(`%c VEHICLE-MAINT-CARD %c v${CARD_VERSION} `, "color:white;background:#455a64;font-weight:700", "color:#455a64;background:white");
