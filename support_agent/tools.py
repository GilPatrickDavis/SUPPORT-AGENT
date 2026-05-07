MOCK_ACCOUNTS = {
    "CUST-001": {
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "plan": "Pro",
        "status": "active",
        "member_since": "2022-03-15",
        "billing_status": "current",
        "total_orders": 12,
        "lifetime_value": 3588.00,
    },
    "CUST-002": {
        "name": "Bob Smith",
        "email": "bob@example.com",
        "plan": "Basic",
        "status": "active",
        "member_since": "2023-11-01",
        "billing_status": "overdue",
        "total_orders": 3,
        "lifetime_value": 87.00,
    },
    "CUST-003": {
        "name": "Carol White",
        "email": "carol@example.com",
        "plan": "Enterprise",
        "status": "active",
        "member_since": "2021-06-10",
        "billing_status": "current",
        "total_orders": 48,
        "lifetime_value": 14400.00,
    },
}

MOCK_ORDERS = {
    "ORD-5523": {
        "status": "delivered",
        "item": "Pro Subscription - Annual",
        "amount": 299.00,
        "date": "2024-01-15",
        "tracking": "TRK123456",
        "delivered_on": "2024-01-17",
    },
    "ORD-8891": {
        "status": "refund_requested",
        "item": "Basic Plan - Monthly",
        "amount": 29.00,
        "date": "2024-01-28",
        "tracking": None,
        "refund_status": "pending_review",
    },
    "ORD-9912": {
        "status": "processing",
        "item": "Enterprise License - Annual",
        "amount": 2400.00,
        "date": "2024-02-01",
        "tracking": None,
    },
}

MOCK_KB_ARTICLES = [
    {
        "id": "KB-001",
        "title": "How to reset your password",
        "category": "account",
        "keywords": ["password", "reset", "forgot", "login", "access", "locked"],
        "content": (
            "To reset your password: 1) Go to the login page. "
            "2) Click 'Forgot Password'. "
            "3) Enter your email — a reset link arrives within 2 minutes. "
            "4) The link is valid for 24 hours. "
            "5) Create a new password with at least 8 characters."
        ),
        "resolution_time": "5 minutes",
    },
    {
        "id": "KB-002",
        "title": "Requesting a refund",
        "category": "billing",
        "keywords": ["refund", "charge", "payment", "money", "cancel", "billing", "charged"],
        "content": (
            "Refunds are processed within 5-7 business days. "
            "Annual plans are fully refundable within the first 30 days. "
            "To request: provide your order number and reason. "
            "The refund returns to your original payment method. "
            "Partial refunds are available for annual plans after 30 days (prorated)."
        ),
        "resolution_time": "5-7 business days",
    },
    {
        "id": "KB-003",
        "title": "Account security and suspicious activity",
        "category": "account",
        "keywords": ["hacked", "compromised", "suspicious", "unauthorized", "security", "breach", "stolen"],
        "content": (
            "If you suspect unauthorized access: "
            "1) Change your password immediately. "
            "2) Enable two-factor authentication (2FA). "
            "3) Review recent login activity in Account > Security. "
            "4) Contact support — we lock compromised accounts within 15 minutes. "
            "Enterprise customers: call the priority line for immediate response."
        ),
        "resolution_time": "15 minutes (critical priority)",
    },
    {
        "id": "KB-004",
        "title": "Technical troubleshooting — service not working",
        "category": "technical",
        "keywords": ["not working", "broken", "error", "bug", "crash", "slow", "down", "issue", "problem"],
        "content": (
            "For technical issues: "
            "1) Clear browser cache and cookies. "
            "2) Try an incognito window or different browser. "
            "3) Check status.example.com for ongoing incidents. "
            "4) If the issue persists, share: your browser, OS, and any error messages. "
            "Most issues resolve within 24-48 hours."
        ),
        "resolution_time": "24-48 hours",
    },
    {
        "id": "KB-005",
        "title": "Upgrading or changing your plan",
        "category": "billing",
        "keywords": ["upgrade", "downgrade", "plan", "change", "switch", "tier", "subscription"],
        "content": (
            "You can upgrade at any time from Account Settings > Subscription. "
            "Upgrades: immediate effect with prorated billing for the remaining cycle. "
            "Downgrades: take effect at the start of your next billing cycle. "
            "Enterprise plans require contacting sales for custom pricing."
        ),
        "resolution_time": "Immediate",
    },
]


def get_account_info(customer_id: str) -> dict:
    account = MOCK_ACCOUNTS.get(customer_id)
    if not account:
        return {"error": f"No account found for customer_id: {customer_id}"}
    return account


def get_order_info(order_id: str) -> dict:
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return {"error": f"No order found for order_id: {order_id}"}
    return order


def search_knowledge_base(category: str, keywords: list[str]) -> list[dict]:
    keywords_lower = {k.lower() for k in keywords}
    scored = []

    for article in MOCK_KB_ARTICLES:
        article_keywords = {k.lower() for k in article["keywords"]}
        keyword_overlap = len(keywords_lower & article_keywords)
        category_match = article["category"] == category

        if category_match or keyword_overlap > 0:
            score = keyword_overlap + (2 if category_match else 0)
            scored.append({**article, "_relevance_score": score})

    scored.sort(key=lambda x: x["_relevance_score"], reverse=True)
    return scored[:3]


def update_crm(ticket_id: str, status: str, resolution_notes: str, category: str) -> dict:
    print(f"\n  [CRM] Ticket {ticket_id} → {status}  (category: {category})")
    print(f"  [CRM] Notes: {resolution_notes[:100]}...")
    return {"success": True, "ticket_id": ticket_id, "new_status": status}


def send_customer_email(to_email: str, subject: str, body: str) -> dict:
    print(f"\n  [EMAIL] To: {to_email}")
    print(f"  [EMAIL] Subject: {subject}")
    print(f"  [EMAIL] Preview: {body[:150]}...")
    return {
        "success": True,
        "to": to_email,
        "message_id": f"MSG-{abs(hash(subject)) % 99999:05d}",
    }


def create_escalation_ticket(
    ticket_id: str, customer_id: str, reason: str, urgency: str
) -> dict:
    queue = "tier-2-urgent" if urgency in ("high", "critical") else "tier-1-support"
    print(f"\n  [ESCALATION] Ticket {ticket_id} → queue: {queue}")
    print(f"  [ESCALATION] Customer: {customer_id}  |  Urgency: {urgency}")
    print(f"  [ESCALATION] Reason: {reason[:100]}")
    return {
        "success": True,
        "escalation_id": f"ESC-{abs(hash(ticket_id)) % 9999:04d}",
        "assigned_queue": queue,
    }
