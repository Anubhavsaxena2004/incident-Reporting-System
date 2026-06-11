from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Incident, IncidentStatusHistory

User = get_user_model()


class IncidentStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = IncidentStatusHistory
        fields = ('id', 'old_status', 'new_status', 'changed_by', 'remarks', 'timestamp')


class IncidentSerializer(serializers.ModelSerializer):
    reported_by = serializers.StringRelatedField(read_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role__in=[User.Role.OPERATOR, User.Role.ADMIN]),
        required=False,
        allow_null=True
    )
    remarks = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Optional comments outlining the status change context."
    )

    class Meta:
        model = Incident
        fields = (
            'incident_id', 'title', 'description', 'category',
            'latitude', 'longitude', 'address', 'image', 'status',
            'priority', 'reported_by', 'assigned_to', 'remarks', 'created_at', 'updated_at'
        )
        read_only_fields = ('incident_id', 'reported_by', 'created_at', 'updated_at')

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None

        # Pop write-only remarks and user context to set them as temporary parameters later
        remarks = attrs.pop('remarks', '')
        attrs['_remarks'] = remarks
        attrs['_changed_by'] = user

        # 1. New Incident Creation Validations
        if not self.instance:
            if user and user.role == User.Role.CITIZEN:
                if 'status' in attrs and attrs['status'] != Incident.Status.REPORTED:
                    raise serializers.ValidationError({"status": "Citizens cannot specify a custom initial status."})
                if 'assigned_to' in attrs and attrs['assigned_to'] is not None:
                    raise serializers.ValidationError({"assigned_to": "Citizens cannot assign responders."})

        # 2. Existing Incident Update Validations (Ownership Rules & State Machine Guard)
        else:
            old_status = self.instance.status
            new_status = attrs.get('status', old_status)

            # Check valid status transitions if changed
            if old_status != new_status:
                valid_next = Incident.VALID_TRANSITIONS.get(old_status, [])
                if new_status not in valid_next:
                    raise serializers.ValidationError(
                        {"status": f"Invalid status transition from {old_status} to {new_status}."}
                    )

            if user and user.role == User.Role.CITIZEN:
                # Citizens can only modify reported incidents if status is still 'REPORTED'
                if old_status != Incident.Status.REPORTED:
                    raise serializers.ValidationError(
                        {"non_field_errors": "Citizens cannot modify incidents after processing has commenced."}
                    )
                # Citizens cannot modify workflow fields
                if old_status != new_status:
                    raise serializers.ValidationError({"status": "Citizens cannot modify incident status."})
                if 'priority' in attrs and attrs['priority'] != self.instance.priority:
                    raise serializers.ValidationError({"priority": "Citizens cannot modify incident priority."})
                if 'assigned_to' in attrs and attrs['assigned_to'] != self.instance.assigned_to:
                    raise serializers.ValidationError({"assigned_to": "Citizens cannot assign or modify responders."})

            elif user and user.role == User.Role.OPERATOR:
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

    def create(self, validated_data):
        remarks = validated_data.pop('_remarks', '')
        changed_by = validated_data.pop('_changed_by', None)
        
        # Instantiate without saving to bind temporary variables
        instance = Incident(**validated_data)
        instance._remarks = remarks
        instance._changed_by = changed_by
        instance.save()
        return instance

    def update(self, instance, validated_data):
        remarks = validated_data.pop('_remarks', '')
        changed_by = validated_data.pop('_changed_by', None)
        
        # Bind temporary variables to the instance before saving
        instance._remarks = remarks
        instance._changed_by = changed_by
        
        return super().update(instance, validated_data)
