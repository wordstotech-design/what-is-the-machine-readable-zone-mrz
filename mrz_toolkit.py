#!/usr/bin/env python3
"""Parse and validate a Machine Readable Zone against ICAO Doc 9303.

Standard library only, Python 3.8+. Supports TD1 (3 lines x 30, ID cards),
TD2 (2 lines x 36, less common ID card format), and TD3 (2 lines x 44,
passports). Detects the format from line count and width, then recomputes
every ICAO 7-3-1 check digit instead of trusting the ones printed in the
zone.

Usage:
    python3 mrz_toolkit.py examples/passport_td3.txt
    python3 mrz_toolkit.py examples/id_card_td1.txt --json
    echo "..." | python3 mrz_toolkit.py -
"""
import argparse
import json
import sys
from datetime import date

WEIGHTS = (7, 3, 1)


def char_value(ch):
    if ch == "<":
        return 0
    if ch.isdigit():
        return int(ch)
    if ch.isalpha():
        return ord(ch.upper()) - ord("A") + 10
    raise ValueError(f"character not valid in an MRZ field: {ch!r}")


def check_digit(field):
    total = sum(char_value(ch) * WEIGHTS[i % 3] for i, ch in enumerate(field))
    return str(total % 10)


def field_check(field, digit_char, label):
    expected = check_digit(field)
    return {
        "label": label,
        "value": field,
        "printed_digit": digit_char,
        "expected_digit": expected,
        "valid": digit_char == expected,
    }


def yymmdd_to_iso(raw, assume_cutoff=50):
    if len(raw) != 6 or not raw.isdigit():
        return None
    yy, mm, dd = int(raw[0:2]), int(raw[2:4]), int(raw[4:6])
    century = 1900 if yy > assume_cutoff else 2000
    try:
        return date(century + yy, mm, dd).isoformat()
    except ValueError:
        return None


def names_from_field(name_field):
    primary, _, rest = name_field.partition("<<")
    given = rest.replace("<<", " ").replace("<", " ").strip()
    surname = primary.replace("<", " ").strip()
    return surname, given


def parse_td3(line1, line2):
    if len(line1) != 44 or len(line2) != 44:
        raise ValueError("TD3 needs two 44 character lines")
    doc_type = line1[0:2].rstrip("<")
    issuing_state = line1[2:5]
    surname, given_names = names_from_field(line1[5:44])

    doc_number, doc_cd = line2[0:9], line2[9]
    nationality = line2[10:13]
    birth_date, birth_cd = line2[13:19], line2[19]
    sex = line2[20]
    expiry_date, expiry_cd = line2[21:27], line2[27]
    personal_number, personal_cd = line2[28:42], line2[42]
    composite_cd = line2[43]
    composite_input = (
        doc_number + doc_cd + birth_date + birth_cd + expiry_date + expiry_cd + personal_number + personal_cd
    )

    checks = [
        field_check(doc_number, doc_cd, "document number"),
        field_check(birth_date, birth_cd, "date of birth"),
        field_check(expiry_date, expiry_cd, "date of expiry"),
        field_check(personal_number, personal_cd, "personal number"),
        field_check(composite_input, composite_cd, "composite"),
    ]
    return {
        "format": "TD3",
        "document_type": doc_type,
        "issuing_state": issuing_state,
        "surname": surname,
        "given_names": given_names,
        "document_number": doc_number.rstrip("<"),
        "nationality": nationality,
        "date_of_birth": yymmdd_to_iso(birth_date),
        "sex": sex,
        "date_of_expiry": yymmdd_to_iso(expiry_date),
        "personal_number": personal_number.rstrip("<") or None,
        "checks": checks,
    }


def parse_td2(line1, line2):
    if len(line1) != 36 or len(line2) != 36:
        raise ValueError("TD2 needs two 36 character lines")
    doc_type = line1[0:2].rstrip("<")
    issuing_state = line1[2:5]
    surname, given_names = names_from_field(line1[5:36])

    doc_number, doc_cd = line2[0:9], line2[9]
    nationality = line2[10:13]
    birth_date, birth_cd = line2[13:19], line2[19]
    sex = line2[20]
    expiry_date, expiry_cd = line2[21:27], line2[27]
    optional_data = line2[28:35]
    composite_cd = line2[35]
    composite_input = doc_number + doc_cd + birth_date + birth_cd + expiry_date + expiry_cd + optional_data

    checks = [
        field_check(doc_number, doc_cd, "document number"),
        field_check(birth_date, birth_cd, "date of birth"),
        field_check(expiry_date, expiry_cd, "date of expiry"),
        field_check(composite_input, composite_cd, "composite"),
    ]
    return {
        "format": "TD2",
        "document_type": doc_type,
        "issuing_state": issuing_state,
        "surname": surname,
        "given_names": given_names,
        "document_number": doc_number.rstrip("<"),
        "nationality": nationality,
        "date_of_birth": yymmdd_to_iso(birth_date),
        "sex": sex,
        "date_of_expiry": yymmdd_to_iso(expiry_date),
        "checks": checks,
    }


def parse_td1(line1, line2, line3):
    if len(line1) != 30 or len(line2) != 30 or len(line3) != 30:
        raise ValueError("TD1 needs three 30 character lines")
    doc_type = line1[0:2].rstrip("<")
    issuing_state = line1[2:5]
    doc_number, doc_cd = line1[5:14], line1[14]
    optional_data_1 = line1[15:30]

    birth_date, birth_cd = line2[0:6], line2[6]
    sex = line2[7]
    expiry_date, expiry_cd = line2[8:14], line2[14]
    nationality = line2[15:18]
    optional_data_2 = line2[18:29]
    composite_cd = line2[29]
    composite_input = (
        doc_number + doc_cd + optional_data_1 + birth_date + birth_cd + expiry_date + expiry_cd + optional_data_2
    )

    surname, given_names = names_from_field(line3)

    checks = [
        field_check(doc_number, doc_cd, "document number"),
        field_check(birth_date, birth_cd, "date of birth"),
        field_check(expiry_date, expiry_cd, "date of expiry"),
        field_check(composite_input, composite_cd, "composite"),
    ]
    return {
        "format": "TD1",
        "document_type": doc_type,
        "issuing_state": issuing_state,
        "surname": surname,
        "given_names": given_names,
        "document_number": doc_number.rstrip("<"),
        "nationality": nationality,
        "date_of_birth": yymmdd_to_iso(birth_date),
        "sex": sex,
        "date_of_expiry": yymmdd_to_iso(expiry_date),
        "checks": checks,
    }


def detect_and_parse(lines):
    lines = [ln for ln in (ln.rstrip("\n\r") for ln in lines) if ln.strip()]
    widths = {len(ln) for ln in lines}
    if len(lines) == 3 and widths == {30}:
        return parse_td1(*lines)
    if len(lines) == 2 and widths == {36}:
        return parse_td2(*lines)
    if len(lines) == 2 and widths == {44}:
        return parse_td3(*lines)
    raise ValueError(
        f"got {len(lines)} line(s) with width(s) {sorted(widths)}. "
        "Expected 3x30 (TD1), 2x36 (TD2), or 2x44 (TD3)."
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", help="path to a file with the raw MRZ lines, or - for stdin")
    parser.add_argument("--json", action="store_true", help="print machine readable JSON instead of a report")
    args = parser.parse_args(argv)

    raw = sys.stdin.read() if args.source == "-" else open(args.source, encoding="ascii").read()
    result = detect_and_parse(raw.splitlines())

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"Format: {result['format']}  Issuing state: {result['issuing_state']}  "
            f"Document type: {result['document_type']}"
        )
        print(f"Name: {result['surname']} / {result['given_names']}")
        print(
            f"Document number: {result['document_number']}   Nationality: {result['nationality']}   "
            f"Sex: {result['sex']}"
        )
        print(f"Date of birth: {result['date_of_birth']}   Date of expiry: {result['date_of_expiry']}")
        print()
        for check in result["checks"]:
            status = "OK" if check["valid"] else "MISMATCH"
            print(f"  [{status}] {check['label']}: printed {check['printed_digit']}, expected {check['expected_digit']}")

    return 0 if all(c["valid"] for c in result["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
