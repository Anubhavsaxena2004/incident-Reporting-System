from rest_framework import generics, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, inline_serializer

from .serializers import (
    UserRegisterSerializer,
    CustomTokenObtainPairSerializer,
    UserDetailSerializer
)

User = get_user_model()


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True, 
        help_text="The refresh token to blacklist (invalidates the session)."
    )


@extend_schema(
    summary="User Registration",
    description="Registers a new system user. By default, the registered user is assigned the 'Citizen' role.",
    responses={201: UserRegisterSerializer}
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth_register'


@extend_schema(
    summary="User Login (Obtain Tokens)",
    description="Authenticates username and password credentials. Returns a short-lived access JWT, a refresh JWT, and detailed user profile context."
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_scope = 'auth_login'


@extend_schema(
    summary="User Profile Details",
    description="Retrieves or updates profile details (email, names, phone number, role) for the currently authenticated user."
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    summary="User Logout",
    description="Logs out the user server-side by blacklisting the provided refresh token.",
    request=LogoutRequestSerializer,
    responses={
        205: inline_serializer(
            name='LogoutSuccessResponse',
            fields={'detail': serializers.CharField(default="Successfully logged out.")}
        ),
        400: inline_serializer(
            name='LogoutErrorResponse',
            fields={'detail': serializers.CharField()}
        )
    }
)
class LogoutView(APIView):
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
