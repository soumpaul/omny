from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Device, DeviceAlert, EmergencyEvent, Space, SOSButtonConfiguration
from django.contrib.auth import get_user_model

User = get_user_model()


class SpaceSerializer(serializers.ModelSerializer):
    """Serializer for Space model"""
    
    class Meta:
        model = Space
        fields = ['id', 'household', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for Device model"""
    device_type_display = serializers.CharField(source='get_device_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    household_id = serializers.SerializerMethodField()
    is_wearable = serializers.BooleanField(read_only=True)
    is_fixed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Device
        fields = [
            'id', 'device_id', 'device_type', 'device_type_display',
            'name', 'manufacturer', 'model', 'serial_number',
            'user', 'space', 'status', 'status_display',
            'battery_level', 'last_online', 'firmware_version',
            'installed_date', 'notes', 'household_id',
            'is_wearable', 'is_fixed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'household_id']
    
    @extend_schema_field(OpenApiTypes.INT)
    def get_household_id(self, obj) -> int:
        household = obj.get_household()
        return household.id if household else None
    
    def validate(self, data):
        """Ensure device is associated with either user OR space, not both"""
        user = data.get('user')
        space = data.get('space')
        
        if user and space:
            raise serializers.ValidationError(
                "Device cannot be associated with both a user and a space."
            )
        if not user and not space:
            raise serializers.ValidationError(
                "Device must be associated with either a user or a space."
            )
        
        return data


class DeviceRegistrationSerializer(serializers.Serializer):
    """Serializer for registering a new device"""
    device_id = serializers.CharField(max_length=255)
    device_type = serializers.ChoiceField(choices=Device.DEVICE_TYPE_CHOICES)
    name = serializers.CharField(max_length=255)
    manufacturer = serializers.CharField(max_length=100, required=False, allow_blank=True)
    model = serializers.CharField(max_length=100, required=False, allow_blank=True)
    serial_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    firmware_version = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    # Association - either user_id OR space_id
    user_id = serializers.IntegerField(required=False, allow_null=True)
    space_id = serializers.IntegerField(required=False, allow_null=True)
    
    # Optional metadata
    installed_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Ensure device is associated with either user OR space"""
        user_id = data.get('user_id')
        space_id = data.get('space_id')
        
        if user_id and space_id:
            raise serializers.ValidationError(
                "Device cannot be associated with both a user and a space."
            )
        if not user_id and not space_id:
            raise serializers.ValidationError(
                "Device must be associated with either a user or a space."
            )
        
        # Validate user exists
        if user_id:
            try:
                User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise serializers.ValidationError({"user_id": "User not found."})
        
        # Validate space exists
        if space_id:
            try:
                Space.objects.get(id=space_id)
            except Space.DoesNotExist:
                raise serializers.ValidationError({"space_id": "Space not found."})
        
        return data


class DeviceAlertSerializer(serializers.ModelSerializer):
    """Serializer for DeviceAlert model"""
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    acknowledged_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceAlert
        fields = [
            'id', 'device', 'device_name', 'alert_type', 'alert_type_display',
            'severity', 'severity_display', 'message',
            'is_acknowledged', 'acknowledged_by', 'acknowledged_by_name',
            'acknowledged_at', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    @extend_schema_field(OpenApiTypes.STR)
    def get_acknowledged_by_name(self, obj) -> str:
        if obj.acknowledged_by:
            return obj.acknowledged_by.display_name or obj.acknowledged_by.email
        return None


class DeviceAlertCreateSerializer(serializers.Serializer):
    """Serializer for creating device alerts"""
    device_id = serializers.CharField(max_length=255)
    alert_type = serializers.ChoiceField(choices=DeviceAlert.ALERT_TYPE_CHOICES)
    severity = serializers.ChoiceField(choices=DeviceAlert.SEVERITY_CHOICES, default='medium')
    message = serializers.CharField()
    metadata = serializers.JSONField(required=False, allow_null=True)
    
    def validate_device_id(self, value):
        """Ensure device exists"""
        try:
            Device.objects.get(device_id=value)
        except Device.DoesNotExist:
            raise serializers.ValidationError("Device not found.")
        return value


class EmergencyEventSerializer(serializers.ModelSerializer):
    """Serializer for EmergencyEvent model"""
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    notification_status_display = serializers.CharField(source='get_notification_status_display', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    first_responder_name = serializers.SerializerMethodField()
    response_time_minutes = serializers.SerializerMethodField()
    location_display = serializers.CharField(source='get_location_display', read_only=True)
    
    class Meta:
        model = EmergencyEvent
        fields = [
            'id', 'device', 'device_name', 'event_type', 'event_type_display',
            'severity', 'severity_display', 'message',
            'notification_status', 'notification_status_display',
            'notified_caregivers', 'first_responder', 'first_responder_name',
            'responded_at', 'response_notes', 'response_time_minutes',
            'location_data', 'sensor_data', 'location_display',
            'sos_configuration', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    @extend_schema_field(OpenApiTypes.STR)
    def get_first_responder_name(self, obj) -> str:
        if obj.first_responder:
            return obj.first_responder.display_name or obj.first_responder.email
        return None
    
    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_response_time_minutes(self, obj) -> float:
        return obj.get_response_time()


class EmergencyEventCreateSerializer(serializers.Serializer):
    """Serializer for creating emergency events"""
    device_id = serializers.CharField(max_length=255)
    event_type = serializers.ChoiceField(choices=EmergencyEvent.EVENT_TYPE_CHOICES)
    severity = serializers.ChoiceField(choices=EmergencyEvent.SEVERITY_CHOICES, default='high')
    message = serializers.CharField()
    location_data = serializers.JSONField(required=False, allow_null=True)
    sensor_data = serializers.JSONField(required=False, allow_null=True)
    
    # For SOS events
    tap_count = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=3)
    
    def validate_device_id(self, value):
        """Ensure device exists"""
        try:
            Device.objects.get(device_id=value)
        except Device.DoesNotExist:
            raise serializers.ValidationError("Device not found.")
        return value
    
    def validate(self, data):
        """Validate SOS events have tap_count"""
        event_type = data.get('event_type')
        tap_count = data.get('tap_count')
        
        if event_type.startswith('sos_') and not tap_count:
            raise serializers.ValidationError(
                {"tap_count": "tap_count is required for SOS events."}
            )
        
        return data


class SOSButtonConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for SOS Button Configuration"""
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    
    class Meta:
        model = SOSButtonConfiguration
        fields = [
            'id', 'device', 'device_name', 'tap_count', 'action_type',
            'action_type_display', 'message_template', 'notify_caregivers',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
