from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Incident

User = get_user_model()


class IncidentSerializer(serializers.ModelSerializer):
    reporter = serializers.StringRelatedField(read_only=True)
    assigned_responder = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.RESPONDER),
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
                if user.role not in [User.Role.ADMIN, User.Role.DISPATCHER]:
                    raise serializers.ValidationError(
                        {"assigned_responder": "Only Admins or Dispatchers can assign or change responders."}
                    )
            
            # Check if status transitions are valid for this role
            if 'status' in attrs and attrs['status'] != self.instance.status:
                if user.role not in [User.Role.ADMIN, User.Role.DISPATCHER]:
                    # Responders can set status to UNDER_INVESTIGATION, RESOLVED, or CLOSED
                    if user.role == User.Role.RESPONDER:
                        allowed_responder_statuses = [
                            Incident.Status.UNDER_INVESTIGATION, 
                            Incident.Status.RESOLVED,
                            Incident.Status.CLOSED
                        ]
                        if attrs['status'] not in allowed_responder_statuses:
                            raise serializers.ValidationError(
                                {"status": f"Responders can only set status to one of: {', '.join(allowed_responder_statuses)}."}
                            )
                    # Reporters cannot change status after dispatcher/admin review has moved past DRAFT or REPORTED
                    elif user.role == User.Role.REPORTER:
                        if self.instance.status not in [Incident.Status.DRAFT, Incident.Status.REPORTED]:
                            raise serializers.ValidationError(
                                {"status": "Reporters cannot transition status once response action has commenced."}
                            )
        return attrs
