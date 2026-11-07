# Rolewisp Free and Plus

Owner update, November 7: add a Free tier and one paid tier, with country-aware currency presentation. The owner has no payment-provider account yet. This is a real server-owned pricing catalogue and frontend handoff; paid checkout and subscriptions are not activated. No payment credentials, charges, revenue or paying users are implied.

## Product presentation

Public navigation: Find jobs, For you, Pricing, account control. Public pages contain job discovery, useful source/checked information and account features. Testing totals, CI, smoke runs, acquisition targets, repository identifiers, parser internals and deployment configuration stay in reviewer/engineering documentation. Coverage evidence remains available separately for acquisition review; do not hide or delete unfinished-platform facts.

Free keeps search, original applications and existing account/profile/resume/recommendation functionality when the account service is configured. Do not remove already implemented free features as part of this handoff. Plus is the paid plan name. Its prices below are initial editable proposals selected for the design, not demonstrated willingness to pay or a conversion from current exchange rates.

Since no provider is connected, Plus is visibly **Coming soon** and has no purchase action. A production deployment may instead hide Plus until launch. Do not create a fake checkout, fake subscription-success screen, payment test badge or inert Upgrade button. Do not collect payment details, add a nonfunctional waitlist or grant Plus through client-side state. Planned premium benefits require implementation and an entitlement contract before being advertised as available; this change does not invent them.

## Working API

GET `/api/v1/plans?country=IN` returns:

- Country-derived local tender currencies using Babel's bundled CLDR data; no IP lookup, geolocation or external exchange-rate call.
- Explicit display currency, integer minor-unit amounts and currency_exponent. JPY uses exponent 0; INR/USD/EUR use 2.
- Exactly Free and Plus, with availability, monthly interval, catalogue version and tax-inclusion flag.
- `paid_checkout_available=false`. This is fixed until an actual billing integration exists; setting a browser flag or environment variable cannot activate billing.

Country is an optional two-letter code. Missing country yields USD plus an instruction to select a country; no location is fabricated. Lowercase codes normalize. Invalid/unrecognized countries return 422. If the country's currency is not priced in the launch catalogue, the response explicitly returns USD and a fallback notice. **This is not a claim of local-currency checkout for every country.** Use a visible country selector and allow correction; browser-language hints are preferences, not proof of residence or billing country. Recheck regional metadata when updating the bundled CLDR version.

| Currency | Plus / month | Minor-unit amount |
| --- | ---: | ---: |
| USD | 6.00 | 600 |
| INR | 399.00 | 39900 |
| EUR | 6.00 | 600 |
| GBP | 5.00 | 500 |
| CAD | 8.00 | 800 |
| AUD | 9.00 | 900 |
| NZD | 10.00 | 1000 |
| SGD | 8.00 | 800 |
| AED | 22.00 | 2200 |
| JPY | 900 | 900 |
| BRL | 29.00 | 2900 |
| MXN | 99.00 | 9900 |
| CHF | 6.00 | 600 |

Free is zero in the same displayed currency. Format with Intl.NumberFormat using the response's currency and exponent. Never just replace a dollar symbol or multiply every currency by 100. Show ISO codes where symbols could be ambiguous. These are fixed regional prices, not daily FX equivalents. Taxes are not included in the catalogue; real tax calculation/disclosure remains part of the billing release.

## Before taking payments

Choose a provider compatible with the merchant's actual country, business status and subscription/presentment requirements. Provider selection is pending, not assumed to be Stripe. Official Stripe documentation currently notes invite-only onboarding for Indian businesses; a new Indian Stripe account cannot be assumed available: https://docs.stripe.com/india-accept-international-payments. Currency rules also depend on the actual provider/account: https://docs.stripe.com/currencies. Babel APIs: https://babel.pocoo.org/en/latest/api/numbers.html.

Then implement and test the real server-created hosted checkout, server-owned price mapping, authenticated billing portal, account/customer ownership, signed raw-body webhook verification, event idempotency/replay handling, durable subscription state and server-enforced entitlements. Verify actual currency and amount against the catalogue and provider price; client values, query parameters and success redirects are not proof of payment. Cover cancellation, expiry, failed payment, refunds, duplicate events and out-of-order events. Finalize paid benefits, taxes and regional support before enabling a purchase CTA.

Provider secrets stay server-side; no NEXT_PUBLIC secret, localStorage/sessionStorage credential, card input in our own app, real payment fixture in Git or sensitive billing content in logs. No processor account was created, no paid service purchased and no money charged in this work.
