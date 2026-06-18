import os
from decimal import Decimal, ROUND_HALF_UP

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Category, Expense, Budget_Alert
from .serializers import CategorySerializer, ExpenseSerializer
from .services import convert_amount, get_month_total_for_category, send_budget_alert


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def category_list(request):
    if request.method == "GET":
        categories = Category.objects.filter(user=request.user)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    serializer = CategorySerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save(user=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def expense_list(request):
    if request.method == "GET":
        expenses = Expense.objects.filter(user=request.user)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            expenses = expenses.filter(date__gte=start_date)

        if end_date:
            expenses = expenses.filter(date__lte=end_date)

        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data)

    serializer = ExpenseSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    expense = serializer.save(user=request.user)

    check_budget_alert(expense)

    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def expense_detail(request, pk):
    try:
        expense = Expense.objects.get(pk=pk, user=request.user)
    except Expense.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ExpenseSerializer(expense)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = ExpenseSerializer(
            expense,
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        expense = serializer.save(user=request.user)

        check_budget_alert(expense)

        return Response(serializer.data)

    expense.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def expense_summary(request):
    base_currency = os.getenv("BASE_CURRENCY", "USD").upper()
    expenses = Expense.objects.filter(
        user=request.user).select_related("category")

    summary = {}

    for expense in expenses:
        category_name = expense.category.name

        converted = convert_amount(
            expense.amount,
            expense.currency,
            base_currency,
        )

        if category_name not in summary:
            summary[category_name] = {
                "category": category_name,
                "total": Decimal("0.00"),
                "rates": {},
            }

        summary[category_name]["total"] += converted["amount"]
        summary[category_name]["rates"][expense.currency] = str(
            converted["rate"])

    categories = []

    for item in summary.values():
        categories.append(
            {
                "category": item["category"],
                "total": str(
                    item["total"].quantize(
                        Decimal("0.01"),
                        rounding=ROUND_HALF_UP,
                    )
                ),
                "rates": item["rates"],
            }
        )

    return Response(
        {
            "base_currency": base_currency,
            "categories": categories,
        }
    )


def check_budget_alert(expense):
    category = expense.category

    if not category.monthly_limit:
        return

    year = expense.date.year
    month = expense.date.month

    already_sent = Budget_Alert.objects.filter(
        user=expense.user,
        category=category,
        year=year,
        month=month,
    ).exists()

    if already_sent:
        return

    month_total = get_month_total_for_category(category, year, month)

    if month_total <= category.monthly_limit:
        return

    base_currency = os.getenv("BASE_CURRENCY", "USD").upper()

    message = (
        f'⚠️ Budget alert: "{category.name}" is over its monthly limit.\n'
        f"Spent {month_total} / {category.monthly_limit} {base_currency} "
        f"for {expense.date.strftime('%B %Y')}."
    )

    send_budget_alert(message)

    Budget_Alert.objects.create(
        user=expense.user,
        category=category,
        year=year,
        month=month,
    )
