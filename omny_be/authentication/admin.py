from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Household, Waitlist


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'member_count', 'patient_name')
    list_filter = ('is_active', 'created_at', 'country', 'state')
    search_fields = ('name', 'address', 'city', 'state', 'country')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active')
        }),
        ('Address', {
            'fields': ('address', 'address_2', 'city', 'state', 'country')
        }),
        ('Settings', {
            'fields': ('timezone',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Total Members'
    
    def patient_name(self, obj):
        patient = obj.members.filter(household_role='patient').first()
        return patient.display_name or patient.email if patient else 'No patient'
    patient_name.short_description = 'Patient'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'display_name', 'household', 'household_role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'household_role', 'date_joined')
    search_fields = ('email', 'display_name', 'firebase_uid', 'phone_number')
    readonly_fields = ('firebase_uid', 'created_at', 'updated_at', 'last_login', 'date_joined')
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'firebase_uid', 'password')
        }),
        ('Personal Information', {
            'fields': ('display_name', 'phone_number', 'profile_picture')
        }),
        ('Care Circle', {
            'fields': ('household', 'household_role')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Required Information', {
            'classes': ('wide',),
            'fields': ('email', 'firebase_uid', 'password1', 'password2'),
        }),
        ('Optional Information', {
            'classes': ('wide',),
            'fields': ('display_name', 'household', 'household_role'),
        }),
    )
    
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'added_at', 'added_by')
    list_filter = ('is_active', 'added_at')
    search_fields = ('email', 'notes')
    readonly_fields = ('added_at',)

    fieldsets = (
        ('Waitlist Entry', {
            'fields': ('email', 'is_active')
        }),
        ('Details', {
            'fields': ('added_by', 'notes', 'added_at')
        }),
    )
