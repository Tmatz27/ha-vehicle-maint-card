const CARD_VERSION = "0.2.1";
const DOMAIN = "vehicle_maintenance";

// Load the actual card from the same integration-owned frontend directory.
// The version query keeps every Home Assistant client on the same release.
const coreUrl = new URL(`./vehicle-maint-card.js?v=${CARD_VERSION}`, import.meta.url).href;
await import(coreUrl);

// Home Assistant replaces the `hass` object frequently, even when nothing the
// visual editor cares about changed. The original editor re-rendered its entire
// DOM on every replacement, which destroys an open native select/dropdown and
// makes it appear to close by itself. Patch the editor lifecycle so it only
// rebuilds when the available Vehicle Maintenance entries actually change.
const Editor = customElements.get("vehicle-maint-card-editor");

if (Editor && !Editor.prototype.__vehicleMaintStableEditor) {
  const vehicleSignature = (hass) => Object.values(hass?.states || {})
    .filter((entity) => entity.attributes.integration === DOMAIN
      && entity.attributes.entry_id
      && !entity.attributes.service_key)
    .map((entity) => `${entity.entity_id}:${entity.attributes.vehicle_name || entity.attributes.friendly_name || ""}`)
    .sort()
    .join("|");

  Object.defineProperty(Editor.prototype, "hass", {
    configurable: true,
    set(hass) {
      const signature = vehicleSignature(hass);
      const shouldRender = !this._hass || signature !== this._vehicleSignature;
      this._hass = hass;
      this._vehicleSignature = signature;
      if (shouldRender) this.render();
    },
  });

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
