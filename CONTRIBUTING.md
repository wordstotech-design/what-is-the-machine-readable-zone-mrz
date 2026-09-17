# Contributing

Corrections to the field layouts, the check digit math, or the writeup are welcome. Two constraints keep this repo useful.

## Every layout claim cites ICAO Doc 9303

TD1, TD2, and TD3 field positions, the character set, and the 7-3-1 check digit weighting come from ICAO Doc 9303, not from a blog post or a secondary summary. If you add or change a field position, link the relevant part of the standard in the PR description.

## The toolkit stays dependency free

- Python: standard library only, 3.8+.

```bash
python3 -m py_compile mrz_toolkit.py
python3 mrz_toolkit.py examples/passport_td3.txt
python3 mrz_toolkit.py examples/id_card_td1.txt
python3 mrz_toolkit.py examples/id_card_td2.txt
python3 mrz_toolkit.py examples/passport_td3_tampered.txt; test $? -eq 1
```

## Example data

Every MRZ string in `examples/` is either ICAO's own published worked example or a synthetic string built with the fictitious issuing state code `UTO`, which the standard reserves for demonstrations. No real document data goes into this repo, ever. A PR that adds a real MRZ string, real or scraped from a real document image, will be rejected regardless of intent.

## Compliance wording

This repo covers a public technical standard, not a legal opinion. Two rules:

- MRZ parsing and check digit validation is a data integrity check, not proof that a document is genuine. Do not word a claim in this repo, or in a PR description, to suggest otherwise.
- Any mention of a vendor's identity verification service should describe it as a verification layer that a regulated business builds a compliance program on top of, not as a guarantee of that business's own compliance.

## What gets rejected

- A rewrite of `mrz_toolkit.py` around a third party MRZ parsing library. The point is that the check digit math is visible and verifiable in one file.
- Real document data of any kind, including a reader's own passport or ID card.
- Legal or compliance advice, in any form, including confident statements about what a given jurisdiction requires from a document check.
