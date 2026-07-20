const CARD_VERSION = "0.1.0";
const DOMAIN = "vehicle_maintenance";

const esc = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const number = (value) => value === null || value === undefined ? "Not set" : Number(value).toLocaleString();

class VehicleMaintCard extends HTMLElement {
  static async getConfigElement() { return document.createElement("vehicle-maint-card-editor"); }
  static getStubConfig() { return { upcoming_miles: 2000 }; }

  constructor() {
    super();
    this.view = "due";
    this.interacting = false;
    this.addEventListener("pointerdown", (event) => {
      if (event.target.closest("select,input,button,summary")) this.interacting = true;
    });
    this.addEventListener("focusout", () => setTimeout(() => {
      if (!this.matches(":focus-within")) this.interacting = false;
      if (this.pendingRender && !this.interacting) { this.pendingRender = false; this.render(); }
    }, 250));
  }

  setConfig(config) {
    this.config = { upcoming_miles: 2000, snooze_miles: 1000, ...config };
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this.interacting) this.pendingRender = true;
    else this.render();
  }

  getCardSize() { return Math.max(4, this.services().length + 2); }
  main() { return this._hass?.states[this.config?.main_entity]; }
  odometer() { return Number(this.main()?.attributes.effective_odometer); }
  entryId() { return this.main()?.attributes.entry_id; }

  services() {
    const entryId = this.entryId();
    if (!entryId || !this._hass) return [];
    return Object.values(this._hass.states)
      .filter((entity) => entity.attributes.entry_id === entryId && entity.attributes.service_key)
      .sort((a, b) => {
        const aDue = a.attributes.scheduled_due_mileage;
        const bDue = b.attributes.scheduled_due_mileage;
        return (aDue ?? Number.MAX_SAFE_INTEGER) - (bDue ?? Number.MAX_SAFE_INTEGER);
      });
  }

  showToast(message) {
    this.dispatchEvent(new CustomEvent("hass-notification", { bubbles: true, composed: true, detail: { message } }));
  }

  moreInfo(entityId) {
    this.dispatchEvent(new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId } }));
  }

  async call(service, data, success) {
    try {
      await this._hass.callService(DOMAIN, service, { entry_id: this.entryId(), ...data });
      this.error = "";
      this.selectedService = null;
      this.interacting = false;
      this.showToast(success);
      this.render();
    } catch (error) {
      this.error = error?.message || String(error);
      this.render();
    }
  }

  selectService(key) {
    this.selectedService = key;
    const entity = this.services().find((item) => item.attributes.service_key === key);
    this.completionMileage = this.odometer();
    const attributes = entity?.attributes || {};
    this.setupMode = !attributes.initialized ? "not_set" : attributes.due_mileage_override != null ? "due_at" : "last_completed";
    this.setupMileage = attributes.due_mileage_override ?? attributes.last_completed_mileage ?? this.odometer();
    this.snoozeChoice = String(this.config.snooze_miles);
    this.customSnooze = this.config.snooze_miles;
    this.error = "";
    this.render();
  }

  serviceRows(services) {
    if (!services.length) return `<div class="empty">Nothing to show in this view.</div>`;
    return services.map((entity) => {
      const a = entity.attributes;
      const remaining = a.miles_remaining;
      const status = a.status || "setup_required";
      const deferred = a.deferred;
      let human = status === "setup_required" ? "Setup required"
        : status === "completed" ? `Completed at ${number(a.milestone_completed_mileage)} mi`
        : remaining < 0 ? `${number(Math.abs(remaining))} mi overdue`
        : `${number(remaining)} mi remaining`;
      if (deferred) human = `Deferred until ${number(a.snoozed_until_mileage)} mi`;
      return `<div class="row ${esc(status)} ${deferred ? "deferred" : ""}">
        <button class="row-main" data-service="${esc(a.service_key)}">
          <span class="service-icon"><ha-icon icon="${esc(a.icon || entity.attributes.icon || "mdi:wrench-outline")}"></ha-icon></span>
          <span class="row-copy"><b>${esc(a.service_name)}</b><small>${esc(human)}</small></span>
          <span class="row-value">${status === "setup_required" ? "SETUP" : deferred ? "LATER" : remaining === null ? "—" : number(remaining)}</span>
        </button>
        <button class="info" data-info="${esc(entity.entity_id)}" aria-label="Entity information"><ha-icon icon="mdi:information-outline"></ha-icon></button>
      </div>`;
    }).join("");
  }

  actionPanel() {
    if (!this.selectedService) return "";
    const entity = this.services().find((item) => item.attributes.service_key === this.selectedService);
    if (!entity) return "";
    const a = entity.attributes;
    const odo = this.odometer();
    const interval = Number(a.interval_miles || 0);
    const nextAfterCompletion = a.milestone ? null : Number(this.completionMileage) + interval;
    const snoozeAmount = this.snoozeChoice === "custom" ? Number(this.customSnooze) : Number(this.snoozeChoice);
    const snoozeTarget = odo + snoozeAmount;
    return `<div class="backdrop"><section class="panel" role="dialog" aria-modal="true">
      <header><div><small>Maintenance action</small><h2>${esc(a.service_name)}</h2></div><button class="close" aria-label="Close">×</button></header>
      <div class="facts"><span>Odometer <b>${number(odo)} mi</b></span><span>Last completed <b>${number(a.last_completed_mileage)}${a.last_completed_mileage == null ? "" : " mi"}</b></span><span>Scheduled due <b>${number(a.scheduled_due_mileage)}${a.scheduled_due_mileage == null ? "" : " mi"}</b></span></div>
      ${this.error ? `<div class="error">${esc(this.error)}</div>` : ""}
      <button class="primary complete-now">Completed now at ${number(odo)} mi</button>
      <label>Mileage when completed</label><div class="input-action"><input class="completion" type="number" min="0" value="${Number(this.completionMileage)}"><button class="complete-other">Complete</button></div>
      <small class="result">Log ${esc(a.service_name)} at ${number(this.completionMileage)} mi · ${a.milestone ? "Milestone will be marked completed" : `Next scheduled service: ${number(nextAfterCompletion)} mi`}</small>
      ${a.initialized ? `<hr><label>Remind me later · Check again in</label><div class="input-action"><select class="snooze"><option value="500">500 mi</option><option value="1000">1,000 mi</option><option value="2000">2,000 mi</option><option value="custom">Custom</option></select><input class="custom-snooze" type="number" min="1" value="${Number(this.customSnooze)}" ${this.snoozeChoice === "custom" ? "" : "hidden"}></div><button class="secondary snooze-action">Remind me again at ${number(snoozeTarget)} mi</button><small>This will not mark the service completed or change its scheduled due mileage.</small>${a.snoozed_until_mileage != null ? `<button class="text clear-snooze">Clear reminder</button>` : ""}` : `<small>Initialize or complete this service before setting a reminder.</small>`}
      <details><summary>Advanced record editing</summary><label>Record state</label><select class="setup-mode"><option value="not_set">Not set</option><option value="never_performed">Never performed</option><option value="last_completed">Last completed at mileage</option><option value="due_at">Due at known mileage</option></select><label>Mileage</label><input class="setup-mileage" type="number" min="0" value="${Number(this.setupMileage || 0)}"><button class="secondary apply-setup">Save record</button></details>
    </section></div>`;
  }

  render() {
    if (!this.config || !this._hass) return;
    const main = this.main();
    if (!this.config.main_entity || !main) {
      this.innerHTML = `<ha-card><div class="empty">Open the visual editor and select a Vehicle Maintenance entry.</div></ha-card>`;
      return;
    }
    const all = this.services();
    const setup = all.filter((entity) => entity.attributes.status === "setup_required");
    const deferred = all.filter((entity) => entity.attributes.deferred);
    const due = all.filter((entity) => !entity.attributes.deferred && entity.attributes.status !== "setup_required" && entity.attributes.status !== "completed" && Number(entity.attributes.miles_remaining) <= this.config.upcoming_miles);
    const shown = this.view === "all" ? all : [...setup, ...due];
    this.innerHTML = `<style>
      vehicle-maint-card{display:block}ha-card{overflow:hidden;border-radius:24px}.hero{display:flex;gap:14px;align-items:center;padding:21px;background:linear-gradient(135deg,color-mix(in srgb,var(--primary-color) 16%,var(--ha-card-background)),var(--ha-card-background) 70%)}.car{display:grid;place-items:center;width:52px;height:52px;border-radius:18px;color:var(--primary-color);background:color-mix(in srgb,var(--primary-color) 18%,transparent)}.title{flex:1}.title b,.title small{display:block}.title b{font-size:1.25rem}.title small{color:var(--secondary-text-color);margin-top:3px}.chips,.views{display:flex;gap:8px;padding:12px 18px;border-bottom:1px solid var(--divider-color)}.chip{padding:6px 10px;border-radius:14px;background:var(--secondary-background-color);font-size:.82rem;font-weight:600}.views button{flex:1;border:0;border-radius:12px;padding:9px;background:transparent;color:var(--secondary-text-color);font-weight:600}.views button.active{background:color-mix(in srgb,var(--primary-color) 16%,transparent);color:var(--primary-color)}h3{margin:0;padding:15px 18px 8px}.row{display:flex;border-top:1px solid var(--divider-color)}.row-main{display:flex;align-items:center;gap:12px;min-height:66px;flex:1;min-width:0;padding:9px 10px 9px 18px;border:0;background:transparent;color:var(--primary-text-color);text-align:left}.service-icon{display:grid;place-items:center;width:38px;height:38px;border-radius:13px;background:var(--secondary-background-color);color:var(--primary-color)}.row-copy{display:flex;flex:1;min-width:0;flex-direction:column}.row-copy small{color:var(--secondary-text-color);margin-top:2px}.row-value{font-size:.8rem;font-weight:700}.overdue .row-value{color:var(--error-color)}.due_soon .row-value{color:var(--warning-color,#ff9800)}.setup_required .row-value{color:#d89b00}.deferred .row-value{color:var(--primary-color)}.info{width:45px;border:0;background:transparent;color:var(--secondary-text-color)}.empty{padding:25px;text-align:center;color:var(--secondary-text-color)}.backdrop{position:fixed;inset:0;z-index:1000;display:flex;align-items:flex-end;justify-content:center;background:#0008}.panel{box-sizing:border-box;width:min(100%,600px);max-height:92vh;overflow:auto;padding:20px;border-radius:24px 24px 0 0;background:var(--card-background-color);color:var(--primary-text-color)}.panel header{display:flex;justify-content:space-between}.panel h2{margin:2px 0 14px}.close{border:0;background:transparent;color:var(--primary-text-color);font-size:2rem}.facts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px}.facts span{padding:9px;border-radius:12px;background:var(--secondary-background-color);font-size:.82rem}.facts b{display:block;margin-top:3px}.panel label{display:block;margin:12px 0 5px;color:var(--secondary-text-color);font-size:.82rem}.panel input,.panel select{box-sizing:border-box;width:100%;min-height:44px;padding:0 10px;border:1px solid var(--divider-color);border-radius:12px;background:var(--secondary-background-color);color:var(--primary-text-color)}.input-action{display:flex;gap:8px}.input-action button{min-width:105px}.primary,.secondary,.text{width:100%;min-height:44px;margin-top:10px;border:0;border-radius:13px;font-weight:700}.primary{background:var(--primary-color);color:var(--text-primary-color)}.secondary{background:color-mix(in srgb,var(--primary-color) 16%,transparent);color:var(--primary-color)}.text{background:transparent;color:var(--primary-color)}.result,.panel>small{display:block;margin-top:7px;color:var(--secondary-text-color)}.panel hr{border:0;border-top:1px solid var(--divider-color);margin:18px 0}.panel details{margin-top:15px;padding-top:12px;border-top:1px solid var(--divider-color)}.panel summary{font-weight:700}.error{padding:10px;border-radius:10px;background:color-mix(in srgb,var(--error-color) 18%,transparent);color:var(--error-color)}
    </style><ha-card><div class="hero"><span class="car"><ha-icon icon="mdi:car"></ha-icon></span><span class="title"><b>${esc(main.attributes.vehicle_name || main.attributes.friendly_name)}</b><small>${number(main.attributes.effective_odometer)} mi · ${esc(main.attributes.odometer_source || "unavailable")}</small></span></div><div class="chips"><span class="chip">${setup.length} setup</span><span class="chip">${main.attributes.overdue_count || 0} overdue</span><span class="chip">${main.attributes.due_soon_count || 0} due soon</span><span class="chip">${deferred.length} deferred</span></div><div class="views"><button data-view="due" class="${this.view === "due" ? "active" : ""}">Due soon</button><button data-view="all" class="${this.view === "all" ? "active" : ""}">All maintenance</button></div><h3>${this.view === "due" ? "Needs attention" : "All maintenance"}</h3>${this.serviceRows(shown)}</ha-card>${this.actionPanel()}`;
    this.querySelectorAll("[data-view]").forEach((button) => button.onclick = () => { this.view = button.dataset.view; this.render(); });
    this.querySelectorAll("[data-service]").forEach((button) => button.onclick = () => this.selectService(button.dataset.service));
    this.querySelectorAll("[data-info]").forEach((button) => button.onclick = () => this.moreInfo(button.dataset.info));
    this.bindPanel();
  }

  bindPanel() {
    if (!this.selectedService) return;
    const entity = this.services().find((item) => item.attributes.service_key === this.selectedService);
    const a = entity.attributes;
    const odo = this.odometer();
    this.querySelector(".close").onclick = () => { this.selectedService = null; this.render(); };
    this.querySelector(".completion").oninput = (event) => { this.completionMileage = Number(event.target.value); };
    this.querySelector(".complete-now").onclick = () => {
      const result = a.milestone ? "Milestone will be marked completed" : `Next scheduled service: ${number(odo + Number(a.interval_miles || 0))} mi`;
      if (confirm(`Log ${a.service_name} at ${number(odo)} mi\n${result}`)) this.call("log_maintenance", { service: this.selectedService }, `${a.service_name} completed at ${number(odo)} mi`);
    };
    this.querySelector(".complete-other").onclick = () => {
      const mileage = Number(this.completionMileage); const future = mileage > odo ? "\nWarning: this is greater than the effective odometer." : ""; const result = a.milestone ? "Milestone will be marked completed" : `Next scheduled service: ${number(mileage + Number(a.interval_miles || 0))} mi`;
      if (confirm(`Log ${a.service_name} at ${number(mileage)} mi${future}\n${result}`)) this.call("log_maintenance", { service: this.selectedService, mileage }, `${a.service_name} completed at ${number(mileage)} mi`);
    };
    const snooze = this.querySelector(".snooze");
    if (snooze) { snooze.value = this.snoozeChoice; snooze.onchange = (event) => { this.snoozeChoice = event.target.value; this.render(); }; }
    if (this.querySelector(".custom-snooze")) this.querySelector(".custom-snooze").oninput = (event) => { this.customSnooze = Number(event.target.value); };
    if (this.querySelector(".snooze-action")) this.querySelector(".snooze-action").onclick = () => { const miles = this.snoozeChoice === "custom" ? Number(this.customSnooze) : Number(this.snoozeChoice); const target = odo + miles; if (confirm(`Remind me about ${a.service_name} again at ${number(target)} mi\nThis will not mark the service completed`)) this.call("snooze_maintenance", { service: this.selectedService, miles }, `${a.service_name} deferred until ${number(target)} mi`); };
    this.querySelector(".clear-snooze")?.addEventListener("click", () => this.call("clear_snooze", { service: this.selectedService }, `Reminder cleared for ${a.service_name}`));
    const setupMode = this.querySelector(".setup-mode"); setupMode.value = this.setupMode;
    setupMode.onchange = (event) => { this.setupMode = event.target.value; };
    this.querySelector(".setup-mileage").oninput = (event) => { this.setupMileage = Number(event.target.value); };
    this.querySelector(".apply-setup").onclick = () => this.call("set_maintenance", { service: this.selectedService, mode: this.setupMode || "not_set", mileage: Number(this.setupMileage || 0) }, `${a.service_name} record updated`);
  }
}

class VehicleMaintCardEditor extends HTMLElement {
  setConfig(config) { this.config = { upcoming_miles: 2000, ...config }; this.render(); }
  set hass(hass) { this._hass = hass; this.render(); }
  changed(key, value) { this.config = { ...this.config, [key]: value }; this.dispatchEvent(new CustomEvent("config-changed", { bubbles: true, composed: true, detail: { config: this.config } })); }
  render() {
    if (!this._hass || !this.config) return;
    const vehicles = Object.values(this._hass.states).filter((entity) => entity.attributes.integration === DOMAIN && entity.attributes.entry_id && !entity.attributes.service_key);
    this.innerHTML = `<div><label>Vehicle</label><select class="vehicle"><option value="">Select a vehicle</option>${vehicles.map((entity) => `<option value="${esc(entity.entity_id)}" ${entity.entity_id === this.config.main_entity ? "selected" : ""}>${esc(entity.attributes.vehicle_name || entity.attributes.friendly_name)}</option>`).join("")}</select><label>Due-soon window (miles)</label><input class="upcoming" type="number" min="1" value="${Number(this.config.upcoming_miles || 2000)}"></div><style>label{display:block;margin:12px 0 5px}select,input{box-sizing:border-box;width:100%;min-height:44px;padding:0 10px}</style>`;
    this.querySelector(".vehicle").onchange = (event) => this.changed("main_entity", event.target.value);
    this.querySelector(".upcoming").onchange = (event) => this.changed("upcoming_miles", Number(event.target.value));
  }
}

if (!customElements.get("vehicle-maint-card")) customElements.define("vehicle-maint-card", VehicleMaintCard);
if (!customElements.get("vehicle-maint-card-editor")) customElements.define("vehicle-maint-card-editor", VehicleMaintCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({ type: "vehicle-maint-card", name: "Vehicle Maintenance Card", description: "Vehicle-neutral maintenance tracking", preview: true });
console.info(`%c VEHICLE-MAINT-CARD %c v${CARD_VERSION} `, "color:white;background:#455a64;font-weight:700", "color:#455a64;background:white");
