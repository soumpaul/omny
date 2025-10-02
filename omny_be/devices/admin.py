from django.contrib import admin
from django.utils.html import format_html
from .models import Space, Device, DeviceAlert, EmergencyEvent, SOSButtonConfiguration


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'household', 'device_count', 'created_at')
    list_filter = ('household', 'created_at')
    search_fields = ('name', 'household__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('household', 'name')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def device_count(self, obj):
        return obj.devices.count()
    device_count.short_description = 'Devices'


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'device_type', 'device_id', 'status', 'battery_indicator', 'association', 'last_online')
    list_filter = ('device_type', 'status', 'manufacturer', 'created_at')
    search_fields = ('name', 'device_id', 'manufacturer', 'model', 'user__email', 'space__name')
    readonly_fields = ('created_at', 'updated_at', 'last_online')
    
    fieldsets = (
        ('Device Information', {
            'fields': ('device_id', 'device_type', 'name', 'manufacturer', 'model')
        }),
        ('Association', {
            'fields': ('user', 'space'),
            'description': 'Associate device with either a user (wearables) OR a space (fixed devices), not both.'
        }),
        ('Status & Monitoring', {
            'fields': ('status', 'battery_level', 'last_online', 'firmware_version')
        }),
        ('Installation', {
            'fields': ('installed_date', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def battery_indicator(self, obj):
        if obj.battery_level is None:
            return '-'
        
        if obj.battery_level < 20:
            color = 'red'
            icon = '🔴'
        elif obj.battery_level < 50:
            color = 'orange'
            icon = '🟠'
        else:
            color = 'green'
            icon = '🟢'
        
        return format_html(
            '<span style="color: {};">{} {}%</span>',
            color, icon, obj.battery_level
        )
    battery_indicator.short_description = 'Battery'
    
    def association(self, obj):
        if obj.user:
            return format_html('👤 User: {}', obj.user.display_name or obj.user.email)
        elif obj.space:
            return format_html('📍 Space: {}', obj.space.name)
        return '-'
    association.short_description = 'Associated With'


@admin.register(DeviceAlert)
class DeviceAlertAdmin(admin.ModelAdmin):
    list_display = ('device', 'alert_type', 'severity_indicator', 'is_acknowledged', 'acknowledged_by', 'created_at')
    list_filter = ('alert_type', 'severity', 'is_acknowledged', 'created_at')
    search_fields = ('device__name', 'message', 'device__device_id')
    readonly_fields = ('created_at', 'acknowledged_at')
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('device', 'alert_type', 'severity', 'message')
        }),
        ('Acknowledgment', {
            'fields': ('is_acknowledged', 'acknowledged_by', 'acknowledged_at')
        }),
        ('Additional Data', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def severity_indicator(self, obj):
        severity_colors = {
            'high': ('orange', '🟠'),
            'medium': ('blue', '🔵'),
            'low': ('green', '🟢'),
            'info': ('gray', 'ℹ️'),
        }
        color, icon = severity_colors.get(obj.severity, ('black', '•'))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_severity_display()
        )
    severity_indicator.short_description = 'Severity'
    
    actions = ['mark_as_acknowledged']
    
    def mark_as_acknowledged(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            is_acknowledged=True,
            acknowledged_by=request.user,
            acknowledged_at=timezone.now()
        )
        self.message_user(request, f'{updated} alert(s) marked as acknowledged.')
    mark_as_acknowledged.short_description = 'Mark selected alerts as acknowledged'


@admin.register(EmergencyEvent)
class EmergencyEventAdmin(admin.ModelAdmin):
    list_display = ('device', 'event_type', 'severity_indicator', 'notification_status_indicator', 'first_responder', 'response_time_display', 'created_at')
    list_filter = ('event_type', 'severity', 'notification_status', 'created_at', 'device')
    search_fields = ('device__name', 'device__device_id', 'message', 'response_notes')
    readonly_fields = ('created_at', 'responded_at', 'response_time_display')
    filter_horizontal = ('notified_caregivers',)
    
    fieldsets = (
        ('Event Details', {
            'fields': ('device', 'event_type', 'severity', 'message', 'sos_configuration')
        }),
        ('Notification', {
            'fields': ('notification_status', 'notified_caregivers')
        }),
        ('Response', {
            'fields': ('first_responder', 'responded_at', 'response_time_display', 'response_notes')
        }),
        ('Additional Data', {
            'fields': ('location_data', 'sensor_data'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def severity_indicator(self, obj):
        severity_colors = {
            'critical': ('red', '🔴'),
            'high': ('orange', '🟠'),
            'medium': ('blue', '🔵'),
        }
        color, icon = severity_colors.get(obj.severity, ('black', '•'))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_severity_display()
        )
    severity_indicator.short_description = 'Severity'
    
    def notification_status_indicator(self, obj):
        status_colors = {
            'pending': ('orange', '⏳'),
            'sent': ('green', '✅'),
            'failed': ('red', '❌'),
            'partially_sent': ('blue', '⚠️'),
        }
        color, icon = status_colors.get(obj.notification_status, ('black', '•'))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_notification_status_display()
        )
    notification_status_indicator.short_description = 'Notification'
    
    def response_time_display(self, obj):
        response_time = obj.get_response_time()
        if response_time is not None:
            if response_time < 5:
                color = 'green'
            elif response_time < 15:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} min</span>',
                color, response_time
            )
        return '-'
    response_time_display.short_description = 'Response Time'
    
    actions = ['mark_as_responded']
    
    def mark_as_responded(self, request, queryset):
        count = 0
        for event in queryset.filter(first_responder__isnull=True):
            event.mark_as_responded(request.user, "Marked via admin action")
            count += 1
        self.message_user(request, f'{count} emergency event(s) marked as responded.')
    mark_as_responded.short_description = 'Mark as responded by me'


@admin.register(SOSButtonConfiguration)
class SOSButtonConfigurationAdmin(admin.ModelAdmin):
    list_display = ('device', 'tap_count', 'action_type', 'caregiver_count', 'is_active', 'created_at')
    list_filter = ('tap_count', 'action_type', 'is_active', 'created_at')
    search_fields = ('device__name', 'device__device_id', 'message_template')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('notify_caregivers',)
    
    fieldsets = (
        ('Device & Trigger', {
            'fields': ('device', 'tap_count', 'is_active')
        }),
        ('Action Configuration', {
            'fields': ('action_type', 'message_template')
        }),
        ('Recipients', {
            'fields': ('notify_caregivers',),
            'description': 'Select caregivers who should be notified when this tap pattern is triggered'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def caregiver_count(self, obj):
        count = obj.notify_caregivers.count()
        return format_html('<span style="font-weight: bold;">{} caregiver(s)</span>', count)
    caregiver_count.short_description = 'Recipients'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "device":
            kwargs["queryset"] = Device.objects.filter(device_type='sos_button')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


