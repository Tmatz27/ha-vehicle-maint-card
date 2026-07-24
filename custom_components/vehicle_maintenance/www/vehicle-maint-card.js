const CARD_VERSION = "0.1.4";
const DOMAIN = "vehicle_maintenance";
const DEFAULT_UPCOMING_MILES = 2000;
const DEFAULT_EXTEND_MILES = 1000;
const QUICK_EXTENSIONS = [500, 1000, 2000];

const esc = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const finiteNumber = (value) => {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (!normalized || ["unknown", "unavailable", "none", "nan"].includes(normalized)) return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const positiveNumber = (value) => {
  const parsed = finiteNumber(value);
  return parsed !== null && parsed > 0 ? parsed : null;
};

const positiveInteger = (value) => {
  const parsed = positiveNumber(value);
  return parsed !== null && Number.isInteger(parsed) ? parsed : null;
};

const formatNumber = (value, fallback = "Unavailable") => {
  const parsed = finiteNumber(value);
  return parsed === null ? fallback : parsed.toLocaleString();
};

const normalizeAccentColor = (value) => {
  if (typeof value !== "string") return null;
  const normalized = value.trim().toLowerCase();
  return /^#[0-9a-f]{6}$/.test(normalized) ? normalized : null;
};

const accentTextColor = (value) => {
  const color = normalizeAccentColor(value);
  if (color === null) return "var(--text-primary-color)";
  const red = Number.parseInt(color.slice(1, 3), 16);
  const green = Number.parseInt(color.slice(3, 5), 16);
  const blue = Number.parseInt(color.slice(5, 7), 16);
  const brightness = (red * 299 + green * 587 + blue * 114) / 1000;
  return brightness >= 150 ? "#111111" : "#ffffff";
};

const normalizeConfig = (config = {}) => {
  const { snooze_miles: legacyExtendMiles, ...rest } = config;
  const normalized = {
    ...rest,
    upcoming_miles: positiveInteger(config.upcoming_miles) ?? DEFAULT_UPCOMING_MILES,
    extend_miles: positiveInteger(config.extend_miles)
      ?? positiveInteger(legacyExtendMiles)
      ?? DEFAULT_EXTEND_MILES,
  };
  const accentColor = normalizeAccentColor(config.accent_color);
  if (accentColor === null) delete normalized.accent_color;
  else normalized.accent_color = accentColor;
  return normalized;
};

const completionMileageDetails = (value, odometer) => {
  const mileage = positiveInteger(value);
  const current = finiteNumber(odometer);
  if (mileage === null) {
    return { valid: false, error: "Enter a positive completion mileage.", mileage: null };
  }
  if (current !== null && mileage > current) {
    return { valid: false, error: "Completion mileage cannot be greater than the current odometer.", mileage };
  }
  return { valid: true, error: "", mileage };
};

const completionDetails = (value, odometer, interval, milestone = false) => {
  const completion = completionMileageDetails(value, odometer);
  if (!completion.valid) return { ...completion, nextDue: null };
  if (milestone) return { ...completion, nextDue: null };
  const serviceInterval = positiveNumber(interval);
  if (serviceInterval === null) {
    return { ...completion, valid: false, error: "A valid service interval is required.", nextDue: null };
  }
  return { ...completion, nextDue: completion.mileage + serviceInterval };
};

const extensionDetails = (odometer, amount) => {
  const current = finiteNumber(odometer);
  const miles = positiveNumber(amount);
  if (current === null) return { valid: false, error: "A valid odometer is required.", miles, target: null };
  if (miles === null) return { valid: false, error: "Enter a positive extension distance.", miles: null, target: null };
  return { valid: true, error: "", miles, target: current + miles };
};

const isDueSoonService = (entity, upcomingMiles) => {
  const attributes = entity?.attributes || {};
  const remaining = finiteNumber(attributes.miles_remaining);
  return Boolean(attributes.initialized)
    && !attributes.deferred
    && attributes.status !== "completed"
    && remaining !== null
    && remaining <= upcomingMiles;
};

const isNeverPerformed = (entity) => {
  const attributes = entity?.attributes || {};
  if (!attributes.initialized) return true;
  return !attributes.milestone_completed
    && finiteNumber(attributes.last_completed_mileage) === 0;
};

const servicePresentation = (entity, odometer, upcomingMiles = DEFAULT_UPCOMING_MILES) => {
  const attributes = entity?.attributes || {};
  const remaining = finiteNumber(attributes.miles_remaining);
  const neverPerformed = isNeverPerformed(entity);
  if (!attributes.initialized) {
    return { kind: "never", detail: "Never performed", badge: "NEVER" };
  }
  if (attributes.status === "completed" || (attributes.milestone && attributes.milestone_completed)) {
    const completedAt = finiteNumber(attributes.milestone_completed_mileage);
    return {
      kind: "completed",
      detail: completedAt === null ? "Completed" : `Completed at ${formatNumber(completedAt)} mi`,
      badge: "DONE",
    };
  }
  if (attributes.deferred) {
    const target = finiteNumber(attributes.snoozed_until_mileage);
    const current = finiteNumber(odometer);
    const untilReview = target !== null && current !== null ? Math.max(0, target - current) : null;
    return {
      kind: "extended",
      detail: target === null ? "Maintenance extended" : `Extended until ${formatNumber(target)} mi`,
      badge: untilReview === null ? "EXTENDED" : `${formatNumber(untilReview)} mi`,
    };
  }
  if (remaining === null) {
    return {
      kind: neverPerformed ? "never" : "unavailable",
      detail: neverPerformed ? "Never performed" : "Due mileage unavailable",
      badge: neverPerformed ? "NEVER" : "N/A",
    };
  }
  const prefix = neverPerformed ? "Never performed · " : "";
  if (remaining < 0) {
    return { kind: "overdue", detail: `${prefix}${formatNumber(Math.abs(remaining))} mi overdue`, badge: "OVERDUE" };
  }
  if (remaining === 0) return { kind: "due", detail: `${prefix}Due now`, badge: "DUE" };
  return { kind: remaining <= upcomingMiles ? "due" : "okay", detail: `${prefix}${formatNumber(remaining)} mi remaining`, badge: `${formatNumber(remaining)} mi` };
};

class VehicleMaintCard extends HTMLElement {
  static async getConfigElement() {
    return document.createElement("vehicle-maint-card-editor");
  }

  static getStubConfig() {
    return { upcoming_miles: DEFAULT_UPCOMING_MILES, extend_miles: DEFAULT_EXTEND_MILES };
  }

  constructor() {
    super();
    this.view = "due";
    this.actionMode = "log";
    this.completionMileage = "";
    this.extensionChoice = String(DEFAULT_EXTEND_MILES);
    this.customExtension = "";
    this.batchOpen = false;
    this.batchServices = new Set();
    this.batchMileage = "";
    this.serviceEntityIds = [];
    this.error = "";
  }

  setConfig(config) {
    if (!config) throw new Error("Vehicle Maintenance Card configuration is required");
    this.config = normalizeConfig(config);
    this.render();
  }

  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    if (!previous || this.relevantStatesChanged(previous, hass)) this.render();
  }

  getCardSize() {
    return Math.max(4, this.visibleServices().length + 2);
  }

  main() {
    return this._hass?.states[this.config?.main_entity];
  }

  odometer() {
    return finiteNumber(this.main()?.attributes.effective_odometer);
  }

  entryId() {
    return this.main()?.attributes.entry_id;
  }

  services() {
    const entryId = this.entryId();
    if (!entryId || !this._hass) return [];
    const services = Object.values(this._hass.states)
      .filter((entity) => entity.attributes.entry_id === entryId && entity.attributes.service_key)
      .sort((left, right) => this.serviceSortValue(left) - this.serviceSortValue(right));
    this.serviceEntityIds = services.map((entity) => entity.entity_id);
    return services;
  }

  serviceSortValue(entity) {
    const attributes = entity.attributes || {};
    if (!attributes.initialized) return 3_000_000_000;
    if (attributes.status === "completed") return 4_000_000_000;
    if (attributes.deferred) return 2_000_000_000 + (finiteNumber(attributes.snoozed_until_mileage) ?? 999_999_999);
    return finiteNumber(attributes.miles_remaining) ?? 2_999_999_999;
  }

  visibleServices() {
    const all = this.services();
    return this.view === "all"
      ? all
      : all.filter((entity) => isDueSoonService(entity, this.config?.upcoming_miles ?? DEFAULT_UPCOMING_MILES));
  }

  selectedEntity() {
    return this.services().find((entity) => entity.attributes.service_key === this.selectedService);
  }

  relevantStatesChanged(previous, next) {
    const mainEntity = this.config?.main_entity;
    if (!mainEntity || previous.states[mainEntity] !== next.states[mainEntity]) return true;
    return this.serviceEntityIds.some((entityId) => previous.states[entityId] !== next.states[entityId]);
  }

  showToast(message) {
    this.dispatchEvent(new CustomEvent("hass-notification", {
      bubbles: true,
      composed: true,
      detail: { message },
    }));
  }

  moreInfo(entityId) {
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId },
    }));
  }

  async call(service, data, success) {
    try {
      await this._hass.callService(DOMAIN, service, { entry_id: this.entryId(), ...data });
      this.error = "";
      this.selectedService = null;
      this.batchOpen = false;
      this.batchServices.clear();
      this.batchMileage = "";
      this.showToast(success);
      this.render();
    } catch (error) {
      this.error = error?.message || String(error);
      this.render();
    }
  }

  selectService(key) {
    this.batchOpen = false;
    this.selectedService = key;
    this.actionMode = "log";
    this.completionMileage = "";
    const configured = String(this.config.extend_miles);
    this.extensionChoice = QUICK_EXTENSIONS.map(String).includes(configured) ? configured : "custom";
    this.customExtension = this.extensionChoice === "custom" ? configured : "";
    this.error = "";
    this.render();
  }

  openBatch() {
    this.selectedService = null;
    this.batchOpen = true;
    this.batchServices = new Set();
    this.batchMileage = "";
    this.error = "";
    this.render();
  }

  batchEligibleServices() {
    return this.services().filter((entity) => !(
      entity.attributes.milestone && entity.attributes.milestone_completed
    ));
  }

  serviceRows(services) {
    if (!services.length) {
      const neverPerformed = this.services().filter(isNeverPerformed).length;
      const note = this.view === "due" && neverPerformed
        ? `<small>${neverPerformed} ${neverPerformed === 1 ? "service has" : "services have"} never been performed. Open All Maintenance to review them.</small>`
        : "";
      return `<div class="empty"><b>No maintenance needs attention.</b><span>Nothing is due within ${formatNumber(this.config.upcoming_miles)} mi.</span>${note}</div>`;
    }
    const odometer = this.odometer();
    return services.map((entity) => {
      const attributes = entity.attributes;
      const display = servicePresentation(entity, odometer, this.config.upcoming_miles);
      return `<div class="row ${esc(display.kind)}">
        <button class="row-main" data-service="${esc(attributes.service_key)}" aria-label="Open ${esc(attributes.service_name)} maintenance actions">
          <span class="service-icon"><ha-icon icon="${esc(attributes.icon || entity.attributes.icon || "mdi:wrench-outline")}"></ha-icon></span>
          <span class="row-copy"><b>${esc(attributes.service_name)}</b><small>${esc(display.detail)}</small></span>
          <span class="row-value">${esc(display.badge)}</span>
        </button>
        <button class="info" data-info="${esc(entity.entity_id)}" aria-label="Open ${esc(attributes.service_name)} entity information"><ha-icon icon="mdi:information-outline"></ha-icon></button>
      </div>`;
    }).join("");
  }

  fact(label, value) {
    return `<span><small>${esc(label)}</small><b>${esc(value)}</b></span>`;
  }

  logPanel(attributes, odometer) {
    const details = completionDetails(
      this.completionMileage,
      odometer,
      attributes.interval_miles,
      Boolean(attributes.milestone),
    );
    const preview = this.completionMileage === ""
      ? "Enter the mileage from when the work was completed."
      : details.valid
        ? attributes.milestone
          ? `This will mark the milestone complete at ${formatNumber(details.mileage)} mi.`
          : `Next due at ${formatNumber(details.nextDue)} mi.`
        : details.error;
    const exactButton = details.valid ? `Log at ${formatNumber(details.mileage)} mi` : "Enter completion mileage";
    return `<div class="workflow log-workflow">
      <h3>Use the current odometer</h3>
      <button class="primary log-current" ${odometer === null ? "disabled" : ""}>${odometer === null ? "Odometer unavailable" : `Log at ${formatNumber(odometer)} mi`}</button>
      <small>${odometer === null ? "Enter the completion mileage below instead." : "Use this when the maintenance was just completed."}</small>
      <div class="divider"><span>or completed earlier</span></div>
      <label for="completion-mileage">Mileage when completed</label>
      <input id="completion-mileage" class="completion" type="number" inputmode="numeric" min="1" step="1" placeholder="Enter exact mileage" value="${esc(this.completionMileage)}">
      <div class="inline-message completion-result ${this.completionMileage !== "" && !details.valid ? "invalid" : ""}">${esc(preview)}</div>
      <button class="secondary log-exact" ${details.valid ? "" : "disabled"}>${esc(exactButton)}</button>
    </div>`;
  }

  extendPanel(attributes, odometer) {
    const completedMilestone = attributes.milestone && attributes.milestone_completed;
    const eligible = Boolean(attributes.initialized) && !completedMilestone;
    if (!eligible) {
      return `<div class="workflow"><div class="notice"><b>${completedMilestone ? "This milestone is complete." : "Log this maintenance first."}</b><span>${completedMilestone ? "No extension is needed." : "A completion mileage is required before maintenance can be extended."}</span></div></div>`;
    }
    const amount = this.extensionChoice === "custom" ? this.customExtension : this.extensionChoice;
    const details = extensionDetails(odometer, amount);
    const choices = QUICK_EXTENSIONS.map((miles) => `<button class="choice ${this.extensionChoice === String(miles) ? "selected" : ""}" data-extension="${miles}">${formatNumber(miles)} mi</button>`).join("");
    const targetText = details.valid
      ? `This maintenance will return at ${formatNumber(details.target)} mi.`
      : details.error;
    const actionText = details.valid ? `Extend until ${formatNumber(details.target)} mi` : "Extension unavailable";
    return `<div class="workflow extend-workflow">
      <h3>How far should this be extended?</h3>
      <div class="extension-choices">${choices}<button class="choice ${this.extensionChoice === "custom" ? "selected" : ""}" data-extension="custom">Custom</button></div>
      <div class="custom-wrap" ${this.extensionChoice === "custom" ? "" : "hidden"}>
        <label for="custom-extension">Custom extension in miles</label>
        <input id="custom-extension" class="custom-extension" type="number" inputmode="numeric" min="1" step="1" placeholder="Enter miles" value="${esc(this.customExtension)}">
      </div>
      <div class="inline-message extension-result ${!details.valid ? "invalid" : ""}">${esc(targetText)}</div>
      <button class="primary extend-action" ${details.valid ? "" : "disabled"}>${esc(actionText)}</button>
      <small>This postpones dashboard attention and notifications. It does not log the service as completed or change its normal interval.</small>
      ${attributes.deferred ? `<button class="text clear-extension">Clear Extension</button>` : ""}
    </div>`;
  }

  actionPanel() {
    if (!this.selectedService) return "";
    const entity = this.selectedEntity();
    if (!entity) return "";
    const attributes = entity.attributes;
    const odometer = this.odometer();
    const interval = positiveNumber(attributes.interval_miles);
    const due = finiteNumber(attributes.scheduled_due_mileage);
    const target = finiteNumber(attributes.snoozed_until_mileage);
    const neverPerformed = isNeverPerformed(entity);
    const initialInterval = positiveNumber(attributes.initial_interval_miles);
    const typeLabel = {
      condition: "Condition reminder",
      inspect: "Inspection",
      milestone: "Mileage milestone",
      perform: "Scheduled service",
      replace: "Replacement",
    }[attributes.maintenance_type] || "Maintenance";
    return `<div class="backdrop"><section class="panel" role="dialog" aria-modal="true" aria-labelledby="maintenance-dialog-title" tabindex="-1">
      <header><div><small>${esc(typeLabel)}</small><h2 id="maintenance-dialog-title">${esc(attributes.service_name)}</h2></div><button class="close" aria-label="Close maintenance actions">×</button></header>
      <div class="why"><ha-icon icon="mdi:information-outline"></ha-icon><div><b>Why it matters</b><span>${esc(attributes.why_it_matters || "Keeping this item current supports safe, reliable vehicle operation.")}</span></div></div>
      <div class="facts">
        ${this.fact("Current odometer", odometer === null ? "Unavailable" : `${formatNumber(odometer)} mi`)}
        ${this.fact(initialInterval === null ? "Interval" : "Repeat interval", interval === null ? "Unavailable" : `${formatNumber(interval)} mi`)}
        ${initialInterval === null ? "" : this.fact("First due", `${formatNumber(initialInterval)} mi`)}
        ${this.fact("Next due", due === null ? (neverPerformed ? "Never performed" : "Unavailable") : `${formatNumber(due)} mi`)}
        ${target !== null && attributes.deferred ? this.fact("Extended until", `${formatNumber(target)} mi`) : ""}
      </div>
      ${this.error ? `<div class="error">${esc(this.error)}</div>` : ""}
      <div class="action-tabs" role="tablist" aria-label="Maintenance action">
        <button class="action-tab ${this.actionMode === "log" ? "active" : ""}" data-action-mode="log" role="tab" aria-selected="${this.actionMode === "log"}">Log Maintenance</button>
        <button class="action-tab ${this.actionMode === "extend" ? "active" : ""}" data-action-mode="extend" role="tab" aria-selected="${this.actionMode === "extend"}">Extend Maintenance</button>
      </div>
      ${this.actionMode === "log" ? this.logPanel(attributes, odometer) : this.extendPanel(attributes, odometer)}
    </section></div>`;
  }

  batchPanel() {
    if (!this.batchOpen) return "";
    const odometer = this.odometer();
    const services = this.batchEligibleServices();
    const selectedCount = this.batchServices.size;
    const mileageDetails = completionMileageDetails(this.batchMileage, odometer);
    const groups = [
      ["Scheduled Service and Replacements", new Set(["perform", "replace"])],
      ["Inspections", new Set(["inspect"])],
      ["Condition-Based Reminders", new Set(["condition"])],
      ["Mileage Milestones", new Set(["milestone"])],
    ];
    const groupedRows = groups.map(([label, kinds]) => {
      const matches = services.filter((entity) => kinds.has(entity.attributes.maintenance_type));
      if (!matches.length) return "";
      const rows = matches.map((entity) => {
        const attributes = entity.attributes;
        const display = servicePresentation(entity, odometer, this.config.upcoming_miles);
        const checked = this.batchServices.has(attributes.service_key) ? "checked" : "";
        return `<label class="batch-item ${esc(display.kind)}">
          <input type="checkbox" data-batch-service="${esc(attributes.service_key)}" ${checked}>
          <span class="service-icon"><ha-icon icon="${esc(attributes.icon || entity.attributes.icon || "mdi:wrench-outline")}"></ha-icon></span>
          <span class="row-copy"><b>${esc(attributes.service_name)}</b><small>${esc(display.detail)}</small></span>
        </label>`;
      }).join("");
      return `<section class="batch-group"><h3>${esc(label)}</h3>${rows}</section>`;
    }).join("");
    const currentText = selectedCount
      ? `Log ${selectedCount} ${selectedCount === 1 ? "item" : "items"} at ${formatNumber(odometer)} mi`
      : "Select maintenance first";
    const exactText = selectedCount && mileageDetails.valid
      ? `Log ${selectedCount} ${selectedCount === 1 ? "item" : "items"} at ${formatNumber(mileageDetails.mileage)} mi`
      : "Select maintenance and enter mileage";
    const preview = this.batchMileage === ""
      ? "Enter the mileage from when this visit was completed."
      : mileageDetails.valid
        ? `The same ${formatNumber(mileageDetails.mileage)} mi reading will be applied to every selected item.`
        : mileageDetails.error;
    return `<div class="backdrop batch-backdrop"><section class="panel batch-panel" role="dialog" aria-modal="true" aria-labelledby="batch-dialog-title" tabindex="-1">
      <header><div><small>Batch maintenance</small><h2 id="batch-dialog-title">Log a Service Visit</h2></div><button class="close batch-close" aria-label="Close service visit">×</button></header>
      <p class="batch-intro">Select everything completed during the same visit. One odometer reading will be applied to all selected items.</p>
      ${this.error ? `<div class="error">${esc(this.error)}</div>` : ""}
      <div class="batch-tools"><button class="text-button select-due" type="button">Select Due Items</button><button class="text-button clear-batch" type="button" ${selectedCount ? "" : "disabled"}>Clear</button><b class="batch-count">${selectedCount} selected</b></div>
      <div class="batch-list">${groupedRows}</div>
      <div class="batch-log-actions">
        <h3>Use the current odometer</h3>
        <button class="primary batch-log-current" ${odometer === null || !selectedCount ? "disabled" : ""}>${odometer === null ? "Odometer unavailable" : esc(currentText)}</button>
        <div class="divider"><span>or completed earlier</span></div>
        <label for="batch-mileage">Mileage when completed</label>
        <input id="batch-mileage" class="batch-mileage" type="number" inputmode="numeric" min="1" step="1" placeholder="Enter exact mileage" value="${esc(this.batchMileage)}">
        <div class="inline-message batch-mileage-result ${this.batchMileage !== "" && !mileageDetails.valid ? "invalid" : ""}">${esc(preview)}</div>
        <button class="secondary batch-log-exact" ${selectedCount && mileageDetails.valid ? "" : "disabled"}>${esc(exactText)}</button>
        <small>Each recurring item keeps its own interval. Any active extension on a logged item is cleared.</small>
      </div>
    </section></div>`;
  }

  render() {
    if (!this.config || !this._hass) return;
    const main = this.main();
    if (!this.config.main_entity || !main) {
      this.innerHTML = `<ha-card><div class="empty"><b>Select a vehicle.</b><span>Open the visual editor and choose a Vehicle Maintenance entry.</span></div></ha-card>`;
      return;
    }

    const all = this.services();
    const shown = this.visibleServices();
    const odometer = this.odometer();
    const neverPerformed = all.filter(isNeverPerformed).length;
    const extended = all.filter((entity) => entity.attributes.deferred).length;
    const overdue = all.filter((entity) => !entity.attributes.deferred && finiteNumber(entity.attributes.miles_remaining) < 0).length;
    const dueSoon = all.filter((entity) => {
      const remaining = finiteNumber(entity.attributes.miles_remaining);
      return isDueSoonService(entity, this.config.upcoming_miles) && remaining !== null && remaining >= 0;
    }).length;
    const source = String(main.attributes.odometer_source || "unavailable");
    const odometerText = odometer === null
      ? "Odometer unavailable"
      : `${formatNumber(odometer)} mi · ${source.charAt(0).toUpperCase()}${source.slice(1)}`;
    const accentColor = this.config.accent_color || "var(--primary-color)";
    this.style.setProperty("--vm-accent", accentColor);
    this.style.setProperty("--vm-on-accent", accentTextColor(this.config.accent_color));

    this.innerHTML = `<style>
      vehicle-maint-card{display:block}
      ha-card{overflow:hidden;border-radius:24px}
      button,input{font:inherit}
      .hero{display:flex;gap:14px;align-items:center;padding:21px;background:linear-gradient(135deg,color-mix(in srgb,var(--vm-accent) 16%,var(--ha-card-background)),var(--ha-card-background) 70%)}
      .car{display:grid;place-items:center;width:52px;height:52px;border-radius:18px;color:var(--vm-accent);background:color-mix(in srgb,var(--vm-accent) 18%,transparent)}
      .title{flex:1;min-width:0}.title b,.title small{display:block}.title b{overflow:hidden;font-size:1.25rem;text-overflow:ellipsis;white-space:nowrap}.title small{color:var(--secondary-text-color);margin-top:3px}
      .chips{display:flex;gap:8px;padding:12px 18px;overflow-x:auto;border-bottom:1px solid var(--divider-color)}.chip{flex:0 0 auto;padding:6px 10px;border-radius:14px;background:var(--secondary-background-color);font-size:.82rem;font-weight:600}.chip.overdue{color:var(--error-color)}.chip.extended{color:var(--vm-accent)}
      .views{display:flex;gap:8px;padding:12px 18px;border-bottom:1px solid var(--divider-color)}.views button{flex:1;min-height:42px;border:0;border-radius:12px;padding:9px;background:transparent;color:var(--secondary-text-color);font-weight:700}.views button.active,.action-tab.active{background:color-mix(in srgb,var(--vm-accent) 16%,transparent);color:var(--vm-accent)}
      .card-actions{padding:12px 18px 0}.batch-open{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;min-height:44px;border:1px solid color-mix(in srgb,var(--vm-accent) 45%,var(--divider-color));border-radius:13px;background:color-mix(in srgb,var(--vm-accent) 10%,transparent);color:var(--vm-accent);font-weight:800}
      .section-title{margin:0;padding:15px 18px 8px;font-size:1rem}.row{display:flex;border-top:1px solid var(--divider-color)}.row-main{display:flex;align-items:center;gap:12px;min-height:68px;flex:1;min-width:0;padding:9px 10px 9px 18px;border:0;background:transparent;color:var(--primary-text-color);text-align:left}.row-main:hover{background:color-mix(in srgb,var(--vm-accent) 7%,transparent)}
      .service-icon{display:grid;place-items:center;width:40px;height:40px;flex:0 0 40px;border-radius:13px;background:var(--secondary-background-color);color:var(--vm-accent)}.row-copy{display:flex;flex:1;min-width:0;flex-direction:column}.row-copy b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.row-copy small{color:var(--secondary-text-color);margin-top:3px}.row-value{flex:0 0 auto;max-width:95px;font-size:.76rem;font-weight:800;text-align:right}
      .overdue .row-value{color:var(--error-color)}.due .row-value{color:var(--warning-color,#ff9800)}.never .row-value,.extended .row-value{color:var(--vm-accent)}.completed .row-value,.okay .row-value{color:var(--success-color,#4caf50)}
      .info{width:46px;min-height:68px;border:0;background:transparent;color:var(--secondary-text-color)}.empty{display:flex;flex-direction:column;gap:6px;padding:28px 20px;text-align:center;color:var(--secondary-text-color)}.empty b{color:var(--primary-text-color)}
      .backdrop{position:fixed;inset:0;z-index:1000;box-sizing:border-box;display:flex;align-items:center;justify-content:center;padding:16px;background:#0009}
      .panel{box-sizing:border-box;width:min(100%,620px);max-height:92vh;max-height:calc(100dvh - 32px);overflow:auto;overscroll-behavior:contain;padding:20px;border-radius:24px;background:var(--card-background-color);color:var(--primary-text-color);box-shadow:0 18px 60px #0008}.panel header{display:flex;justify-content:space-between;align-items:flex-start}.panel header>div>small{color:var(--secondary-text-color)}.panel h2{margin:2px 0 14px}.close{width:44px;height:44px;border:0;background:transparent;color:var(--primary-text-color);font-size:2rem}
      .why{display:flex;align-items:flex-start;gap:10px;margin-bottom:14px;padding:12px 13px;border-left:4px solid var(--vm-accent);border-radius:10px;background:color-mix(in srgb,var(--vm-accent) 10%,var(--secondary-background-color))}.why>ha-icon{flex:0 0 auto;margin-top:1px;color:var(--vm-accent)}.why div{display:flex;min-width:0;flex-direction:column;gap:3px}.why b{font-size:.84rem}.why span{color:var(--secondary-text-color);font-size:.86rem;line-height:1.35}
      .facts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px}.facts span{padding:10px;border-radius:12px;background:var(--secondary-background-color)}.facts small,.facts b{display:block}.facts small{color:var(--secondary-text-color);font-size:.76rem}.facts b{margin-top:3px}
      .action-tabs{display:flex;gap:7px;margin-top:14px;padding:4px;border-radius:14px;background:var(--secondary-background-color)}.action-tab{flex:1;min-height:44px;border:0;border-radius:11px;background:transparent;color:var(--secondary-text-color);font-weight:700}
      .workflow{padding-top:14px}.workflow h3{margin:0 0 10px;font-size:1rem}.workflow label{display:block;margin:12px 0 6px;color:var(--secondary-text-color);font-size:.85rem}.workflow input{box-sizing:border-box;width:100%;min-height:48px;padding:0 12px;border:1px solid var(--divider-color);border-radius:12px;background:var(--secondary-background-color);color:var(--primary-text-color)}
      .primary,.secondary,.text{width:100%;min-height:48px;margin-top:10px;border:0;border-radius:13px;font-weight:800}.primary{background:var(--vm-accent);color:var(--vm-on-accent)}.secondary{background:color-mix(in srgb,var(--vm-accent) 16%,transparent);color:var(--vm-accent)}.text{background:transparent;color:var(--vm-accent)}button:disabled{cursor:not-allowed;opacity:.45}.workflow>small{display:block;margin-top:8px;color:var(--secondary-text-color)}
      .divider{display:flex;align-items:center;gap:10px;margin:18px 0 4px;color:var(--secondary-text-color);font-size:.78rem;text-transform:uppercase}.divider:before,.divider:after{content:"";height:1px;flex:1;background:var(--divider-color)}.inline-message{min-height:20px;margin-top:8px;color:var(--secondary-text-color);font-size:.84rem}.inline-message.invalid{color:var(--error-color)}
      .extension-choices{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.choice{min-height:44px;padding:6px;border:1px solid var(--divider-color);border-radius:11px;background:transparent;color:var(--primary-text-color);font-size:.82rem;font-weight:700}.choice.selected{border-color:var(--vm-accent);background:color-mix(in srgb,var(--vm-accent) 14%,transparent);color:var(--vm-accent)}
      .batch-intro{margin:0 0 12px;color:var(--secondary-text-color)}.batch-tools{display:grid;grid-template-columns:auto auto 1fr;align-items:center;gap:8px;margin:12px 0}.text-button{min-height:38px;padding:6px 10px;border:0;border-radius:10px;background:color-mix(in srgb,var(--vm-accent) 12%,transparent);color:var(--vm-accent);font-weight:700}.batch-count{text-align:right;font-size:.84rem}.batch-list{max-height:38vh;overflow:auto;overscroll-behavior:contain;border:1px solid var(--divider-color);border-radius:14px}.batch-group h3{position:sticky;top:0;z-index:1;margin:0;padding:9px 12px;background:var(--secondary-background-color);font-size:.78rem;text-transform:uppercase;color:var(--secondary-text-color)}.batch-item{display:flex;align-items:center;gap:10px;min-height:58px;padding:7px 11px;border-top:1px solid var(--divider-color)}.batch-item input{width:22px;height:22px;flex:0 0 22px;accent-color:var(--vm-accent)}.batch-item .service-icon{width:36px;height:36px;flex-basis:36px}.batch-log-actions{padding-top:15px}.batch-log-actions h3{margin:0 0 8px;font-size:1rem}.batch-log-actions>label{display:block;margin:12px 0 6px;color:var(--secondary-text-color);font-size:.85rem}.batch-log-actions>input{box-sizing:border-box;width:100%;min-height:48px;padding:0 12px;border:1px solid var(--divider-color);border-radius:12px;background:var(--secondary-background-color);color:var(--primary-text-color)}.batch-log-actions>small{display:block;margin-top:8px;color:var(--secondary-text-color)}
      .notice{display:flex;flex-direction:column;gap:5px;padding:14px;border-radius:13px;background:var(--secondary-background-color)}.notice span{color:var(--secondary-text-color)}.error{padding:11px;border-radius:11px;background:color-mix(in srgb,var(--error-color) 18%,transparent);color:var(--error-color)}[hidden]{display:none!important}
      @media(max-width:430px){.hero{padding:18px}.panel{padding:17px}.extension-choices{grid-template-columns:1fr 1fr}.facts{grid-template-columns:1fr 1fr}.row-value{max-width:80px}.chips{padding-inline:14px}.batch-tools{grid-template-columns:1fr 1fr}.batch-count{grid-column:1/-1;text-align:left}}
    </style>
    <ha-card>
      <div class="hero"><span class="car"><ha-icon icon="mdi:car"></ha-icon></span><span class="title"><b>${esc(main.attributes.vehicle_name || main.attributes.friendly_name)}</b><small>${esc(odometerText)}</small></span></div>
      <div class="chips"><span class="chip overdue">${overdue} overdue</span><span class="chip">${dueSoon} due soon</span><span class="chip extended">${extended} extended</span><span class="chip">${neverPerformed} never performed</span></div>
      <div class="views"><button data-view="due" class="${this.view === "due" ? "active" : ""}">Due Soon</button><button data-view="all" class="${this.view === "all" ? "active" : ""}">All Maintenance</button></div>
      <div class="card-actions"><button class="batch-open" type="button"><ha-icon icon="mdi:clipboard-check-outline"></ha-icon>Log a Service Visit</button></div>
      <h3 class="section-title">${this.view === "due" ? "Needs Attention" : "All Maintenance"}</h3>
      ${this.serviceRows(shown)}
    </ha-card>${this.actionPanel()}${this.batchPanel()}`;

    this.querySelectorAll("[data-view]").forEach((button) => {
      button.onclick = () => { this.view = button.dataset.view; this.render(); };
    });
    this.querySelectorAll("[data-service]").forEach((button) => {
      button.onclick = () => this.selectService(button.dataset.service);
    });
    this.querySelectorAll("[data-info]").forEach((button) => {
      button.onclick = () => this.moreInfo(button.dataset.info);
    });
    this.querySelector(".batch-open")?.addEventListener("click", () => this.openBatch());
    this.bindPanel();
    this.bindBatchPanel();
  }

  bindPanel() {
    if (!this.selectedService) return;
    const entity = this.selectedEntity();
    if (!entity) return;
    const attributes = entity.attributes;
    const odometer = this.odometer();
    const panel = this.querySelector(".panel");
    const close = () => { this.selectedService = null; this.error = ""; this.render(); };
    this.querySelector(".close").onclick = close;
    this.querySelector(".backdrop").onclick = (event) => { if (event.target === event.currentTarget) close(); };
    panel.onkeydown = (event) => { if (event.key === "Escape") close(); };

    this.querySelectorAll("[data-action-mode]").forEach((button) => {
      button.onclick = () => { this.actionMode = button.dataset.actionMode; this.error = ""; this.render(); };
    });

    const currentButton = this.querySelector(".log-current");
    if (currentButton) {
      currentButton.onclick = () => {
        if (odometer === null) return;
        this.call("log_maintenance", { service: this.selectedService }, `${attributes.service_name} logged at ${formatNumber(odometer)} mi`);
      };
    }

    const completionInput = this.querySelector(".completion");
    const exactButton = this.querySelector(".log-exact");
    const completionResult = this.querySelector(".completion-result");
    const refreshCompletion = () => {
      this.completionMileage = completionInput.value;
      const details = completionDetails(completionInput.value, odometer, attributes.interval_miles, Boolean(attributes.milestone));
      exactButton.disabled = !details.valid;
      exactButton.textContent = details.valid ? `Log at ${formatNumber(details.mileage)} mi` : "Enter completion mileage";
      completionResult.classList.toggle("invalid", completionInput.value !== "" && !details.valid);
      completionResult.textContent = completionInput.value === ""
        ? "Enter the mileage from when the work was completed."
        : details.valid
          ? attributes.milestone
            ? `This will mark the milestone complete at ${formatNumber(details.mileage)} mi.`
            : `Next due at ${formatNumber(details.nextDue)} mi.`
          : details.error;
    };
    if (completionInput && exactButton) {
      completionInput.oninput = refreshCompletion;
      exactButton.onclick = () => {
        const details = completionDetails(completionInput.value, odometer, attributes.interval_miles, Boolean(attributes.milestone));
        if (!details.valid) { refreshCompletion(); return; }
        this.call("log_maintenance", { service: this.selectedService, mileage: details.mileage }, `${attributes.service_name} logged at ${formatNumber(details.mileage)} mi`);
      };
    }

    this.querySelectorAll("[data-extension]").forEach((button) => {
      button.onclick = () => {
        this.extensionChoice = button.dataset.extension;
        if (this.extensionChoice === "custom" && this.customExtension === String(this.config.extend_miles)) this.customExtension = "";
        this.error = "";
        this.render();
      };
    });

    const customInput = this.querySelector(".custom-extension");
    const extendButton = this.querySelector(".extend-action");
    const extensionResult = this.querySelector(".extension-result");
    const refreshExtension = () => {
      this.customExtension = customInput.value;
      const details = extensionDetails(odometer, customInput.value);
      extendButton.disabled = !details.valid;
      extendButton.textContent = details.valid ? `Extend until ${formatNumber(details.target)} mi` : "Extension unavailable";
      extensionResult.classList.toggle("invalid", !details.valid);
      extensionResult.textContent = details.valid ? `This maintenance will return at ${formatNumber(details.target)} mi.` : details.error;
    };
    if (customInput && extendButton) customInput.oninput = refreshExtension;

    if (extendButton) {
      extendButton.onclick = () => {
        const amount = this.extensionChoice === "custom" ? this.customExtension : this.extensionChoice;
        const details = extensionDetails(odometer, amount);
        if (!details.valid) {
          if (customInput) refreshExtension();
          return;
        }
        this.call("snooze_maintenance", { service: this.selectedService, miles: details.miles }, `${attributes.service_name} extended until ${formatNumber(details.target)} mi`);
      };
    }

    this.querySelector(".clear-extension")?.addEventListener("click", () => {
      this.call("clear_snooze", { service: this.selectedService }, `Extension cleared for ${attributes.service_name}`);
    });
  }

  bindBatchPanel() {
    if (!this.batchOpen) return;
    const services = this.batchEligibleServices();
    const odometer = this.odometer();
    const panel = this.querySelector(".batch-panel");
    const checkboxes = [...this.querySelectorAll("[data-batch-service]")];
    const count = this.querySelector(".batch-count");
    const clearButton = this.querySelector(".clear-batch");
    const currentButton = this.querySelector(".batch-log-current");
    const exactButton = this.querySelector(".batch-log-exact");
    const mileageInput = this.querySelector(".batch-mileage");
    const mileageResult = this.querySelector(".batch-mileage-result");
    const close = () => {
      this.batchOpen = false;
      this.batchServices.clear();
      this.batchMileage = "";
      this.error = "";
      this.render();
    };
    const refresh = () => {
      const selectedCount = this.batchServices.size;
      const details = completionMileageDetails(this.batchMileage, odometer);
      count.textContent = `${selectedCount} selected`;
      clearButton.disabled = !selectedCount;
      currentButton.disabled = odometer === null || !selectedCount;
      currentButton.textContent = odometer === null
        ? "Odometer unavailable"
        : selectedCount
          ? `Log ${selectedCount} ${selectedCount === 1 ? "item" : "items"} at ${formatNumber(odometer)} mi`
          : "Select maintenance first";
      exactButton.disabled = !selectedCount || !details.valid;
      exactButton.textContent = selectedCount && details.valid
        ? `Log ${selectedCount} ${selectedCount === 1 ? "item" : "items"} at ${formatNumber(details.mileage)} mi`
        : "Select maintenance and enter mileage";
      mileageResult.classList.toggle("invalid", this.batchMileage !== "" && !details.valid);
      mileageResult.textContent = this.batchMileage === ""
        ? "Enter the mileage from when this visit was completed."
        : details.valid
          ? `The same ${formatNumber(details.mileage)} mi reading will be applied to every selected item.`
          : details.error;
    };
    const selectKeys = (keys) => {
      this.batchServices = new Set(keys);
      checkboxes.forEach((checkbox) => {
        checkbox.checked = this.batchServices.has(checkbox.dataset.batchService);
      });
      refresh();
    };

    this.querySelector(".batch-close").onclick = close;
    this.querySelector(".batch-backdrop").onclick = (event) => {
      if (event.target === event.currentTarget) close();
    };
    panel.onkeydown = (event) => { if (event.key === "Escape") close(); };
    checkboxes.forEach((checkbox) => {
      checkbox.onchange = () => {
        if (checkbox.checked) this.batchServices.add(checkbox.dataset.batchService);
        else this.batchServices.delete(checkbox.dataset.batchService);
        refresh();
      };
    });
    this.querySelector(".select-due").onclick = () => selectKeys(
      services
        .filter((entity) => isDueSoonService(entity, this.config.upcoming_miles))
        .map((entity) => entity.attributes.service_key),
    );
    clearButton.onclick = () => selectKeys([]);
    mileageInput.oninput = () => {
      this.batchMileage = mileageInput.value;
      refresh();
    };
    currentButton.onclick = () => {
      if (odometer === null || !this.batchServices.size) return;
      const selected = [...this.batchServices];
      this.call(
        "log_maintenance_batch",
        { services: selected },
        `${selected.length} maintenance ${selected.length === 1 ? "item" : "items"} logged at ${formatNumber(odometer)} mi`,
      );
    };
    exactButton.onclick = () => {
      const details = completionMileageDetails(this.batchMileage, odometer);
      if (!details.valid || !this.batchServices.size) { refresh(); return; }
      const selected = [...this.batchServices];
      this.call(
        "log_maintenance_batch",
        { services: selected, mileage: details.mileage },
        `${selected.length} maintenance ${selected.length === 1 ? "item" : "items"} logged at ${formatNumber(details.mileage)} mi`,
      );
    };
  }
}

class VehicleMaintCardEditor extends HTMLElement {
  setConfig(config) {
    this.config = normalizeConfig(config);
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  changed(key, value) {
    const next = { ...this.config };
    if (value === null || value === undefined || value === "") delete next[key];
    else next[key] = value;
    this.config = normalizeConfig(next);
    this.dispatchEvent(new CustomEvent("config-changed", {
      bubbles: true,
      composed: true,
      detail: { config: this.config },
    }));
  }

  render() {
    if (!this._hass || !this.config) return;
    const vehicles = Object.values(this._hass.states)
      .filter((entity) => entity.attributes.integration === DOMAIN && entity.attributes.entry_id && !entity.attributes.service_key);
    this.innerHTML = `<div>
      <label for="vehicle">Vehicle</label>
      <select id="vehicle" class="vehicle"><option value="">Select a vehicle</option>${vehicles.map((entity) => `<option value="${esc(entity.entity_id)}" ${entity.entity_id === this.config.main_entity ? "selected" : ""}>${esc(entity.attributes.vehicle_name || entity.attributes.friendly_name)}</option>`).join("")}</select>
      <label for="upcoming">Due Soon window in miles</label>
      <input id="upcoming" class="upcoming" type="number" min="1" step="1" value="${this.config.upcoming_miles}">
      <label for="extend">Default extension in miles</label>
      <input id="extend" class="extend" type="number" min="1" step="1" value="${this.config.extend_miles}">
      <label for="accent">Card accent color</label>
      <div class="color-row"><input id="accent" class="accent" type="color" value="${this.config.accent_color || "#2196f3"}"><button type="button" class="reset-accent" ${this.config.accent_color ? "" : "disabled"}>Use Home Assistant theme</button></div>
      <small>${this.config.accent_color ? `Using custom accent ${esc(this.config.accent_color)}.` : "Using the current Home Assistant theme color."}</small>
    </div><style>label{display:block;margin:12px 0 5px}select,input{box-sizing:border-box;width:100%;min-height:44px;padding:0 10px}.color-row{display:grid;grid-template-columns:64px 1fr;gap:10px}.color-row input{padding:4px}.color-row button{min-height:44px;padding:0 12px;border:1px solid var(--divider-color);border-radius:8px;background:var(--secondary-background-color);color:var(--primary-text-color)}small{display:block;margin-top:5px;color:var(--secondary-text-color)}</style>`;
    this.querySelector(".vehicle").onchange = (event) => this.changed("main_entity", event.target.value);
    this.querySelector(".upcoming").onchange = (event) => {
      const value = positiveInteger(event.target.value);
      if (value !== null) this.changed("upcoming_miles", value);
    };
    this.querySelector(".extend").onchange = (event) => {
      const value = positiveInteger(event.target.value);
      if (value !== null) this.changed("extend_miles", value);
    };
    this.querySelector(".accent").onchange = (event) => {
      const value = normalizeAccentColor(event.target.value);
      if (value !== null) this.changed("accent_color", value);
    };
    this.querySelector(".reset-accent").onclick = () => this.changed("accent_color", null);
  }
}

if (!customElements.get("vehicle-maint-card")) customElements.define("vehicle-maint-card", VehicleMaintCard);
if (!customElements.get("vehicle-maint-card-editor")) customElements.define("vehicle-maint-card-editor", VehicleMaintCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "vehicle-maint-card",
  name: "Vehicle Maintenance Card",
  description: "Simple mileage-based vehicle maintenance tracking",
  preview: true,
});
console.info(`%c VEHICLE-MAINT-CARD %c v${CARD_VERSION} `, "color:white;background:#455a64;font-weight:700", "color:#455a64;background:white");

if (typeof module !== "undefined") {
  module.exports = {
    VehicleMaintCard,
    accentTextColor,
    completionDetails,
    completionMileageDetails,
    extensionDetails,
    finiteNumber,
    isDueSoonService,
    isNeverPerformed,
    normalizeConfig,
    normalizeAccentColor,
    positiveNumber,
    servicePresentation,
  };
}
