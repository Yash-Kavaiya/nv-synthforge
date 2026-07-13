from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.domain.support import ConversationTurn, SupportConversation


_SCENARIOS = {
    "telecom": {
        "issue": "unexpected mobile-data charge",
        "channel": "chat",
        "turns": [
            "My bill includes a mobile-data charge I do not recognise.",
            "I can review the usage ledger and explain each charge.",
            "Please check it; the amount is higher than my usual bill.",
            "The charge came from roaming data, but an alert was not delivered.",
            "I was not informed, so I would like this corrected.",
            "I have applied a courtesy credit and enabled roaming alerts for your account.",
            "Will the correction be visible on my current statement?",
            "Yes. The credit is posted and the revised balance is available now.",
            "Please confirm that future roaming sessions will trigger an alert.",
            "Roaming alerts are active, and I sent the case summary to your registered contact.",
        ],
        "resolution": "I applied the courtesy credit, enabled roaming alerts, and sent the corrected balance confirmation.",
        "escalation": "I could not authorise the adjustment, so I escalated the case to the billing resolution team.",
    },
    "ecommerce": {
        "issue": "delayed order delivery",
        "channel": "chat",
        "turns": [
            "My order is late and the tracking page has not changed.",
            "I will check the courier scan and delivery commitment.",
            "I need the item before the weekend.",
            "The parcel missed a transfer scan and is now at the local hub.",
            "Can you make sure it arrives on time?",
            "I upgraded delivery at no cost and sent the confirmed delivery window.",
            "Can I receive the new tracking event by message?",
            "Yes. Tracking notifications are active for every remaining courier scan.",
            "Please confirm there is nothing else I need to do.",
            "No further action is needed; the delivery upgrade and notification preferences are confirmed.",
        ],
        "resolution": "I upgraded delivery at no cost and sent the confirmed delivery window and tracking alerts.",
        "escalation": "The courier could not confirm a delivery window, so I escalated the order to our logistics desk.",
    },
    "banking": {
        "issue": "duplicate card transaction",
        "channel": "voice-transcript",
        "turns": [
            "The same card payment appears twice in my account.",
            "I can verify whether one entry is an unsettled authorisation.",
            "Both entries are reducing my available balance.",
            "One is a temporary authorisation and will expire automatically.",
            "Please confirm when the balance will be restored.",
            "I documented the case and confirmed restoration within two business days.",
            "Will I receive a reference number for this review?",
            "Yes. I sent the case reference and the authorisation expiry details securely.",
            "Please make sure the temporary entry is monitored.",
            "Monitoring is active, and we will notify you when the available balance is restored.",
        ],
        "resolution": "I confirmed the temporary authorisation, activated monitoring, and sent the restoration timeline.",
        "escalation": "The duplicate entries require a specialist review, so I escalated the case to card operations.",
    },
    "saas": {
        "issue": "workspace access failure",
        "channel": "email",
        "turns": [
            "Our team cannot sign in after the identity-provider update.",
            "I will inspect the workspace SSO configuration and recent audit events.",
            "This is blocking our support shift.",
            "The signing certificate is expired; I have prepared a replacement.",
            "Can you restore access without changing user accounts?",
            "The certificate was rotated and all existing accounts can sign in again.",
            "Can you verify that the overnight support group is included?",
            "I verified the group mapping and completed a successful sign-in check.",
            "Please send the audit details for our change record.",
            "The access test and certificate-rotation summary are attached to the workspace case.",
        ],
        "resolution": "I rotated the certificate, verified group mapping, and confirmed that existing accounts can sign in.",
        "escalation": "The identity provider rejected the replacement certificate, so I escalated the outage to the SSO team.",
    },
}

_LOCALIZED_PREFIX = {
    "en-IN": "",
    "hi-IN": "[हिन्दी सहायता] ",
    "gu-IN": "[ગુજરાતી સહાય] ",
}

_SENTIMENTS = {
    "recovery": [-0.8, -0.1, -0.4, 0.6, -0.2, 0.7, 0.1, 0.8, 0.3, 0.9],
    "steady-positive": [0.1, 0.5, 0.2, 0.6, 0.3, 0.7, 0.4, 0.8, 0.5, 0.9],
    "escalation": [-0.3, -0.5, -0.6, -0.65, -0.7, -0.75, -0.8, -0.85, -0.9, -0.95],
}


class OfflineSupportGenerator:
    def generate(
        self,
        count: int,
        seed: int,
        language: str = "en-IN",
        industry: str = "mixed",
        sentiment_arc: str = "recovery",
        max_turns: int = 6,
    ) -> list[SupportConversation]:
        if not 1 <= count <= 10_000:
            raise ValueError("count must be between 1 and 10000")
        if industry not in {*_SCENARIOS, "mixed"}:
            raise ValueError("unsupported support industry")
        if sentiment_arc not in _SENTIMENTS:
            raise ValueError("unsupported sentiment arc")
        if not 4 <= max_turns <= 10:
            raise ValueError("max_turns must be between 4 and 10")

        rng = random.Random(seed)
        industries = list(_SCENARIOS) if industry == "mixed" else [industry]
        turn_count = max_turns if max_turns % 2 == 0 else max_turns - 1
        prefix = _LOCALIZED_PREFIX.get(language, "")
        results: list[SupportConversation] = []

        for index in range(1, count + 1):
            selected_industry = rng.choice(industries)
            scenario = _SCENARIOS[selected_industry]
            started_at = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(
                days=rng.randrange(365), minutes=rng.randrange(1440)
            )
            texts = list(scenario["turns"][:turn_count])
            texts[-1] = scenario["escalation" if sentiment_arc == "escalation" else "resolution"]
            sentiments = _SENTIMENTS[sentiment_arc][:turn_count]
            turns = [
                ConversationTurn(
                    turn_id=turn_index,
                    role="customer" if turn_index % 2 else "agent",
                    timestamp=started_at + timedelta(minutes=(turn_index - 1) * 3),
                    text=f"{prefix}{message}" if turn_index == 1 and prefix else message,
                    sentiment=sentiments[turn_index - 1],
                )
                for turn_index, message in enumerate(texts, start=1)
            ]
            results.append(
                SupportConversation(
                    conversation_id=f"SUP-{seed:06d}-{index:04d}",
                    customer_id=f"SYN-CUST-{(seed * 97 + index) % 900000 + 100000}",
                    started_at=started_at,
                    language=language,
                    industry=selected_industry,
                    channel=scenario["channel"],
                    issue_type=scenario["issue"],
                    sentiment_arc=sentiment_arc,
                    resolution_status="escalated" if sentiment_arc == "escalation" else "resolved",
                    turns=turns,
                )
            )
        return results
