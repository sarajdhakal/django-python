import os
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.db.models import Sum


def get_exchange_rate(from_currency, to_currency):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return Decimal("1.00")

    api_url = os.getenv("EXCHANGE_RATE_API_URL",
                        "https://api.exchangerate.host")
    url = f"{api_url}/{from_currency}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    data = response.json()
    rates = data.get("rates", {})

    if to_currency not in rates:
        raise ValueError(f"Rate is not available for {to_currency}")

    return Decimal(str(rates[to_currency]))


def convert_amount(amount, from_currency, to_currency):
    rate = get_exchange_rate(from_currency, to_currency)
    converted = Decimal(amount) * rate

    return {
        "amount": converted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "rate": rate.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
    }


def get_month_total_for_category(category, year, month):
    from .models import Expense

    total = (
        Expense.objects.filter(
            user=category.user,
            category=category,
            date__year=year,
            date__month=month,
        )
        .aggregate(total=Sum("amount"))
        .get("total")
    )

    return total or Decimal("0.00")


def send_budget_alert(message):
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("BOT_CHAT_ID")

    if not bot_token or not chat_id:
        print("Budget alert skipped: BOT_TOKEN or BOT_CHAT_ID missing.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        return True

    except requests.exceptions.RequestException as error:
        print(f"Budget alert failed: {error}")
        return False
