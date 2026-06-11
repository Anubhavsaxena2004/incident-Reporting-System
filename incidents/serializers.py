from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Incident

User = get_user_model()


class IncidentSerializer(serializers.ModelSerializer):
    reported_by = serializers.StringRelatedField(read_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role__in=[User.Role.OPERATOR, User.Role.ADMIN]),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Incident
        fields = (
            'incident_id', 'title', 'description', 'category',
            'latitude', 'longitude', 'address', 'image', 'status',
            'priority', 'reported_by', 'assigned_to', 'created_at', 'updated_at'
        )
        read_only_fields = ('incident_id', 'reported_by', 'created_at', 'updated_at')

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user:
            return attrs
        
        user = request.user
        
        # 1. Validation for Creating Incidents
        if not self.instance:
            if user.role == User.Role.CITIZEN:
                if 'status' in attrs and attrs['status'] != Incident.Status.REPORTED:
                    raise serializers.ValidationError({"status": "Citizens cannot specify a custom initial status."})
                if 'assigned_to' in attrs and attrs['assigned_to'] is not None:
                    raise serializers.ValidationError({"assigned_to": "Citizens cannot assign responders."})

        # 2. Validation for Updating Incidents (Ownership Rules)
        else:
            if user.role == User.Role.CITIZEN:
                # Citizens can only modify their reported incidents if status is still 'REPORTED'
                if self.instance.status != Incident.Status.REPORTED:
                    raise serializers.ValidationError(
                        {"non_field_errors": "Citizens cannot modify incidents after an Operator has processed them."}
                    )
                # Citizens cannot modify workflow fields
                if 'status' in attrs and attrs['status'] != self.instance.status:
                    raise serializers.ValidationError({"status": "Citizens cannot modify status."})
                if 'priority' in attrs and attrs['priority'] != self.instance.priority:
                    raise serializers.ValidationError({"priority": "Citizens cannot modify priority."})
                if 'assigned_to' in attrs and attrs['assigned_to'] != self.instance.assigned_to:
                    raise serializers.ValidationError({"assigned_to": "Citizens cannot assign or modify responders."})

            elif user.role == User.Role.OPERATOR:
                # Operators cannot change the reporter
                if 'reported_by' in attrs and attrs['reported_by'] != self.instance.reported_by:
                    raise serializers.ValidationError({"reported_by": "Reporters cannot be modified."})

        # 3. Geo Coordinates Range checks
        latitude = attrs.get('latitude', self.instance.latitude if self.instance else None)
        if latitude is not None and (latitude < -90 or latitude > 90):
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90 degrees."})

        longitude = attrs.get('longitude', self.instance.longitude if self.instance else None)
        if longitude is not None and (longitude < -180 or longitude > 180):
            raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180 degrees."})

        return attrs
