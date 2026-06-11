from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Incident

User = get_user_model()


class IncidentSerializer(serializers.ModelSerializer):
    reporter = serializers.StringRelatedField(read_only=True)
    assigned_responder = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.OPERATOR),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Incident
        fields = (
            'id', 'title', 'description', 'location', 'status',
            'priority', 'reporter', 'assigned_responder', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'reporter', 'created_at', 'updated_at')

    def validate(self, attrs):
        # Retrieve user context from request
        request = self.context.get('request')
        if not request or not request.user:
            return attrs
            
        user = request.user
        
        # If updating an existing incident (Instance update checks)
        if self.instance:
            # Check if attempting to assign or reassign field responder
            if 'assigned_responder' in attrs and attrs['assigned_responder'] != self.instance.assigned_responder:
                if user.role not in [User.Role.ADMIN, User.Role.OPERATOR]:
                    raise serializers.ValidationError(
                        {"assigned_responder": "Only Admins or Operators can assign or change responders."}
                    )
            
            # Check if status transitions are valid for this role
            if 'status' in attrs and attrs['status'] != self.instance.status:
                if user.role not in [User.Role.ADMIN, User.Role.OPERATOR]:
                    # Citizens cannot transition status once response action has commenced (past DRAFT or REPORTED)
                    if user.role == User.Role.CITIZEN:
                        if self.instance.status not in [Incident.Status.DRAFT, Incident.Status.REPORTED]:
                            raise serializers.ValidationError(
                                {"status": "Citizens cannot transition status once response action has commenced."}
                            )
        return attrs
