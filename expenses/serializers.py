from rest_framework import serializers

from .models import Category, Expense


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")

        if request := self.context.get("request"):
            user = request.user
            if Category.objects.filter(user=user, name=value).exists():
                raise serializers.ValidationError(
                    "You already have a category with this name.")

        return value


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ["id", "title", "amount", "category", "date", "notes"]
        read_only_fields = ["id"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero.")
        return value

    def validate_category(self, value):
        request = self.context.get("request")

        if request and value.user != request.user:
            raise serializers.ValidationError(
                "You can only use your own categories.")

        return value
