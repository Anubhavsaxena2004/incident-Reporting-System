from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'role', 'phone_number')

    def create(self, validated_data):
        # Create user through the user manager to ensure passwords are encrypted
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=validated_data.get('role', User.Role.REPORTER),
            phone_number=validated_data.get('phone_number', '')
        )
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'phone_number', 'is_staff', 'is_active', 'date_joined')
        read_only_fields = ('id', 'username', 'is_staff', 'is_active', 'date_joined')
