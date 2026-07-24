const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

global.HTMLElement = class {};
global.customElements = { get() { return true; }, define() {} };
global.window = { customCards: [] };
global.document = { createElement() { return {}; } };

const cardPath = path.join(__dirname, "../../custom_components/vehicle_maintenance/www/vehicle-maint-card.js");
const source = fs.readFileSync(cardPath, "utf8");
const {
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
} = require(cardPath);

test("unavailable and blank values never become zero", () => {
  for (const value of [null, undefined, "", "   ", "unknown", "unavailable", "NaN", NaN, Infinity]) {
    assert.equal(finiteNumber(value), null);
  }
  assert.equal(finiteNumber("0"), 0);
  assert.equal(finiteNumber("44973"), 44973);
});

test("extension distances must be finite and positive", () => {
  for (const value of [null, "", "0", 0, -1, "nope", NaN]) assert.equal(positiveNumber(value), null);
  assert.equal(positiveNumber("1000"), 1000);
});

test("public config uses extend_miles with a legacy alias", () => {
  assert.deepEqual(normalizeConfig({}), { upcoming_miles: 2000, extend_miles: 1000 });
  assert.equal(normalizeConfig({ snooze_miles: 500 }).extend_miles, 500);
  assert.equal(normalizeConfig({ extend_miles: 2000, snooze_miles: 500 }).extend_miles, 2000);
  assert.equal("snooze_miles" in normalizeConfig({ snooze_miles: 500 }), false);
});

test("accent colors are normalized safely and choose readable button text", () => {
  assert.equal(normalizeAccentColor(" #43A047 "), "#43a047");
  assert.equal(normalizeAccentColor("green"), null);
  assert.equal(normalizeAccentColor("#fff; color: red"), null);
  assert.equal(normalizeConfig({ accent_color: "#43A047" }).accent_color, "#43a047");
  assert.equal("accent_color" in normalizeConfig({ accent_color: "invalid" }), false);
  assert.equal(accentTextColor("#ffffff"), "#111111");
  assert.equal(accentTextColor("#1b5e20"), "#ffffff");
});

test("completion preview uses the exact entered mileage", () => {
  assert.deepEqual(completionDetails("43500", 44973, 6000, false), {
    valid: true,
    error: "",
    mileage: 43500,
    nextDue: 49500,
  });
});

test("completion validation rejects blank, zero, and future mileage", () => {
  assert.equal(completionDetails("", 44973, 6000).valid, false);
  assert.equal(completionDetails("0", 44973, 6000).valid, false);
  assert.match(completionDetails("45000", 44973, 6000).error, /greater than/);
  assert.equal(completionDetails("43500", null, 6000).valid, true);
});

test("batch completion accepts one factual mileage without requiring one interval", () => {
  assert.deepEqual(completionMileageDetails("43500", 44973), {
    valid: true,
    error: "",
    mileage: 43500,
  });
  assert.equal(completionMileageDetails("45000", 44973).valid, false);
  assert.equal(completionMileageDetails("", 44973).valid, false);
  assert.equal(completionMileageDetails("43500.5", 44973).valid, false);
});

test("extension target is always current odometer plus extension", () => {
  assert.deepEqual(extensionDetails(44973, 1000), {
    valid: true,
    error: "",
    miles: 1000,
    target: 45973,
  });
  assert.equal(extensionDetails(null, 1000).valid, false);
  assert.equal(extensionDetails(44973, "").valid, false);
});

test("Due Soon excludes unlogged, completed, unavailable, and extended services", () => {
  const entity = (attributes) => ({ attributes });
  assert.equal(isDueSoonService(entity({ initialized: true, miles_remaining: -100, status: "overdue", deferred: false }), 2000), true);
  assert.equal(isDueSoonService(entity({ initialized: true, miles_remaining: 1900, status: "due_soon", deferred: false }), 2000), true);
  assert.equal(isDueSoonService(entity({ initialized: true, miles_remaining: 2100, status: "okay", deferred: false }), 2000), false);
  assert.equal(isDueSoonService(entity({ initialized: false, miles_remaining: null, status: "setup_required", deferred: false }), 2000), false);
  assert.equal(isDueSoonService(entity({ initialized: true, miles_remaining: -100, status: "overdue", deferred: true }), 2000), false);
  assert.equal(isDueSoonService(entity({ initialized: true, miles_remaining: null, status: "unavailable", deferred: false }), 2000), false);
});

test("extended row shows its target instead of a strange negative result", () => {
  const display = servicePresentation({
    attributes: {
      initialized: true,
      deferred: true,
      miles_remaining: -14973,
      snoozed_until_mileage: 45973,
    },
  }, 44973);
  assert.equal(display.kind, "extended");
  assert.equal(display.detail, "Extended until 45,973 mi");
  assert.equal(display.badge, "1,000 mi");
});

test("never-performed services are explicit and still have a calculated schedule", () => {
  const entity = {
    attributes: {
      initialized: true,
      last_completed_mileage: 0,
      due_mileage_override: null,
      miles_remaining: -1000,
      status: "overdue",
    },
  };
  assert.equal(isNeverPerformed(entity), true);
  assert.deepEqual(servicePresentation(entity, 7000), {
    kind: "overdue",
    detail: "Never performed · 1,000 mi overdue",
    badge: "OVERDUE",
  });

  entity.attributes.due_mileage_override = 137500;
  entity.attributes.miles_remaining = 92527;
  entity.attributes.status = "okay";
  assert.equal(isNeverPerformed(entity), true);
  assert.deepEqual(servicePresentation(entity, 44973), {
    kind: "okay",
    detail: "Never performed · 92,527 mi remaining",
    badge: "92,527 mi",
  });
});

test("normal card source does not expose internal record editing", () => {
  for (const forbidden of [
    "Set maintenance history",
    "Apply history",
    "Advanced record editing",
    "Record state",
    "Due at known mileage",
    "apply-setup",
    "setup-mode",
  ]) {
    assert.equal(source.includes(forbidden), false, `Found forbidden card text: ${forbidden}`);
  }
  assert.equal(source.includes("Log Maintenance"), true);
  assert.equal(source.includes("Extend Maintenance"), true);
});

test("card offers one batch service-visit workflow", () => {
  assert.equal(source.includes("Log a Service Visit"), true);
  assert.equal(source.includes("Select Due Items"), true);
  assert.equal(source.includes('"log_maintenance_batch"'), true);
  assert.equal(source.includes("data-batch-service"), true);
});

test("batch logging excludes an already completed one-time milestone", () => {
  const card = new VehicleMaintCard();
  card.config = { main_entity: "sensor.vehicle", upcoming_miles: 2000 };
  card._hass = {
    states: {
      "sensor.vehicle": { attributes: { entry_id: "entry-1" } },
      "sensor.oil": {
        entity_id: "sensor.oil",
        attributes: { entry_id: "entry-1", service_key: "oil_change", milestone: false },
      },
      "sensor.60k": {
        entity_id: "sensor.60k",
        attributes: {
          entry_id: "entry-1",
          service_key: "service_60k",
          milestone: true,
          milestone_completed: true,
        },
      },
    },
  };

  assert.deepEqual(
    card.batchEligibleServices().map((entity) => entity.attributes.service_key),
    ["oil_change"],
  );
});

test("maintenance dialog is centered and the editor exposes accent color", () => {
  assert.equal(source.includes("align-items:center"), true);
  assert.equal(source.includes("align-items:flex-end"), false);
  assert.equal(source.includes("--vm-accent"), true);
  assert.equal(source.includes("Card accent color"), true);
  assert.equal(source.includes("Use Home Assistant theme"), true);
});

test("maintenance dialog includes a concise why it matters BLUF", () => {
  assert.equal(source.includes("Why it matters"), true);
  assert.equal(source.includes("attributes.why_it_matters"), true);
});

test("unrelated state changes do not trigger a card rebuild", () => {
  const card = new VehicleMaintCard();
  card.config = { main_entity: "sensor.vehicle" };
  card.serviceEntityIds = ["sensor.oil"];
  const main = { state: "okay" };
  const oil = { state: "1000" };
  const before = { states: { "sensor.vehicle": main, "sensor.oil": oil, "light.kitchen": { state: "off" } } };
  const unrelated = { states: { "sensor.vehicle": main, "sensor.oil": oil, "light.kitchen": { state: "on" } } };
  assert.equal(card.relevantStatesChanged(before, unrelated), false);
  const changed = { states: { "sensor.vehicle": main, "sensor.oil": { state: "900" } } };
  assert.equal(card.relevantStatesChanged(before, changed), true);
});
