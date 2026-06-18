from django.db import models
from django.conf import settings


class Category(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    monthly_limit = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name_plural = "categories"
        unique_together = ("user", "name")

    def __str__(self):
        return self.name


class Expense(models.Model):
    CURRENCY_CHOICES = [
        ("USD", "US Dollar"),
        ("EUR", "Euro"),
        ("GBP", "British Pound"),
        ("JPY", "Japanese Yen"),
        ("INR", "Indian Rupee"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses"
    )
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(
        max_length=3, choices=CURRENCY_CHOICES, default="USD")
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="expenses"
    )
    date = models.DateField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} ({self.amount})"


class Budget_Alert(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budget_alerts"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="budget_alerts"
    )
    year = models.IntegerField()
    month = models.IntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "category", "year", "month")

    def __str__(self):
        return f"{self.user.username} - {self.category.name}"
