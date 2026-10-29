"""Attach passed task receipts to exact record bodies, without inheriting edits."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from maintenance import source_fingerprint

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", nargs="?")
    parser.add_argument(
        "--upgrade-existing",
        action="store_true",
        help="Bind receipts to original immutable source references.",
    )
    parser.add_argument(
        "--only-stale",
        action="store_true",
        help="Keep valid existing receipts; accept only missing/body/source-stale records.",
    )
    args = parser.parse_args()
    if args.upgrade_existing:
        path = ROOT / "knowledge/validation-receipts.json"
        receipts = json.loads(path.read_text(encoding="utf-8"))
        cached = {}
        for rid, receipt in receipts["records"].items():
            build_id = receipt["validated_build_id"]
            if build_id not in cached:
                build = ROOT / "knowledge/builds" / build_id
                manifest = json.loads(
                    (build / "manifest.json").read_text(encoding="utf-8")
                )
                if sha(build / "records.json") != manifest["files"]["records.json"]:
                    raise ValueError("Original validated snapshot changed")
                cached[build_id] = json.loads(
                    (build / "records.json").read_text(encoding="utf-8")
                )
            original = cached[build_id][rid]
            if (
                hashlib.sha256(original["body"].encode()).hexdigest()
                != receipt["body_sha256"]
            ):
                raise ValueError("Original body does not match receipt")
            receipt["source_refs_sha256"] = source_fingerprint(original["source_refs"])
        path.write_text(
            json.dumps(receipts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({"upgraded_receipts": len(receipts["records"])}))
        return
    if not args.report:
        parser.error("report is required unless --upgrade-existing")
    report_path = (ROOT / args.report).resolve()
    if not report_path.is_relative_to(ROOT):
        raise ValueError("Report outside workspace")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (
        report["status"] != "passed"
        or report["failed"]
        or not report.get("validated_records")
    ):
        raise ValueError("Only passed record-specific evidence can be accepted")
    build = ROOT / "knowledge/builds" / report["build_id"]
    records = json.loads((build / "records.json").read_text(encoding="utf-8"))
    for item in report["validated_records"]:
        if (
            hashlib.sha256(records[item["id"]]["body"].encode()).hexdigest()
            != item["body_sha256"]
        ):
            raise ValueError("Receipt does not match validated source body")
    receipts_path = ROOT / "knowledge/validation-receipts.json"
    receipts = (
        json.loads(receipts_path.read_text(encoding="utf-8"))
        if receipts_path.exists()
        else {"version": "1.7.0", "records": {}}
    )
    if args.only_stale:
        report["validated_records"] = [
            item
            for item in report["validated_records"]
            if (old := receipts["records"].get(item["id"], {})).get("body_sha256")
            != item["body_sha256"]
            or old.get("source_refs_sha256")
            != source_fingerprint(records[item["id"]]["source_refs"])
        ]
        if not report["validated_records"]:
            print(
                json.dumps(
                    {
                        "accepted_records": 0,
                        "reason": "existing body/source receipts remain valid",
                    }
                )
            )
            return
    directory = ROOT / "evaluations/history" / report["build_id"]
    directory.mkdir(parents=True, exist_ok=True)
    saved = directory / report_path.name
    if saved.exists() and sha(saved) != sha(report_path):
        raise ValueError(
            "Historical report exists with different content; retain immutable history"
        )
    if not saved.exists():
        shutil.copyfile(report_path, saved)
    receipts_path = ROOT / "knowledge/validation-receipts.json"
    receipts = (
        json.loads(receipts_path.read_text(encoding="utf-8"))
        if receipts_path.exists()
        else {"version": "1.7.0", "records": {}}
    )
    for item in report["validated_records"]:
        receipts["records"][item["id"]] = {
            **item,
            "validated_build_id": report["build_id"],
            "report": saved.relative_to(ROOT).as_posix(),
            "report_sha256": sha(saved),
            "source_refs_sha256": source_fingerprint(
                records[item["id"]]["source_refs"]
            ),
        }
    receipts_path.write_text(
        json.dumps(receipts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "accepted_records": len(report["validated_records"]),
                "validated_build_id": report["build_id"],
            }
        )
    )


if __name__ == "__main__":
    main()
