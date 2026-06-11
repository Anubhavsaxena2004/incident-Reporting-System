from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import (
    UserRegisterSerializer,
    CustomTokenObtainPairSerializer,
    UserDetailSerializer
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    API endpoint that allows new users to register.
    """
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    API endpoint that takes user credentials and returns access, refresh tokens, and user details.
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint that retrieves or updates user details for the currently authenticated user.
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """
    API endpoint that logs out the user by blacklisting their refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Successfully logged out."}, 
                status=status.HTTP_205_RESET_CONTENT
            )
        except KeyError:
            return Response(
                {"detail": "Refresh token is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
