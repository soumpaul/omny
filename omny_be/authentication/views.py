from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import firebase_admin
from firebase_admin import auth, credentials
import os
import json

User = get_user_model()

# Import Waitlist model - can be easily removed later
from .models import Waitlist


class FirebaseAuthView(APIView):
    """
    Base view for Firebase authentication
    """
    permission_classes = [AllowAny]

    def verify_firebase_token(self, id_token):
        """
        Verify Firebase ID token and return decoded token
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token, None
        except auth.InvalidIdTokenError:
            return None, "Invalid authentication token"
        except auth.ExpiredIdTokenError:
            return None, "Authentication token has expired"
        except Exception as e:
            return None, f"Authentication error: {str(e)}"


class RegisterView(FirebaseAuthView):
    """
    Register a new user with Firebase authentication
    """
    
    @extend_schema(
        tags=['Authentication'],
        summary='Register a new user',
        description='Register a new user with Firebase ID token',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'id_token': {'type': 'string', 'description': 'Firebase ID token', 'example': 'eyJhbGciOiJSUzI1NiIsImtpZCI6...'},
                    'display_name': {'type': 'string', 'description': 'User display name', 'example': 'John Doe'},
                    'phone_number': {'type': 'string', 'description': 'Phone number', 'example': '+1234567890'},
                    'household_role': {
                        'type': 'string',
                        'enum': ['caregiver', 'patient', 'primary_caregiver'],
                        'description': 'User role in household',
                        'example': 'caregiver'
                    }
                },
                'required': ['id_token']
            }
        },
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'User registered successfully'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer', 'example': 1},
                            'email': {'type': 'string', 'example': 'john@example.com'},
                            'firebase_uid': {'type': 'string', 'example': 'firebase_uid_123'},
                            'display_name': {'type': 'string', 'example': 'John Doe'},
                            'phone_number': {'type': 'string', 'example': '+1234567890'},
                            'household_role': {'type': 'string', 'example': 'caregiver'},
                            'household_id': {'type': 'integer', 'nullable': True, 'example': None}
                        }
                    }
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Firebase ID token is required'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Invalid authentication token'}
                }
            }
        }
    )
    def post(self, request):
        id_token = request.data.get('id_token')

        if not id_token:
            return Response(
                {'error': 'Firebase ID token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify Firebase token
        decoded_token, error = self.verify_firebase_token(id_token)
        if error:
            return Response(
                {'error': error},
                status=status.HTTP_401_UNAUTHORIZED
            )

        firebase_uid = decoded_token.get('uid')
        email = decoded_token.get('email')

        # WAITLIST CHECK - Remove this block later to disable waitlist
        if not Waitlist.is_email_allowed(email):
            return Response(
                {
                    'error': 'waitlist_required',
                    'message': 'You are not currently on our waitlist. Please contact us for access.',
                    'email': email
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not email:
            return Response(
                {'error': 'Email not found in Firebase token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already exists - if so, treat as login
        try:
            user = User.objects.get(firebase_uid=firebase_uid)

            # Update last login
            from django.utils import timezone
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            return Response({
                'message': 'User registered successfully',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'firebase_uid': user.firebase_uid,
                    'display_name': user.display_name,
                    'phone_number': user.phone_number,
                    'household_role': user.household_role,
                    'household_id': user.household_id,
                }
            }, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            pass

        # Check if email already registered with different firebase_uid
        if User.objects.filter(email=email).exists():
            existing_user = User.objects.get(email=email)

            # Update last login
            from django.utils import timezone
            existing_user.last_login = timezone.now()
            existing_user.save(update_fields=['last_login'])

            return Response({
                'message': 'User registered successfully',
                'user': {
                    'id': existing_user.id,
                    'email': existing_user.email,
                    'firebase_uid': existing_user.firebase_uid,
                    'display_name': existing_user.display_name,
                    'phone_number': existing_user.phone_number,
                    'household_role': existing_user.household_role,
                    'household_id': existing_user.household_id,
                }
            }, status=status.HTTP_201_CREATED)

        # Create new user
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    firebase_uid=firebase_uid,
                    display_name=request.data.get('display_name', ''),
                    phone_number=request.data.get('phone_number', ''),
                    profile_picture=decoded_token.get('picture', ''),
                    household_role=request.data.get('household_role', 'caregiver'),
                )

                return Response({
                    'message': 'User registered successfully',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'firebase_uid': user.firebase_uid,
                        'display_name': user.display_name,
                        'phone_number': user.phone_number,
                        'household_role': user.household_role,
                        'household_id': user.household_id,
                    }
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Failed to create user: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(FirebaseAuthView):
    """
    Login user with Firebase authentication
    """
    
    @extend_schema(
        tags=['Authentication'],
        summary='Login user',
        description='Login an existing user with Firebase ID token',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'id_token': {'type': 'string', 'example': 'eyJhbGciOiJSUzI1NiIsImtpZCI6...'}
                },
                'required': ['id_token']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Login successful'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer', 'example': 1},
                            'email': {'type': 'string', 'example': 'john@example.com'},
                            'firebase_uid': {'type': 'string', 'example': 'firebase_uid_123'},
                            'display_name': {'type': 'string', 'example': 'John Doe'},
                            'phone_number': {'type': 'string', 'example': '+1234567890'},
                            'profile_picture': {'type': 'string', 'example': 'https://example.com/photo.jpg'},
                            'household_role': {'type': 'string', 'example': 'caregiver'},
                            'household_id': {'type': 'integer', 'example': 1},
                            'is_patient': {'type': 'boolean', 'example': False},
                            'is_caregiver': {'type': 'boolean', 'example': True},
                            'is_primary_caregiver': {'type': 'boolean', 'example': False}
                        }
                    }
                }
            },
            401: {'type': 'object', 'properties': {'error': {'type': 'string', 'example': 'Invalid authentication token'}}},
            404: {'type': 'object', 'properties': {'error': {'type': 'string', 'example': 'User not found. Please register first.'}}}
        }
    )
    def post(self, request):
        id_token = request.data.get('id_token')

        if not id_token:
            return Response(
                {'error': 'Firebase ID token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify Firebase token
        decoded_token, error = self.verify_firebase_token(id_token)
        if error:
            return Response(
                {'error': error},
                status=status.HTTP_401_UNAUTHORIZED
            )

        firebase_uid = decoded_token.get('uid')
        email = decoded_token.get('email')

        # WAITLIST CHECK - Remove this block later to disable waitlist
        if not Waitlist.is_email_allowed(email):
            return Response(
                {
                    'error': 'waitlist_required',
                    'message': 'You are not currently on our waitlist. Please contact us for access.',
                    'email': email
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create user
        try:
            user = User.objects.get(firebase_uid=firebase_uid)
            
            # Update last login
            from django.utils import timezone
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            return Response({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'firebase_uid': user.firebase_uid,
                    'display_name': user.display_name,
                    'phone_number': user.phone_number,
                    'profile_picture': user.profile_picture,
                    'household_role': user.household_role,
                    'household_id': user.household_id,
                    'is_patient': user.is_patient(),
                    'is_caregiver': user.is_caregiver(),
                    'is_primary_caregiver': user.is_primary_caregiver(),
                }
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found. Please register first.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Login failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyTokenView(FirebaseAuthView):
    """
    Verify Firebase ID token and return user information
    """
    
    @extend_schema(
        tags=['Authentication'],
        summary='Verify Firebase token',
        description='Verify a Firebase ID token and return user information',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'id_token': {'type': 'string', 'example': 'eyJhbGciOiJSUzI1NiIsImtpZCI6...'}
                },
                'required': ['id_token']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'valid': {'type': 'boolean', 'example': True},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer', 'example': 1},
                            'email': {'type': 'string', 'example': 'john@example.com'},
                            'firebase_uid': {'type': 'string', 'example': 'firebase_uid_123'},
                            'display_name': {'type': 'string', 'example': 'John Doe'},
                            'phone_number': {'type': 'string', 'example': '+1234567890'},
                            'profile_picture': {'type': 'string', 'example': 'https://example.com/photo.jpg'},
                            'household_role': {'type': 'string', 'example': 'caregiver'},
                            'household_id': {'type': 'integer', 'example': 1},
                            'is_active': {'type': 'boolean', 'example': True}
                        }
                    }
                }
            },
            401: {'type': 'object', 'properties': {'error': {'type': 'string', 'example': 'Invalid authentication token'}}},
            404: {'type': 'object', 'properties': {'valid': {'type': 'boolean', 'example': False}, 'error': {'type': 'string', 'example': 'User not found'}}}
        }
    )
    def post(self, request):
        id_token = request.data.get('id_token')
        
        if not id_token:
            return Response(
                {'error': 'Firebase ID token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify Firebase token
        decoded_token, error = self.verify_firebase_token(id_token)
        if error:
            return Response(
                {'error': error},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        firebase_uid = decoded_token.get('uid')
        
        try:
            user = User.objects.get(firebase_uid=firebase_uid)
            
            return Response({
                'valid': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'firebase_uid': user.firebase_uid,
                    'display_name': user.display_name,
                    'phone_number': user.phone_number,
                    'profile_picture': user.profile_picture,
                    'household_role': user.household_role,
                    'household_id': user.household_id,
                    'is_active': user.is_active,
                }
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {'valid': False, 'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserProfileView(APIView):
    """
    Get or update user profile (requires authentication)
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Authentication'],
        summary='Get user profile',
        description='Get current authenticated user profile',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer', 'example': 1},
                            'email': {'type': 'string', 'example': 'john@example.com'},
                            'firebase_uid': {'type': 'string', 'example': 'firebase_uid_123'},
                            'display_name': {'type': 'string', 'example': 'John Doe'},
                            'phone_number': {'type': 'string', 'example': '+1234567890'},
                            'profile_picture': {'type': 'string', 'example': 'https://example.com/photo.jpg'},
                            'household_role': {'type': 'string', 'example': 'caregiver'},
                            'household_id': {'type': 'integer', 'example': 1},
                            'is_patient': {'type': 'boolean', 'example': False},
                            'is_caregiver': {'type': 'boolean', 'example': True},
                            'is_primary_caregiver': {'type': 'boolean', 'example': False},
                            'date_joined': {'type': 'string', 'format': 'date-time', 'example': '2025-01-01T00:00:00Z'},
                            'last_login': {'type': 'string', 'format': 'date-time', 'example': '2025-01-02T12:30:00Z'}
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        """Get current user profile"""
        user = request.user
        
        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'firebase_uid': user.firebase_uid,
                'display_name': user.display_name,
                'phone_number': user.phone_number,
                'profile_picture': user.profile_picture,
                'household_role': user.household_role,
                'household_id': user.household_id,
                'is_patient': user.is_patient(),
                'is_caregiver': user.is_caregiver(),
                'is_primary_caregiver': user.is_primary_caregiver(),
                'date_joined': user.date_joined,
                'last_login': user.last_login,
            }
        }, status=status.HTTP_200_OK)
    
    @extend_schema(
        tags=['Authentication'],
        summary='Update user profile',
        description='Update current user profile fields',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'display_name': {'type': 'string', 'example': 'Jane Doe'},
                    'phone_number': {'type': 'string', 'example': '+9876543210'},
                    'profile_picture': {'type': 'string', 'example': 'https://example.com/new-photo.jpg'}
                }
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Profile updated successfully'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer', 'example': 1},
                            'email': {'type': 'string', 'example': 'john@example.com'},
                            'display_name': {'type': 'string', 'example': 'Jane Doe'},
                            'phone_number': {'type': 'string', 'example': '+9876543210'},
                            'profile_picture': {'type': 'string', 'example': 'https://example.com/new-photo.jpg'}
                        }
                    }
                }
            }
        }
    )
    def patch(self, request):
        """Update user profile"""
        user = request.user
        
        # Update allowed fields
        allowed_fields = ['display_name', 'phone_number', 'profile_picture']
        
        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
        
        try:
            user.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'display_name': user.display_name,
                    'phone_number': user.phone_number,
                    'profile_picture': user.profile_picture,
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Failed to update profile: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(APIView):
    """
    Logout user (client should delete Firebase token)
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Authentication'],
        summary='Logout user',
        description='Logout user (client should delete Firebase token)',
        request=None,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Logout successful. Please delete your Firebase token on the client side.'}
                }
            }
        }
    )
    def post(self, request):
        return Response({
            'message': 'Logout successful. Please delete your Firebase token on the client side.'
        }, status=status.HTTP_200_OK)
