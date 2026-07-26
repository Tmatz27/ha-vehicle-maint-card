const CARD_VERSION = "0.2.2";
const DOMAIN = "vehicle_maintenance";
const DEFAULT_UPCOMING_MILES = 2000;
const DEFAULT_EXTEND_MILES = 1000;

// Load the actual card from the same integration-owned frontend directory.
// The version query keeps every Home Assistant client on the same release.
const coreUrl = new URL(`./vehicle-maint-card.js?v=${CARD_VERSION}`, import.meta.url).href;
await import(coreUrl);

const Card = customElements.get("vehicle-maint-card");
const Editor = customElements.get("vehicle-maint-card-editor");
let instanceCounter = 0;

const completedMilestone = (entity) => Boolean(
  entity?.attributes?.milestone && entity.attributes.milestone_completed,
);

const positiveInteger = (value) => {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
};

const normalizeEditorConfig = (config = {}) => {
  const { snooze_miles: legacyExtendMiles, ...rest } = config;
  const normalized = {
    ...rest,
    upcoming_miles: positiveInteger(config.upcoming_miles) ?? DEFAULT_UPCOMING_MILES,
    extend_miles: positiveInteger(config.extend_miles)
      ?? positiveInteger(legacyExtendMiles)
      ?? DEFAULT_EXTEND_MILES,
  };
  const accent = typeof config.accent_color === "string"
    && /^#[0-9a-f]{6}$/i.test(config.accent_color.trim())
    ? config.accent_color.trim().toLowerCase()
    : null;
  if (accent === null) delete normalized.accent_color;
  else normalized.accent_color = accent;
  return normalized;
};

const editorConfigSignature = (config = {}) => {
  const normalized = normalizeEditorConfig(config);
  return JSON.stringify({
    main_entity: normalized.main_entity || "",
    upcoming_miles: normalized.upcoming_miles,
    extend_miles: normalized.extend_miles,
    accent_color: normalized.accent_color || "",
  });
};

const scopeRuleList = (rules, hostSelector) => {
  [...(rules || [])].forEach((rule) => {
    if (typeof rule.selectorText === "string") {
      rule.selectorText = rule.selectorText
        .split(",")
        .map((selector) => {
          const trimmed = selector.trim();
          if (!trimmed || trimmed.startsWith(hostSelector)) return trimmed;
          return `${hostSelector} ${trimmed}`;
        })
        .join(", ");
      return;
    }
    if (rule.cssRules) scopeRuleList(rule.cssRules, hostSelector);
  });
};

const scopeStyles = (root, hostSelector) => {
  root.querySelectorAll("style").forEach((style) => {
    if (style.dataset.vehicleMaintScoped === "true") return;
    try {
      scopeRuleList(style.sheet?.cssRules, hostSelector);
      style.dataset.vehicleMaintScoped = "true";
    } catch (error) {
      console.warn("Vehicle Maintenance could not scope an inline style block", error);
    }
  });
};

const namespaceIds = (root, prefix) => {
  if (!root.__vehicleMaintInstanceId) {
    instanceCounter += 1;
    root.__vehicleMaintInstanceId = `${prefix}-${instanceCounter}`;
  }
  const idMap = new Map();
  root.querySelectorAll("[id]").forEach((element) => {
    const original = element.id;
    const namespaced = `${root.__vehicleMaintInstanceId}-${original}`;
    idMap.set(original, namespaced);
    element.id = namespaced;
  });
  root.querySelectorAll("[for]").forEach((element) => {
    const target = idMap.get(element.getAttribute("for"));
    if (target) element.setAttribute("for", target);
  });
  root.querySelectorAll("[aria-labelledby]").forEach((element) => {
    const values = element.getAttribute("aria-labelledby").split(/\s+/);
    element.setAttribute(
      "aria-labelledby",
      values.map((value) => idMap.get(value) || value).join(" "),
    );
  });
};

if (Card && !Card.prototype.__vehicleMaintCardHardened) {
  const originalHass = Object.getOwnPropertyDescriptor(Card.prototype, "hass");
  const originalRender = Card.prototype.render;

  // Cache the vehicle's service entities. The original card scanned every Home
  // Assistant entity several times during one render. Keep every service ID for
  // change detection, but do not return completed one-time milestones to the card.
  Card.prototype.services = function services() {
    const entryId = this.entryId();
    if (!entryId || !this._hass) return [];
    if (this.__vehicleMaintServices?.entryId === entryId) {
      return this.__vehicleMaintServices.visible;
    }

    const all = Object.values(this._hass.states)
      .filter((entity) => entity.attributes.entry_id === entryId && entity.attributes.service_key)
      .sort((left, right) => {
        const distance = this.serviceSortValue(left) - this.serviceSortValue(right);
        if (distance !== 0) return distance;
        return String(left.attributes.service_name || "").localeCompare(
          String(right.attributes.service_name || ""),
        );
      });

    this.serviceEntityIds = all.map((entity) => entity.entity_id);
    const visible = all.filter((entity) => !completedMilestone(entity));
    this.__vehicleMaintServices = { entryId, visible };
    return visible;
  };

  if (originalHass?.set) {
    Object.defineProperty(Card.prototype, "hass", {
      configurable: true,
      set(hass) {
        const previous = this._hass;
        if (!previous || this.relevantStatesChanged(previous, hass)) {
          this.__vehicleMaintServices = null;
        }
        originalHass.set.call(this, hass);
      },
    });
  }

  // Keep the existing light-DOM implementation for compatibility, but scope its
  // CSS selectors to this custom element and namespace dialog/input IDs so two
  // vehicle cards cannot style or label each other's controls.
  Card.prototype.render = function render(...args) {
    const result = originalRender.apply(this, args);
    namespaceIds(this, "vm-card");
    scopeStyles(this, "vehicle-maint-card");
    return result;
  };

  Object.defineProperty(Card.prototype, "__vehicleMaintCardHardened", {
    configurable: false,
    value: true,
  });
}

if (Editor && !Editor.prototype.__vehicleMaintStableEditor) {
  const originalRender = Editor.prototype.render;
  const vehicleSignature = (hass) => Object.values(hass?.states || {})
    .filter((entity) => entity.attributes.integration === DOMAIN
      && entity.attributes.entry_id
      && !entity.attributes.service_key)
    .map((entity) => `${entity.entity_id}:${entity.attributes.vehicle_name || entity.attributes.friendly_name || ""}`)
    .sort()
    .join("|");

  const installFocusGuard = (editor) => {
    if (editor.__vehicleMaintFocusGuardInstalled) return;
    editor.__vehicleMaintFocusGuardInstalled = true;
    editor.addEventListener("focusout", () => {
      queueMicrotask(() => {
        if (editor.contains(document.activeElement)) return;
        if (!editor.__vehicleMaintRenderPending) return;
        editor.__vehicleMaintRenderPending = false;
        editor.render();
      });
    });
  };

  const renderWhenIdle = function renderWhenIdle() {
    installFocusGuard(this);
    if (this.contains(document.activeElement)) {
      this.__vehicleMaintRenderPending = true;
      return;
    }
    this.__vehicleMaintRenderPending = false;
    this.render();
  };

  // Home Assistant may call setConfig several times during one editor session.
  // Keep the normalized config current, but do not replace the editor DOM when
  // the values that this editor actually displays have not changed. A config
  // echo after the user's own change therefore cannot throw focus away.
  Editor.prototype.setConfig = function setConfig(config) {
    const previousSignature = this.config ? editorConfigSignature(this.config) : null;
    this.config = normalizeEditorConfig(config);
    const nextSignature = editorConfigSignature(this.config);
    this.__vehicleMaintConfigSignature = nextSignature;
    if (previousSignature === null || previousSignature !== nextSignature) {
      renderWhenIdle.call(this);
    }
  };

  // Home Assistant replaces the hass object frequently. Rebuilding the visual
  // editor on every replacement destroys an open select, color picker, or text
  // cursor. Only rebuild when the available Vehicle Maintenance entries change,
  // and even then wait until the user has left the active control.
  Object.defineProperty(Editor.prototype, "hass", {
    configurable: true,
    set(hass) {
      const signature = vehicleSignature(hass);
      const shouldRender = !this._hass || signature !== this._vehicleSignature;
      this._hass = hass;
      this._vehicleSignature = signature;
      if (shouldRender) renderWhenIdle.call(this);
    },
  });

  Editor.prototype.render = function render(...args) {
    const result = originalRender.apply(this, args);
    namespaceIds(this, "vm-editor");
    scopeStyles(this, "vehicle-maint-card-editor");
    return result;
  };

  Object.defineProperty(Editor.prototype, "__vehicleMaintStableEditor", {
    configurable: false,
    value: true,
  });
}

console.info(
  `%c VEHICLE-MAINT-CARD %c bootstrap v${CARD_VERSION} `,
  "color:white;background:#455a64;font-weight:700",
  "color:#455a64;background:white",
);