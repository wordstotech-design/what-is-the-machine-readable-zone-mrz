# What Is the Machine Readable Zone (MRZ)

<p align="center">
  <a href="https://www.idenfy.com/">
 <img width="1659" height="935" alt="image" src="https://github.com/user-attachments/assets/d8a398e8-8ec1-430e-9cc3-fd9614650193" />

  </a>
</p>

Flip any passport to its photo page and the two dense lines of capital letters and numbers at the bottom are the [machine readable zone](https://idenfy.com/blog/machine-readable-zone/), or MRZ for short. That is the MRZ full form, and it is not a barcode or a chip. It is the same personal data already printed above it (name, document number, nationality, date of birth, sex, expiry date) laid out in a fixed width format that a scanner can lift with plain OCR, no special reader hardware required.

This repo pairs that explanation with something most write ups on the topic skip: a standard library only Python script, [mrz_toolkit.py](mrz_toolkit.py), that parses a real MRZ string and recomputes every ICAO check digit itself, rather than asking the reader to trust that the standard works as described.

## MRZ full form and what the zone actually encodes

MRZ stands for Machine Readable Zone. It is defined by [ICAO Doc 9303](https://www.icao.int/publications/doc-series/doc-9303), the same body that standardizes passport design worldwide, and it uses a restricted 39 character alphabet: the digits 0 to 9, the capital letters A to Z, and the filler character `<`, all printed in a fixed width font called OCR B so a scanner reads every character at a predictable position.

"Encoded" is the accurate word here, not "encrypted." Anyone who can read the zone, human or machine, can read the data. There is no key or cipher involved in the zone itself, which matters later when a reader asks what is MRZ on a passport actually protecting against. The answer is transcription errors and casual tampering, not confidentiality. A document check inside an [identity verification service](https://idenfy.com/identity-verification-service/) treats the MRZ as one input among several, alongside the visual inspection of the document and, where the document has a chip, a cryptographic check that the MRZ alone cannot perform.

## The three ICAO formats: TD1, TD2, TD3

ICAO Doc 9303 defines three machine readable zone layouts, and confusing them is the most common mistake when writing a parser.

| Format | Lines x width | Typical document | Character budget |
| --- | --- | --- | --- |
| TD1 | 3 lines of 30 characters | National ID cards, driver licenses | 90 characters |
| TD2 | 2 lines of 36 characters | A smaller set of ID cards | 72 characters |
| TD3 | 2 lines of 44 characters | Passports and passport booklets | 88 characters |

TD3 is the format most people picture when they think of machine readable zone passport data, since it is the one printed at the bottom of a passport's data page. TD1 fits the shorter, wider layout of a credit card sized national ID. TD2 shares TD3's two line structure but drops the separate personal number field to fit a narrower card.

## Reading a real MRZ line by line

Here is a TD3 example straight from ICAO's own published specification, using the fictitious issuing state code `UTO` that the standard reserves for worked examples:

```
P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<
L898902C36UTO7408122F1204159ZE184226B<<<<<10
```

Line 1 carries the document type (`P` for passport), the three letter issuing state, then the surname and given names separated by `<<`, padded with `<` to fill exactly 44 characters.

Line 2 packs everything else into fixed positions: the document number (`L898902C3`) and its check digit, the nationality (`UTO`), the date of birth in `YYMMDD` order (`740812`, or 1974-08-12) plus its check digit, sex (`F`), the expiry date plus its check digit, an optional personal number field, and one final composite check digit computed over the document number, birth date, expiry date, and personal number together.

## How the check digit algorithm actually works

Every numeric field in the MRZ carries its own check digit, calculated with what ICAO calls the 7-3-1 weighting. The rule is short enough to run by hand:

1. Convert every character to a value: digits keep their own value, `A` through `Z` map to 10 through 35, and the filler `<` maps to 0.
2. Multiply each character's value by a repeating weight of 7, 3, 1, 7, 3, 1, and so on across the field.
3. Sum the results and take the remainder after dividing by 10. That remainder is the check digit.

Run it on the document number `L898902C3` from the example above: `L` is 21, so `21x7 + 8x3 + 9x1 + 8x7 + 9x3 + 0x1 + 2x7 + C(12)x3 + 3x1` sums to 316, and 316 mod 10 is 6, which is exactly the check digit printed right after the field. [mrz_toolkit.py](mrz_toolkit.py) runs that same arithmetic in code, for every numeric field, plus the composite digit that ties the four fields together.

This is also why a single edited character is so easy to catch. Change one digit of the date of birth without recalculating its check digit, and the field check fails immediately. Change it and get the new check digit right, and the composite check digit at the end of the line still fails, because it was computed from the original value. A forger has to get every dependent digit right at once, by hand, which is a lot harder than editing one printed number.

That said, a check digit is an integrity check, not a security feature. It tells a reader the field was transcribed and typed correctly. It says nothing about whether the document itself is genuine, which is why real identity verification pairs MRZ parsing with physical document inspection and, on chip enabled documents, a cryptographic check the MRZ cannot perform on its own.

## The MRZ is also the key to the chip

Modern passports carry an RFID chip alongside the printed page, and the two are connected in a way the MRZ full form definition alone does not suggest. Before a reader can access the chip's contents, it has to prove it already read the printed page. Under Basic Access Control, an NFC reader derives an access key from the document number, date of birth, and expiry date, each combined with its own check digit, and the chip only starts talking once that derived key matches. In practice, this means a device has to physically scan or already possess a valid MRZ before the chip will hand over anything, which is a deliberate design choice to stop the chip from being read by anyone who merely walks past the document.

## Try it yourself: a check digit validator with no dependencies

[mrz_toolkit.py](mrz_toolkit.py) reads raw MRZ lines from a file or stdin, detects whether they are TD1, TD2, or TD3 by line count and width, and reports whether every check digit matches what it recomputes.

```bash
python3 mrz_toolkit.py examples/passport_td3.txt
```

```
Format: TD3  Issuing state: UTO  Document type: P
Name: ERIKSSON / ANNA MARIA
Document number: L898902C3   Nationality: UTO   Sex: F
Date of birth: 1974-08-12   Date of expiry: 2012-04-15

  [OK] document number: printed 6, expected 6
  [OK] date of birth: printed 2, expected 2
  [OK] date of expiry: printed 9, expected 9
  [OK] personal number: printed 1, expected 1
  [OK] composite: printed 0, expected 0
```

Run it against [examples/passport_td3_tampered.txt](examples/passport_td3_tampered.txt), where a single digit of the birth date was edited without touching the check digits, and both the affected field and the composite fail while everything else still passes:

```bash
python3 mrz_toolkit.py examples/passport_td3_tampered.txt; echo "exit code: $?"
```

```
  [OK] document number: printed 6, expected 6
  [MISMATCH] date of birth: printed 2, expected 3
  [OK] date of expiry: printed 9, expected 9
  [OK] personal number: printed 1, expected 1
  [MISMATCH] composite: printed 0, expected 7
exit code: 1
```

The nonzero exit code is intentional. A document pipeline can call this script against extracted MRZ text and treat a failed check digit as a reason to route the session to manual review instead of approving it automatically. `--json` prints the same result as structured data for a pipeline that would rather parse JSON than screen scrape stdout. [examples/id_card_td1.txt](examples/id_card_td1.txt) and [examples/id_card_td2.txt](examples/id_card_td2.txt) cover the other two formats.

## Where MRZ reading fits in identity verification

MRZ scanning shows up anywhere a business needs to confirm who is holding a document, quickly and without a human retyping every field by hand.

**Onboarding and KYC.** Fintechs, exchanges, and other regulated platforms scan the MRZ as part of document based identity verification during account opening, then cross check the extracted fields against what the applicant typed. A mismatch between the two is a flag, not necessarily a rejection.

**Borders and travel.** Automated passport gates read the MRZ (and then the chip, once the MRZ derived key unlocks it) to process travelers faster than a manual check.

**Hospitality, telecom, and age gated access.** Hotel check in, SIM card registration, and age restricted purchases increasingly lean on the same MRZ extraction to skip manual data entry and confirm the traveler, subscriber, or customer is who the document says.

As of this writing, iDenfy's own document verification covers 3,000+ active documents from 190+ countries, per its [supported documents page](https://idenfy.com/supported-documents/), and pairs MRZ extraction with the physical and biometric checks a check digit alone cannot provide. iDenfy itself is a verification layer a regulated business builds a compliance program on top of, not a substitute for that business's own AML or KYC obligations.

## Known limits of MRZ reading

A few edge cases are worth knowing before a team leans on MRZ extraction as its only input.

- **OCR still misreads glare, creases, and worn print.** The check digit catches most transcription errors, but a reader should treat a failed check digit as a signal to re scan or fall back to visual inspection, not as automatic proof of fraud.
- **Names get transliterated.** ICAO Doc 9303 defines transliteration tables for non Latin scripts, so the MRZ spelling of a name can legitimately differ from the diacritic bearing spelling printed above it, for example a German umlaut expanding to an extra letter.
- **The zone is plain text.** Because MRZ data carries no encryption, a document handling pipeline should avoid logging the raw MRZ, or at minimum mask the personal number field, past the point where it is actually needed for the check.

## FAQ

### What does MRZ stand for?

MRZ stands for Machine Readable Zone, the printed strip of OCR text on a passport, ID card, or residence permit that encodes the holder's key details in a fixed, scannable format.

### What is MRZ on a passport, exactly?

On a passport, the MRZ is the two 44 character lines at the bottom of the photo page, following the TD3 format. It repeats the document number, name, nationality, date of birth, sex, and expiry date already printed on the page, but in a layout a scanner can read reliably.

### Is the MRZ encrypted?

No. The MRZ encodes data in a standardized format so machines can read it, but it applies no encryption. Anyone able to read the printed characters, by eye or by scanner, can read the data.

### How is the MRZ different from the passport's chip?

The MRZ is printed text with no active security features of its own. The chip stores the same data plus a biometric photo, protected by cryptography, and Basic Access Control means the chip will not respond until a reader derives the correct key from the MRZ first. The MRZ is the key. The chip is the vault.

### Does a valid check digit prove a document is not forged?

No. A check digit confirms a field was transcribed correctly, not that the document is genuine. Real fraud detection pairs MRZ validation with physical document inspection and, where available, the chip's own cryptographic checks.

### Can a smartphone camera read an MRZ?

Yes. Modern OCR models trained on the OCR B font can extract MRZ text from a phone camera image, which is how most mobile identity verification flows capture a document without dedicated scanner hardware.

## Contributing and credits

To correct a field layout, add a format, or fix a bug in the check digit math, open a pull request. Please cite [ICAO Doc 9303](https://www.icao.int/publications/doc-series/doc-9303) for any layout claim rather than a secondary summary. Run the following before submitting:

```bash
python3 -m py_compile mrz_toolkit.py
python3 mrz_toolkit.py examples/passport_td3.txt
python3 mrz_toolkit.py examples/id_card_td1.txt
python3 mrz_toolkit.py examples/id_card_td2.txt
python3 mrz_toolkit.py examples/passport_td3_tampered.txt; test $? -eq 1
```

The explanation of the machine readable zone here is adapted from iDenfy's own [machine readable zone explainer](https://idenfy.com/blog/machine-readable-zone/), and iDenfy is the publisher of that source. The check digit walkthrough, the Basic Access Control section, and [mrz_toolkit.py](mrz_toolkit.py) itself are independent work verified directly against ICAO Doc 9303 and are not legal or compliance advice.

## License

MIT. See [LICENSE](LICENSE).
