from app.services.ocr_eval import evaluate_ocr_prediction, make_noisy_prediction


def test_ocr_eval_scores_perfect_prediction() -> None:
    ground_truth = {
        "invoice_number": "INV-1001",
        "invoice_date": "2026-01-15",
        "currency": "INR",
        "place_of_supply": "Karnataka",
        "seller": {
            "name": "Astra Analytics Pvt Ltd",
            "gstin": "29AABCU9603R1ZM",
            "address": {
                "line1": "12 MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "state_code": "29",
                "postal_code": "560001",
            },
        },
        "buyer": {
            "name": "Indigo Labs LLP",
            "gstin": "27AABCU9603R1ZN",
            "address": {
                "line1": "88 FC Road",
                "city": "Pune",
                "state": "Maharashtra",
                "state_code": "27",
                "postal_code": "411004",
            },
        },
        "items": [
            {
                "description": "GPU hours",
                "hsn_sac": "998314",
                "quantity": "2.00",
                "unit_price": "1000.00",
                "gst_rate": "18.00",
                "line_subtotal": "2000.00",
                "tax_amount": "360.00",
                "line_total": "2360.00",
            }
        ],
        "subtotal": "2000.00",
        "cgst": "0.00",
        "sgst": "0.00",
        "igst": "360.00",
        "grand_total": "2360.00",
    }
    report = evaluate_ocr_prediction(ground_truth=ground_truth, prediction=ground_truth, model_name="perfect")
    assert report["accuracy"] == 100.0
    assert report["correct_fields"] == report["total_fields"]
    assert report["incorrect_fields"] == []


def test_ocr_eval_detects_field_errors() -> None:
    ground_truth = {
        "invoice_number": "INV-1001",
        "invoice_date": "2026-01-15",
        "currency": "INR",
        "place_of_supply": "Karnataka",
        "seller": {
            "name": "Astra Analytics Pvt Ltd",
            "gstin": "29AABCU9603R1ZM",
            "address": {
                "line1": "12 MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "state_code": "29",
                "postal_code": "560001",
            },
        },
        "buyer": {
            "name": "Indigo Labs LLP",
            "gstin": "27AABCU9603R1ZN",
            "address": {
                "line1": "88 FC Road",
                "city": "Pune",
                "state": "Maharashtra",
                "state_code": "27",
                "postal_code": "411004",
            },
        },
        "items": [
            {
                "description": "GPU hours",
                "hsn_sac": "998314",
                "quantity": "2.00",
                "unit_price": "1000.00",
                "gst_rate": "18.00",
                "line_subtotal": "2000.00",
                "tax_amount": "360.00",
                "line_total": "2360.00",
            }
        ],
        "subtotal": "2000.00",
        "cgst": "0.00",
        "sgst": "0.00",
        "igst": "360.00",
        "grand_total": "2360.00",
    }
    noisy = make_noisy_prediction(ground_truth, noise_level=0.3)
    report = evaluate_ocr_prediction(ground_truth=ground_truth, prediction=noisy, model_name="noisy-demo")
    assert report["accuracy"] < 100.0
    assert report["incorrect_fields"]
    assert "identity" in report["groups"]
