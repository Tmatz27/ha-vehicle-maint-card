const test = require("node:test");
const assert = require("node:assert/strict");
global.HTMLElement = class {};
global.customElements = { get() { return true; }, define() {} };
global.window = { customCards: [] };
global.document = { createElement() { return {}; } };
const { finiteNumber, positiveNumber, VehicleMaintCard } = require("../../custom_components/vehicle_maintenance/www/vehicle-maint-card.js");

test("unavailable and blank values never become zero", () => {
  for (const value of [null, undefined, "", "unknown", "unavailable", "NaN", NaN]) assert.equal(finiteNumber(value), null);
  assert.equal(finiteNumber("0"), 0);
});

test("reminder distances must be finite and positive", () => {
  for (const value of [null, "", "0", 0, -1, "nope", NaN]) assert.equal(positiveNumber(value), null);
  assert.equal(positiveNumber("1000"), 1000);
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
