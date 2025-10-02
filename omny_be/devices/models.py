from django.db import models
from django.conf import settings
from authentication.models import Household


class Space(models.Model):
    """
    Represents a physical space/room within a household (e.g., living room, bathroom)
    """
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='spaces',
        help_text="The care circle/household this space belongs to"
    )
    name = models.CharField(max_length=100, help_text="Room name (e.g., 'Living Room', 'Master Bathroom')")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['household', 'name']
        verbose_name = 'Space'
        verbose_name_plural = 'Spaces'
        unique_together = ['household', 'name']
    
    def __str__(self):
        return f"{self.household.name} - {self.name}"


class Device(models.Model):
    """
    Represents a safety device that can be associated with either a user or a space
    """
    DEVICE_TYPE_CHOICES = [
        ('watch', 'Smart Watch'),
        ('sos_button', 'SOS Button'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('offline', 'Offline'),
    ]
    
    # Basic device information
    device_id = models.CharField(max_length=255, unique=True, db_index=True, help_text="Unique device identifier")
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPE_CHOICES)
    name = models.CharField(max_length=255, help_text="Custom name for the device")
    manufacturer = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    
    # Association - either with a user OR a space
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='devices',
        null=True,
        blank=True,
        help_text="User this device is assigned to (for wearables like watches)"
    )
    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        related_name='devices',
        null=True,
        blank=True,
        help_text="Space this device is installed in (for fixed devices like SOS buttons)"
    )
    
    # Device status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    battery_level = models.IntegerField(null=True, blank=True, help_text="Battery percentage (0-100)")
    last_online = models.DateTimeField(null=True, blank=True)
    firmware_version = models.CharField(max_length=50, blank=True)
    
    # Installation details
    installed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Additional notes about the device")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'
        indexes = [
            models.Index(fields=['device_id', 'status']),
            models.Index(fields=['device_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_device_type_display()})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Ensure device is associated with either user OR space, not both or neither
        if self.user and self.space:
            raise ValidationError("Device cannot be associated with both a user and a space.")
        if not self.user and not self.space:
            raise ValidationError("Device must be associated with either a user or a space.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_household(self):
        """Get the household this device belongs to"""
        if self.user:
            return self.user.household
        elif self.space:
            return self.space.household
        return None
    
    def is_wearable(self):
        """Check if device is a wearable (user-associated)"""
        return self.user is not None
    
    def is_fixed(self):
        """Check if device is fixed to a space"""
        return self.space is not None
    
    def needs_battery_replacement(self, threshold=20):
        """Check if battery is below threshold"""
        if self.battery_level is not None:
            return self.battery_level < threshold
        return False


class DeviceAlert(models.Model):
    """
    Tracks non-emergency device alerts (low battery, offline, etc.)
    For emergencies (falls, SOS), use EmergencyEvent model
    """
    ALERT_TYPE_CHOICES = [
        ('low_battery', 'Low Battery'),
        ('device_offline', 'Device Offline'),
        ('maintenance_required', 'Maintenance Required'),
    ]
    
    SEVERITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('info', 'Info'),
    ]
    
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    message = models.TextField(help_text="Alert message/description")
    
    # Alert status
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        help_text="Caregiver who acknowledged the alert"
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Additional data
    metadata = models.JSONField(null=True, blank=True, help_text="Additional alert data")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Device Alert'
        verbose_name_plural = 'Device Alerts'
        indexes = [
            models.Index(fields=['device', 'alert_type', 'created_at']),
            models.Index(fields=['is_acknowledged', 'severity']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.get_alert_type_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class EmergencyEvent(models.Model):
    """
    Unified model for all emergency events requiring caregiver response
    (fall detection, SOS button presses, etc.)
    """
    EVENT_TYPE_CHOICES = [
        ('fall_detected', 'Fall Detected'),
        ('sos_1_tap', 'SOS - 1 Tap'),
        ('sos_2_taps', 'SOS - 2 Taps'),
        ('sos_3_taps', 'SOS - 3 Taps'),
    ]
    
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
    ]
    
    NOTIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('partially_sent', 'Partially Sent'),
    ]
    
    # Event details
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='emergency_events',
        help_text="Device that triggered the emergency"
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='high')
    message = models.TextField(help_text="Emergency message/description")
    
    # SOS Configuration reference (if applicable)
    sos_configuration = models.ForeignKey(
        'SOSButtonConfiguration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emergency_events',
        help_text="SOS configuration used (if this is an SOS event)"
    )
    
    # Notification tracking
    notification_status = models.CharField(
        max_length=20,
        choices=NOTIFICATION_STATUS_CHOICES,
        default='pending'
    )
    notified_caregivers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='emergency_notifications',
        blank=True,
        help_text="Caregivers who were notified"
    )
    
    # Response tracking
    first_responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emergency_responses',
        help_text="First caregiver to respond"
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    response_notes = models.TextField(blank=True, help_text="Notes from the responder")
    
    # Additional data
    location_data = models.JSONField(
        null=True,
        blank=True,
        help_text="GPS coordinates or location data"
    )
    sensor_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Sensor data (e.g., accelerometer readings for falls)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Emergency Event'
        verbose_name_plural = 'Emergency Events'
        indexes = [
            models.Index(fields=['device', 'event_type', 'created_at']),
            models.Index(fields=['notification_status', 'severity']),
            models.Index(fields=['first_responder', 'responded_at']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.get_event_type_display()} at {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def mark_as_responded(self, responder, notes=""):
        """Mark this emergency as responded to"""
        from django.utils import timezone
        if not self.first_responder:
            self.first_responder = responder
            self.responded_at = timezone.now()
            self.response_notes = notes
            self.save()
    
    def get_response_time(self):
        """Get time between event and response in minutes"""
        if self.responded_at:
            delta = self.responded_at - self.created_at
            return round(delta.total_seconds() / 60, 1)
        return None
    
    def get_location_display(self):
        """Get human-readable location"""
        if self.device.space:
            return self.device.space.name
        elif self.device.user:
            return f"With {self.device.user.display_name or self.device.user.email}"
        return "Unknown location"


class SOSButtonConfiguration(models.Model):
    """
    Configuration for SOS button tap patterns (1, 2, or 3 taps)
    """
    ACTION_TYPE_CHOICES = [
        ('call', 'Phone Call'),
        ('sms', 'SMS'),
        ('notification', 'Push Notification'),
        ('all', 'All (Call + SMS + Notification)'),
    ]
    
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='sos_configurations',
        limit_choices_to={'device_type': 'sos_button'},
        help_text="SOS Button device"
    )
    tap_count = models.IntegerField(
        choices=[(1, '1 Tap'), (2, '2 Taps'), (3, '3 Taps')],
        help_text="Number of taps to trigger this action"
    )
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPE_CHOICES,
        default='all',
        help_text="Type of notification to send"
    )
    message_template = models.TextField(
        help_text="Message template. Use {patient_name}, {location}, {time} as placeholders"
    )
    
    # Recipients - caregivers who should be notified
    notify_caregivers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='sos_notifications',
        limit_choices_to={'household_role__in': ['primary_caregiver', 'caregiver']},
        help_text="Caregivers to notify when this tap pattern is triggered"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['device', 'tap_count']
        verbose_name = 'SOS Button Configuration'
        verbose_name_plural = 'SOS Button Configurations'
        unique_together = ['device', 'tap_count']
        indexes = [
            models.Index(fields=['device', 'tap_count', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.tap_count} Tap(s)"
    
    def get_formatted_message(self):
        """Get the message with placeholders replaced"""
        from django.utils import timezone
        
        household = self.device.get_household()
        patient = household.members.filter(household_role='patient').first() if household else None
        location = self.device.space.name if self.device.space else "Unknown location"
        
        return self.message_template.format(
            patient_name=patient.display_name if patient else "Patient",
            location=location,
            time=timezone.now().strftime('%I:%M %p')
        )


