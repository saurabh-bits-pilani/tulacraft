# Brief 4 — Price Suggestion AI

## Tasks

1. Add a "Suggest Price" button on the product listing form in producer
   dashboard.
2. Create new route `POST /producer/suggest-price`.
3. Input fields: `material_cost` (INR), `hours_spent`, `craft_category`.
4. Use Gemma 4 to suggest three price options: Budget / Standard / Premium.
5. Each option has a price in INR and a one-line reason.
6. Also show USD equivalent using exchangerate-api.com free tier.
7. Return JSON — seller clicks any price to auto-fill the price field on
   the form.

## Branch
`feature/price-suggestion`

## Test
Enter material cost 200, hours 3, category pottery — confirm three price
suggestions appear with INR and USD.

## Implementation notes

- Exchange rate: use the open endpoint `https://open.er-api.com/v6/latest/INR`
  (no key required). Cache the INR→USD rate for 6 hours per process so we
  don't hit the API on every suggestion.
- Validation: positive `material_cost` and `hours_spent`, non-empty
  `craft_category`. JSON 400 on invalid input.
- Gemma prompt returns strict JSON with three tiers; parser tolerates
  fenced code blocks and surrounding text.
- Auto-fill: click handler sets `#price` value and switches the currency
  dropdown to INR. Adds `INR` to currency options in `product_form.html`
  since the existing list (EUR / USD / GBP / RSD) lacks it — without
  this, clicking an INR suggestion would store an INR value labelled EUR.
- Scope: only `product_form.html` (new product). Edit form not changed
  per the brief's "product listing form" wording.
