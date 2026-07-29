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
  carWashPresentation,
  completionDetails,
  completionMileageDetails,
  csvCell,
  extensionDetails,
  finiteNumber,
  isDueSoonService,
  isNeverPerformed,
  maintenanceCsv,
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

test("hero background keeps its accent tint even when the theme never sets --ha-card-background", () => {
  // Most Home Assistant themes only define --card-background-color. Without a
  // fallback here, color-mix() receives an invalid argument and the browser
  // drops the whole background declaration, silently hiding the accent tint.
  assert.equal(source.includes("var(--ha-card-background,var(--card-background-color))"), true);
  assert.equal(source.includes("color-mix(in srgb,var(--vm-accent) 16%,var(--ha-card-background))"), false);
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
    warning: "",
    miles: 1000,
    target: 45973,
  });
  assert.equal(extensionDetails(null, 1000).valid, false);
  assert.equal(extensionDetails(44973, "").valid, false);
});

test("an implausibly long extension warns without blocking a deliberate choice", () => {
  const typo = extensionDetails(44973, 100000);
  assert.equal(typo.valid, true);
  assert.equal(typo.target, 144973);
  assert.match(typo.warning, /very long extension/);

  // The threshold itself must stay quiet so normal deferrals are never nagged.
  assert.equal(extensionDetails(44973, 20000).warning, "");
  assert.equal(extensionDetails(44973, 2000).warning, "");
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

test("service visits are sorted by miles remaining instead of service type", () => {
  const card = new VehicleMaintCard();
  card.config = { main_entity: "sensor.vehicle", upcoming_miles: 2000 };
  card._hass = {
    states: {
      "sensor.vehicle": { attributes: { entry_id: "entry-1" } },
      "sensor.filter": {
        entity_id: "sensor.filter",
        attributes: {
          entry_id: "entry-1",
          service_key: "cabin_air_filter",
          service_name: "Cabin Air Filter",
          initialized: true,
          miles_remaining: 4000,
        },
      },
      "sensor.oil": {
        entity_id: "sensor.oil",
        attributes: {
          entry_id: "entry-1",
          service_key: "oil_change",
          service_name: "Oil Change",
          initialized: true,
          miles_remaining: -200,
        },
      },
      "sensor.rotation": {
        entity_id: "sensor.rotation",
        attributes: {
          entry_id: "entry-1",
          service_key: "tire_rotation",
          service_name: "Tire Rotation",
          initialized: true,
          miles_remaining: 900,
        },
      },
    },
  };

  assert.deepEqual(
    card.batchEligibleServices().map((entity) => entity.attributes.service_key),
    ["oil_change", "tire_rotation", "cabin_air_filter"],
  );
});

test("washable filters expose wash and replace actions plus filter-life facts", () => {
  assert.equal(source.includes("Wash / clean"), true);
  assert.equal(source.includes("Replace filter"), true);
  assert.equal(source.includes("filter_action"), true);
  assert.equal(source.includes("filter_actions"), true);
  assert.equal(source.includes("Times washed"), true);
  assert.equal(source.includes("Miles on this filter"), true);
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

test("csv cells escape quotes, commas, and newlines", () => {
  assert.equal(csvCell("Oil Change"), "Oil Change");
  assert.equal(csvCell(null), "");
  assert.equal(csvCell(undefined), "");
  assert.equal(csvCell(0), "0");
  assert.equal(csvCell("30,000 mi Service"), '"30,000 mi Service"');
  assert.equal(csvCell('He said "hi"'), '"He said ""hi"""');
  assert.equal(csvCell("line\nbreak"), '"line\nbreak"');
});

test("csv export snapshots current maintenance state without inventing history", () => {
  const services = [
    {
      attributes: {
        service_name: "Oil Change",
        status: "due_soon",
        last_completed_mileage: 40882,
        interval_miles: 6000,
        scheduled_due_mileage: 46882,
        miles_remaining: 1788,
        snoozed_until_mileage: null,
        washable: false,
      },
    },
    {
      attributes: {
        service_name: "Cabin Air Filter",
        status: "okay",
        last_completed_mileage: 37733,
        interval_miles: 12000,
        scheduled_due_mileage: 49733,
        miles_remaining: 4639,
        snoozed_until_mileage: null,
        washable: true,
        wash_count: 2,
        filter_installed_mileage: 37733,
      },
    },
  ];
  const csv = maintenanceCsv(services, "Outback", 45094);
  const lines = csv.split("\n");

  assert.equal(lines.length, 3);
  assert.match(lines[0], /^Vehicle,Odometer \(mi\),Service,Status,/);
  assert.equal(lines[1], "Outback,45094,Oil Change,due_soon,40882,6000,46882,1788,,,");
  assert.equal(
    lines[2],
    "Outback,45094,Cabin Air Filter,okay,37733,12000,49733,4639,,2,37733",
  );
});

test("csv export stays valid when the odometer is unavailable", () => {
  const csv = maintenanceCsv(
    [{ attributes: { service_name: "Oil Change", status: "unavailable", washable: false } }],
    "Forester",
    null,
  );
  assert.equal(csv.split("\n")[1], "Forester,,Oil Change,unavailable,,,,,,,");
});

test("car wash presentation is date based and never claims a wash that did not happen", () => {
  const entity = (attributes) => ({ attributes });

  assert.deepEqual(carWashPresentation(entity({ days_since_wash: null, days_remaining: null })), {
    kind: "never",
    detail: "Never washed",
    badge: "NEVER",
  });

  const overdue = carWashPresentation(entity({ days_since_wash: 20, days_remaining: -6 }));
  assert.equal(overdue.kind, "overdue");
  assert.equal(overdue.detail, "Washed 20 days ago");
  assert.equal(overdue.badge, "6 days over");

  assert.equal(carWashPresentation(entity({ days_since_wash: 14, days_remaining: 0 })).kind, "due");
  assert.equal(carWashPresentation(entity({ days_since_wash: 12, days_remaining: 2 })).kind, "due");
  assert.equal(carWashPresentation(entity({ days_since_wash: 3, days_remaining: 11 })).kind, "okay");

  // Singular day wording matters because this tile is read at a glance.
  assert.equal(carWashPresentation(entity({ days_since_wash: 1, days_remaining: 13 })).detail, "Washed 1 day ago");
  assert.equal(carWashPresentation(entity({ days_since_wash: 13, days_remaining: 1 })).badge, "1 day left");
});

test("a service visit pauses on a confirmation recap before writing records", () => {
  assert.equal(source.includes("batchConfirmPanel"), true);
  assert.equal(source.includes("batch-confirm-yes"), true);
  assert.equal(source.includes("batch-confirm-back"), true);
  // Both entry points must route through the recap rather than logging directly.
  assert.equal(source.includes("this.batchConfirm = { mileage: odometer, useCurrentOdometer: true }"), true);
  assert.equal(source.includes("this.batchConfirm = { mileage: details.mileage, useCurrentOdometer: false }"), true);
});

test("card exposes car wash and export affordances", () => {
  assert.equal(source.includes("carWashSection"), true);
  assert.equal(source.includes('"log_car_wash"'), true);
  assert.equal(source.includes("export-csv"), true);
  assert.equal(source.includes("Export CSV"), true);
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
