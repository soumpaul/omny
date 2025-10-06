from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class Household(models.Model):
    """
    Represents a care circle - a group consisting of a patient and their caregivers
    """
    name = models.CharField(max_length=255, help_text="Care circle name (e.g., 'John's Care Team')")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Address fields
    address = models.CharField(max_length=255, blank=True, help_text="Street address line 1")
    address_2 = models.CharField(max_length=255, blank=True, help_text="Street address line 2 (apt, suite, etc.)")
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default='')
    
    # Optional settings
    timezone = models.CharField(max_length=50, default='UTC')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Household'
        verbose_name_plural = 'Households'
    
    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    """
    Custom user manager for handling user creation with Firebase UID
    """
    def create_user(self, email, password=None, firebase_uid=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        
        # Generate a placeholder firebase_uid if not provided (for admin/superuser)
        if not firebase_uid:
            import uuid
            firebase_uid = f"admin_{uuid.uuid4().hex[:20]}"
        
        user = self.model(email=email, firebase_uid=firebase_uid, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model that uses Firebase for authentication.
    Supports patients (those receiving care) and caregivers (those providing care).
    """
    # Firebase authentication
    firebase_uid = models.CharField(max_length=128, unique=True, db_index=True)
    
    # Basic user information
    email = models.EmailField(unique=True, db_index=True)
    display_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.URLField(blank=True, null=True)
    
    # Care circle relationship
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='members',
        null=True,
        blank=True,
        help_text="The care circle this user belongs to"
    )
    
    # User role within care circle
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('primary_caregiver', 'Primary Caregiver'),
        ('caregiver', 'Caregiver'),
    ]
    household_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='caregiver',
        help_text="User's role: patient (receiving care) or caregiver (providing care)"
    )
    
    # Django required fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Additional metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # firebase_uid is auto-generated for admin users
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email', 'firebase_uid']),
            models.Index(fields=['household', 'household_role']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return self.display_name or self.email
    
    def get_short_name(self):
        return self.display_name.split()[0] if self.display_name else self.email.split('@')[0]
    
    def is_patient(self):
        """Check if user is a patient"""
        return self.household_role == 'patient'
    
    def is_primary_caregiver(self):
        """Check if user is the primary caregiver"""
        return self.household_role == 'primary_caregiver'
    
    def is_caregiver(self):
        """Check if user is any type of caregiver"""
        return self.household_role in ['primary_caregiver', 'caregiver']
    
    def get_care_circle_members(self):
        """Get all members of the user's care circle"""
        if self.household:
            return self.household.members.all()
        return User.objects.none()
    
    def get_patient(self):
        """Get the patient in this care circle"""
        if self.household:
            return self.household.members.filter(household_role='patient').first()
        return None
    
    def get_caregivers(self):
        """Get all caregivers in this care circle"""
        if self.household:
            return self.household.members.filter(
                household_role__in=['primary_caregiver', 'caregiver']
            )
        return User.objects.none()


class Waitlist(models.Model):
    """
    Waitlist for controlling access during beta/early access.

    To enable/disable: Set WAITLIST_ENABLED in settings.py
    To remove entirely later: Delete this model, remove from admin.py, and remove waitlist checks in views.py
    """
    email = models.EmailField(unique=True, db_index=True)
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='waitlist_entries'
    )
    notes = models.TextField(blank=True, help_text='Optional notes about this waitlist entry')
    is_active = models.BooleanField(default=True, help_text='Set to False to revoke access')

    class Meta:
        ordering = ['-added_at']
        verbose_name = 'Waitlist Entry'
        verbose_name_plural = 'Waitlist Entries'

    def __str__(self):
        return f"{self.email} ({'active' if self.is_active else 'inactive'})"

    @classmethod
    def is_email_allowed(cls, email):
        """Check if an email is on the waitlist"""
        from django.conf import settings

        # If waitlist is disabled in settings, allow all emails
        if not getattr(settings, 'WAITLIST_ENABLED', True):
            return True

        try:
            return cls.objects.filter(
                email__iexact=email.lower(),
                is_active=True
            ).exists()
        except Exception:
            return False
